import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import assert_storage_access, get_current_user
from app.api.files import content_disposition
from app.api.openapi import error_responses
from app.db.session import get_db
from app.exceptions import AuthenticationError, FileNotFound, PermissionDenied, ShareTokenInvalid
from app.models.enums import StorageGrantType
from app.models.user import User
from app.schemas.share import ShareTokenCreate, ShareTokenRead
from app.services import file_service, share_service

router = APIRouter(tags=["share"])


@router.post(
    "/files/{file_id}/share",
    response_model=ShareTokenRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать ссылку на файл",
    description=(
        "Создаёт временную публичную ссылку на конкретный файл с ограничением по времени "
        "и (опционально) по числу скачиваний. Требуется право STORAGE_MANAGE_ACCESS."
    ),
    responses=error_responses(AuthenticationError, PermissionDenied, FileNotFound),
)
async def create_share(
    file_id: uuid.UUID,
    payload: ShareTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareTokenRead:
    file_row = await file_service.get_active_file_or_404(db, file_id)
    await assert_storage_access(
        db, current_user, file_row.storage_id, StorageGrantType.STORAGE_MANAGE_ACCESS
    )
    share = await share_service.create_share_token(
        db,
        file_row=file_row,
        creator=current_user,
        expires_in_hours=payload.expires_in_hours,
        max_downloads=payload.max_downloads,
    )
    return share


@router.get(
    "/shared/{token}",
    summary="Скачать по ссылке",
    description=(
        "Публичное скачивание файла по токену без авторизации. Невалидный, просроченный "
        "или исчерпанный токен возвращает 404 (без раскрытия причины)."
    ),
    responses=error_responses(ShareTokenInvalid),
)
async def download_shared(token: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    share, file_row = await share_service.resolve_and_consume_token(db, token)
    return FileResponse(
        path=file_service.absolute_path_for(file_row),
        media_type=file_row.mime_type,
        headers={"Content-Disposition": content_disposition(file_row.original_filename)},
    )


@router.delete(
    "/files/{file_id}/share/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать ссылку",
    description="Делает ссылку на файл недействительной. Требуется право STORAGE_MANAGE_ACCESS.",
    responses=error_responses(AuthenticationError, PermissionDenied, FileNotFound, ShareTokenInvalid),
)
async def revoke_share(
    file_id: uuid.UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    file_row = await file_service.get_active_file_or_404(db, file_id)
    await assert_storage_access(
        db, current_user, file_row.storage_id, StorageGrantType.STORAGE_MANAGE_ACCESS
    )
    await share_service.revoke_token(db, file_id=file_id, token=token)
