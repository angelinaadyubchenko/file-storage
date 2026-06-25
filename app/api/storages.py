import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_global_grant, require_storage_grant
from app.db.session import get_db
from app.models.enums import GlobalGrantType, StorageGrantType
from app.models.user import User
from app.schemas.storage import (
    StorageCreate,
    StoragePolicyRead,
    StoragePolicyUpdate,
    StorageRead,
)
from app.services import grant_service, storage_service

router = APIRouter(prefix="/storages", tags=["storages"])


def _to_read(storage, used_bytes: int | None = None) -> StorageRead:
    data = StorageRead.model_validate(storage)
    data.used_bytes = used_bytes
    if storage.policy is not None:
        data.policy = StoragePolicyRead.model_validate(storage.policy)
    return data


@router.post("", response_model=StorageRead, status_code=status.HTTP_201_CREATED)
async def create_storage(
    payload: StorageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_global_grant(GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE)),
) -> StorageRead:
    storage = await storage_service.create_global_storage(db, payload, owner=current_user)
    return _to_read(storage, used_bytes=0)


@router.get("", response_model=list[StorageRead])
async def list_storages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StorageRead]:
    storages = await storage_service.list_accessible_storages(db, current_user)
    return [_to_read(s) for s in storages]


@router.get("/{storage_id}", response_model=StorageRead)
async def get_storage(
    storage_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_READ)),
) -> StorageRead:
    storage = await storage_service.get_storage_or_404(db, storage_id)
    used = await storage_service.get_used_bytes(db, storage_id)
    return _to_read(storage, used_bytes=used)


@router.get("/{storage_id}/my-grants")
async def my_grants(
    storage_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    storage = await storage_service.get_storage_or_404(db, storage_id)
    is_owner = storage.owner_id == current_user.id
    grants = await grant_service.list_user_storage_grants(db, current_user.id, storage_id)
    return {"is_owner": is_owner, "grants": [g.grant_type.value for g in grants]}


@router.put("/{storage_id}/policy", response_model=StoragePolicyRead)
async def update_policy(
    storage_id: uuid.UUID,
    payload: StoragePolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_storage_grant(StorageGrantType.STORAGE_MANAGE_ACCESS)),
) -> StoragePolicyRead:
    policy = await storage_service.update_policy(db, storage_id, payload)
    return StoragePolicyRead.model_validate(policy)
