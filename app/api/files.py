import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import assert_storage_access, get_current_user, require_storage_grant
from app.db.session import get_db
from app.models.enums import StorageGrantType
from app.models.user import User
from app.schemas.file import FileRead
from app.services import file_service

router = APIRouter(tags=["files"])


def content_disposition(filename: str) -> str:
    ascii_only = filename.encode("ascii", "ignore").decode("ascii")
    ascii_fallback = "".join(c for c in ascii_only if c.isprintable() and c not in '"\\') or "download"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.post(
    "/storages/{storage_id}/files",
    response_model=FileRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    storage_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_WRITE)),
) -> FileRead:
    file_row = await file_service.upload_file(db, storage_id, file, uploader=current_user)
    return file_row


@router.get("/storages/{storage_id}/files", response_model=list[FileRead])
async def list_files(
    storage_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_READ)),
) -> list[FileRead]:
    return await file_service.list_active_files(db, storage_id)


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    file_row = await file_service.get_active_file_or_404(db, file_id)
    await assert_storage_access(db, current_user, file_row.storage_id, StorageGrantType.STORAGE_READ)

    file_service.audit.info(
        "file_downloaded file_id=%s storage_id=%s by=%s",
        file_row.id, file_row.storage_id, current_user.id,
    )
    return FileResponse(
        path=file_service.absolute_path_for(file_row),
        media_type=file_row.mime_type,
        headers={"Content-Disposition": content_disposition(file_row.original_filename)},
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    file_row = await file_service.get_active_file_or_404(db, file_id)
    await assert_storage_access(
        db, current_user, file_row.storage_id, StorageGrantType.STORAGE_DELETE
    )
    await file_service.soft_delete_file(db, file_row, deleted_by=current_user)
