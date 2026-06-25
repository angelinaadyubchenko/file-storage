import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.exceptions import EmailAlreadyRegistered, InvalidCredentials
from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    if await get_user_by_email(db, email):
        raise EmailAlreadyRegistered()

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
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
