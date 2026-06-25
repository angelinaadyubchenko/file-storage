import uuid

from fastapi import Depends, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.exceptions import AuthenticationError, PermissionDenied, StorageNotFound
from app.models.enums import GlobalGrantType, StorageGrantType
from app.models.user import User
from app.services import auth_service, grant_service, storage_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise AuthenticationError("Missing authentication token")

    subject = decode_access_token(token)
    if subject is None:
        raise AuthenticationError("Invalid or expired token")

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise AuthenticationError("Invalid token subject")

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise AuthenticationError("User no longer exists")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.email != settings.ADMIN_EMAIL:
        raise PermissionDenied("Only the administrator can perform this action")
    return current_user


async def assert_storage_access(
    db: AsyncSession,
    user: User,
    storage_id: uuid.UUID,
    grant_type: StorageGrantType,
) -> None:
    storage = await storage_service.get_storage(db, storage_id)
    if storage is None:
        raise StorageNotFound()
    if storage.owner_id == user.id:
        return
    if not await grant_service.has_storage_grant(
        db, user_id=user.id, storage_id=storage_id, grant_type=grant_type
    ):
        raise PermissionDenied(f"Missing required grant: {grant_type.value}")


def require_storage_grant(grant_type: StorageGrantType):

    async def dependency(
        storage_id: uuid.UUID = Path(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        await assert_storage_access(db, current_user, storage_id, grant_type)
        return current_user

    return dependency


def require_global_grant(grant_type: GlobalGrantType):

    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await grant_service.has_global_grant(
            db, user_id=current_user.id, grant_type=grant_type
        ):
            raise PermissionDenied(f"Missing required global grant: {grant_type.value}")
        return current_user

    return dependency
