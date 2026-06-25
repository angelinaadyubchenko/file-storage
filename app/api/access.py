import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_storage_grant
from app.db.session import get_db
from app.models.enums import StorageGrantType
from app.models.user import User
from app.schemas.grant import GrantCreate, GrantRead
from app.services import grant_service

router = APIRouter(prefix="/storages/{storage_id}/access", tags=["access"])


@router.post("", response_model=GrantRead, status_code=status.HTTP_201_CREATED)
async def grant_access(
    storage_id: uuid.UUID,
    payload: GrantCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_MANAGE_ACCESS)),
) -> GrantRead:
    grant, created = await grant_service.grant_storage_access(
        db,
        storage_id=storage_id,
        target_user_id=payload.target_user_id,
        grant_type=payload.grant_type,
        granted_by=current_user,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return grant


@router.get("", response_model=list[GrantRead])
async def list_access(
    storage_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_MANAGE_ACCESS)),
) -> list[GrantRead]:
    return await grant_service.list_storage_grants(db, storage_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_access(
    storage_id: uuid.UUID,
    user_id: uuid.UUID,
    grant_type: StorageGrantType | None = Query(
        default=None, description="If omitted, all grants for the user on this storage are revoked"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_MANAGE_ACCESS)),
) -> None:
    await grant_service.revoke_storage_access(
        db,
        storage_id=storage_id,
        target_user_id=user_id,
        grant_type=grant_type,
        revoked_by=current_user,
    )
