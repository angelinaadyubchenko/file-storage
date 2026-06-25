import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.exceptions import PermissionDenied, StorageNotFound
from app.models.enums import GlobalGrantType, StorageType
from app.models.file import File
from app.models.grant import StorageGrant
from app.models.storage import Storage, StoragePolicy
from app.models.user import User
from app.schemas.storage import StorageCreate, StoragePolicyUpdate
from app.services import grant_service


async def get_storage(db: AsyncSession, storage_id: uuid.UUID) -> Storage | None:
    result = await db.execute(
        select(Storage).options(selectinload(Storage.policy)).where(Storage.id == storage_id)
    )
    return result.scalar_one_or_none()


async def get_storage_or_404(db: AsyncSession, storage_id: uuid.UUID) -> Storage:
    storage = await get_storage(db, storage_id)
    if storage is None:
        raise StorageNotFound()
    return storage


async def get_storage_policy(db: AsyncSession, storage_id: uuid.UUID) -> StoragePolicy | None:
    result = await db.execute(
        select(StoragePolicy).where(StoragePolicy.storage_id == storage_id)
    )
    return result.scalar_one_or_none()


async def get_used_bytes(db: AsyncSession, storage_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(File.size), 0)).where(
            File.storage_id == storage_id, File.deleted_at.is_(None)
        )
    )
    return int(result.scalar_one())


async def lock_storage(db: AsyncSession, storage_id: uuid.UUID) -> None:
    await db.execute(select(Storage.id).where(Storage.id == storage_id).with_for_update())


async def create_storage(
    db: AsyncSession, payload: StorageCreate, owner: User
) -> Storage:
    if payload.type == StorageType.GLOBAL and not await grant_service.has_global_grant(
        db, user_id=owner.id, grant_type=GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE
    ):
        raise PermissionDenied("Missing required global grant: CAN_CREATE_GLOBAL_STORAGE")

    storage = Storage(name=payload.name, type=payload.type, owner_id=owner.id)
    db.add(storage)
    await db.flush()

    requested = payload.policy or StoragePolicyUpdate()
    policy = StoragePolicy(
        storage_id=storage.id,
        max_file_size=requested.max_file_size or settings.DEFAULT_MAX_FILE_SIZE,
        max_storage_size=requested.max_storage_size or settings.DEFAULT_MAX_STORAGE_SIZE,
        allowed_mime_types=requested.allowed_mime_types,
        allowed_extensions=requested.allowed_extensions,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(storage, attribute_names=["policy"])
    return storage


async def rename_storage(db: AsyncSession, storage_id: uuid.UUID, name: str) -> Storage:
    storage = await get_storage_or_404(db, storage_id)
    storage.name = name
    await db.commit()
    await db.refresh(storage, attribute_names=["policy"])
    return storage


async def update_policy(
    db: AsyncSession, storage_id: uuid.UUID, payload: StoragePolicyUpdate
) -> StoragePolicy:
    policy = await get_storage_policy(db, storage_id)
    if policy is None:
        raise StorageNotFound("Storage policy not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(policy, field, value)

    await db.commit()
    await db.refresh(policy)
    return policy


async def list_accessible_storages(db: AsyncSession, user: User) -> list[Storage]:
    granted_subquery = select(StorageGrant.storage_id).where(StorageGrant.user_id == user.id)
    result = await db.execute(
        select(Storage)
        .options(selectinload(Storage.policy))
        .where(or_(Storage.owner_id == user.id, Storage.id.in_(granted_subquery)))
        .distinct()
    )
    return list(result.scalars().all())
