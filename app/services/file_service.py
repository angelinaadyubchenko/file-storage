import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import magic
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_audit_logger
from app.exceptions import FileNotFound, FileTooLarge, InvalidFileType, StorageQuotaExceeded
from app.models.file import File
from app.models.storage import StoragePolicy
from app.models.user import User
from app.services import storage_service

audit = get_audit_logger()


def _storage_root() -> Path:
    return Path(settings.STORAGE_ROOT_PATH)


def _mime_allowed(mime_type: str, policy: StoragePolicy) -> bool:
    if not policy.allowed_mime_types:
        return True
    return mime_type in policy.allowed_mime_types


def _extension_allowed(filename: str, policy: StoragePolicy) -> bool:
    if not policy.allowed_extensions:
        return True
    ext = os.path.splitext(filename)[1].lower()
    return ext in [e.lower() for e in policy.allowed_extensions]


async def upload_file(
    db: AsyncSession,
    storage_id: uuid.UUID,
    upload: UploadFile,
    uploader: User,
) -> File:
    policy = await storage_service.get_storage_policy(db, storage_id)
    if policy is None:
        raise StorageQuotaExceeded("Storage has no policy configured")

    buffer = bytearray()
    total = 0
    while True:
        chunk = await upload.read(settings.UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > policy.max_file_size:
            buffer.clear()
            await upload.close()
            raise FileTooLarge(
                f"File exceeds the per-file limit of {policy.max_file_size} bytes"
            )
        buffer.extend(chunk)
    await upload.close()

    mime_type = magic.from_buffer(bytes(buffer[:2048]), mime=True) if buffer else "application/octet-stream"
    if not _mime_allowed(mime_type, policy):
        raise InvalidFileType(f"MIME type '{mime_type}' is not allowed by the storage policy")
    if not _extension_allowed(upload.filename or "", policy):
        raise InvalidFileType("File extension is not allowed by the storage policy")

    await storage_service.lock_storage(db, storage_id)
    used = await storage_service.get_used_bytes(db, storage_id)
    if used + total > policy.max_storage_size:
        free = max(policy.max_storage_size - used, 0)
        raise StorageQuotaExceeded(
            f"Uploading this file ({total} bytes) would exceed the storage quota. "
            f"Only {free} bytes remain of {policy.max_storage_size}."
        )

    file_id = uuid.uuid4()
    ext = os.path.splitext(upload.filename or "")[1]
    relative_path = f"{storage_id}/{file_id}{ext}"
    absolute_path = _storage_root() / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(bytes(buffer))

    file_row = File(
        id=file_id,
        storage_id=storage_id,
        original_filename=upload.filename or "unnamed",
        mime_type=mime_type,
        size=total,
        file_path=relative_path,
        uploaded_by=uploader.id,
    )
    db.add(file_row)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        absolute_path.unlink(missing_ok=True)
        raise
    await db.refresh(file_row)

    audit.info(
        "file_uploaded file_id=%s storage_id=%s size=%s mime=%s by=%s",
        file_id, storage_id, total, mime_type, uploader.id,
    )
    return file_row


async def get_active_file(db: AsyncSession, file_id: uuid.UUID) -> File | None:
    result = await db.execute(
        select(File).where(File.id == file_id, File.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_active_file_or_404(db: AsyncSession, file_id: uuid.UUID) -> File:
    file_row = await get_active_file(db, file_id)
    if file_row is None:
        raise FileNotFound()
    return file_row


async def list_active_files(db: AsyncSession, storage_id: uuid.UUID) -> list[File]:
    result = await db.execute(
        select(File)
        .where(File.storage_id == storage_id, File.deleted_at.is_(None))
        .order_by(File.created_at.desc())
    )
    return list(result.scalars().all())


def absolute_path_for(file_row: File) -> Path:
    return _storage_root() / file_row.file_path


async def soft_delete_file(db: AsyncSession, file_row: File, deleted_by: User) -> None:
    file_row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    audit.info(
        "file_deleted file_id=%s storage_id=%s by=%s (soft)",
        file_row.id, file_row.storage_id, deleted_by.id,
    )
