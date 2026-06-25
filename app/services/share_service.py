import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_audit_logger
from app.exceptions import ShareTokenInvalid
from app.models.file import File
from app.models.share_token import FileShareToken
from app.models.user import User

audit = get_audit_logger()

TOKEN_BYTES = 32


async def create_share_token(
    db: AsyncSession,
    file_row: File,
    creator: User,
    expires_in_hours: int,
    max_downloads: int | None,
) -> FileShareToken:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    share = FileShareToken(
        token=token,
        file_id=file_row.id,
        created_by=creator.id,
        expires_at=expires_at,
        max_downloads=max_downloads,
        downloads_count=0,
        revoked=False,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    audit.info(
        "share_created token_file=%s by=%s expires_at=%s max_downloads=%s",
        file_row.id, creator.id, expires_at.isoformat(), max_downloads,
    )
    return share


async def resolve_and_consume_token(db: AsyncSession, token: str) -> tuple[FileShareToken, File]:
    result = await db.execute(
        select(FileShareToken).where(FileShareToken.token == token).with_for_update()
    )
    share = result.scalar_one_or_none()
    if share is None or share.revoked:
        raise ShareTokenInvalid()

    now = datetime.now(timezone.utc)
    expires_at = share.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise ShareTokenInvalid()

    if share.max_downloads is not None and share.downloads_count >= share.max_downloads:
        raise ShareTokenInvalid()

    file_row = await db.get(File, share.file_id)
    if file_row is None or file_row.deleted_at is not None:
        raise ShareTokenInvalid()

    share.downloads_count += 1
    await db.commit()
    await db.refresh(share)

    audit.info(
        "share_downloaded token_file=%s count=%s", file_row.id, share.downloads_count
    )
    return share, file_row


async def revoke_token(db: AsyncSession, file_id: uuid.UUID, token: str) -> None:
    result = await db.execute(
        select(FileShareToken).where(
            FileShareToken.token == token, FileShareToken.file_id == file_id
        )
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise ShareTokenInvalid()

    share.revoked = True
    await db.commit()
    audit.info("share_revoked token_file=%s", file_id)
