import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_audit_logger
from app.exceptions import GrantNotFound, NotFound, PermissionDenied, StorageNotFound
from app.models.enums import GlobalGrantType, StorageGrantType
from app.models.grant import GlobalGrant, StorageGrant
from app.models.storage import Storage
from app.models.user import User

audit = get_audit_logger()


async def has_global_grant(
    db: AsyncSession, user_id: uuid.UUID, grant_type: GlobalGrantType
) -> bool:
    result = await db.execute(
        select(GlobalGrant.id).where(
            GlobalGrant.user_id == user_id, GlobalGrant.grant_type == grant_type
        )
    )
    return result.first() is not None


async def has_storage_grant(
    db: AsyncSession,
    user_id: uuid.UUID,
    storage_id: uuid.UUID,
    grant_type: StorageGrantType,
) -> bool:
    result = await db.execute(
        select(StorageGrant.id).where(
            StorageGrant.user_id == user_id,
            StorageGrant.storage_id == storage_id,
            StorageGrant.grant_type == grant_type,
        )
    )
    return result.first() is not None


async def grant_storage_access(
    db: AsyncSession,
    storage_id: uuid.UUID,
    target_user_id: uuid.UUID,
    grant_type: StorageGrantType,
    granted_by: User,
) -> tuple[StorageGrant, bool]:
    storage = await db.get(Storage, storage_id)
    if storage is None:
        raise StorageNotFound()

    # Owner has full authority. A non-owner with STORAGE_MANAGE_ACCESS may invite
    # others as readers/writers/deleters, but must not be able to escalate: only
    # the owner can hand out STORAGE_MANAGE_ACCESS, and a manager cannot grant
    # rights to themselves.
    if storage.owner_id != granted_by.id:
        if grant_type == StorageGrantType.STORAGE_MANAGE_ACCESS:
            raise PermissionDenied("Only the storage owner can delegate STORAGE_MANAGE_ACCESS")
        if target_user_id == granted_by.id:
            raise PermissionDenied("You cannot grant rights to yourself")

    target = await db.get(User, target_user_id)
    if target is None:
        raise NotFound("Target user not found")

    existing = await db.execute(
        select(StorageGrant).where(
            StorageGrant.user_id == target_user_id,
            StorageGrant.storage_id == storage_id,
            StorageGrant.grant_type == grant_type,
        )
    )
    grant = existing.scalar_one_or_none()
    if grant is not None:
        return grant, False

    grant = StorageGrant(
        user_id=target_user_id, storage_id=storage_id, grant_type=grant_type
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)

    audit.info(
        "grant_issued storage_id=%s target_user=%s grant=%s by=%s",
        storage_id, target_user_id, grant_type.value, granted_by.id,
    )
    return grant, True


async def list_storage_grants(
    db: AsyncSession, storage_id: uuid.UUID
) -> list[StorageGrant]:
    result = await db.execute(
        select(StorageGrant).where(StorageGrant.storage_id == storage_id)
    )
    return list(result.scalars().all())


async def list_user_storage_grants(
    db: AsyncSession, user_id: uuid.UUID, storage_id: uuid.UUID
) -> list[StorageGrant]:
    result = await db.execute(
        select(StorageGrant).where(
            StorageGrant.user_id == user_id, StorageGrant.storage_id == storage_id
        )
    )
    return list(result.scalars().all())


async def revoke_storage_access(
    db: AsyncSession,
    storage_id: uuid.UUID,
    target_user_id: uuid.UUID,
    grant_type: StorageGrantType | None,
    revoked_by: User,
) -> int:
    storage = await db.get(Storage, storage_id)
    if storage is None:
        raise StorageNotFound()

    # Same asymmetry as granting: a non-owner manager may take away ordinary
    # rights, but revoking management access (or wiping every grant at once) is
    # reserved for the owner.
    if storage.owner_id != revoked_by.id and (
        grant_type is None or grant_type == StorageGrantType.STORAGE_MANAGE_ACCESS
    ):
        raise PermissionDenied("Only the storage owner can revoke management access or all grants")

    query = select(StorageGrant).where(
        StorageGrant.user_id == target_user_id,
        StorageGrant.storage_id == storage_id,
    )
    if grant_type is not None:
        query = query.where(StorageGrant.grant_type == grant_type)

    result = await db.execute(query)
    grants = list(result.scalars().all())
    if not grants:
        raise GrantNotFound()

    for grant in grants:
        await db.delete(grant)
    await db.commit()

    audit.info(
        "grant_revoked storage_id=%s target_user=%s grant=%s count=%s by=%s",
        storage_id, target_user_id, grant_type.value if grant_type else "ALL",
        len(grants), revoked_by.id,
    )
    return len(grants)


async def grant_global_access(
    db: AsyncSession, user_id: uuid.UUID, grant_type: GlobalGrantType
) -> tuple[GlobalGrant, bool]:
    target = await db.get(User, user_id)
    if target is None:
        raise NotFound("Target user not found")

    existing = await db.execute(
        select(GlobalGrant).where(
            GlobalGrant.user_id == user_id, GlobalGrant.grant_type == grant_type
        )
    )
    grant = existing.scalar_one_or_none()
    if grant is not None:
        return grant, False

    grant = GlobalGrant(user_id=user_id, grant_type=grant_type)
    db.add(grant)
    await db.commit()
    await db.refresh(grant)

    audit.info("global_grant_issued user=%s grant=%s", user_id, grant_type.value)
    return grant, True


async def revoke_global_access(
    db: AsyncSession, user_id: uuid.UUID, grant_type: GlobalGrantType
) -> int:
    result = await db.execute(
        select(GlobalGrant).where(
            GlobalGrant.user_id == user_id, GlobalGrant.grant_type == grant_type
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise GrantNotFound()

    await db.delete(grant)
    await db.commit()
    audit.info("global_grant_revoked user=%s grant=%s", user_id, grant_type.value)
    return 1
