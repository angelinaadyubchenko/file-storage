from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.models.enums import StorageType
from app.models.storage import Storage, StoragePolicy
from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    if await get_user_by_email(db, email):
        raise EmailAlreadyRegistered()

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()

    storage = Storage(name="Personal storage", type=StorageType.PERSONAL, owner_id=user.id)
    db.add(storage)
    await db.flush()

    policy = StoragePolicy(
        storage_id=storage.id,
        max_file_size=settings.DEFAULT_MAX_FILE_SIZE,
        max_storage_size=settings.DEFAULT_MAX_STORAGE_SIZE,
        allowed_mime_types=None,
        allowed_extensions=None,
    )
    db.add(policy)

    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> str:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials()

    return create_access_token(
        subject=str(user.id), expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
