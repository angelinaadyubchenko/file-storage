from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.openapi import error_responses
from app.core.config import settings
from app.db.session import get_db
from app.exceptions import AuthenticationError, EmailAlreadyRegistered, InvalidCredentials
from app.models.enums import GlobalGrantType
from app.models.user import User
from app.schemas.access_request import MeAccess
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services import access_request_service, auth_service, grant_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description=(
        "Создаёт новый аккаунт. Хранилища пользователь создаёт сам после входа "
        "(POST /storages). Email должен быть уникальным, пароль — от 6 символов."
    ),
    responses=error_responses(EmailAlreadyRegistered),
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    user = await auth_service.register_user(db, email=payload.email, password=payload.password)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Вход (получение JWT)",
    description=(
        "Проверяет email и пароль, возвращает access-токен. Токен передаётся в заголовке "
        "Authorization: Bearer <token> для доступа к защищённым эндпоинтам."
    ),
    responses=error_responses(InvalidCredentials),
)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    access_token = await auth_service.authenticate(db, email=payload.email, password=payload.password)
    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь",
    description="Возвращает данные пользователя, которому принадлежит переданный токен.",
    responses=error_responses(AuthenticationError),
)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


@router.get(
    "/me/access",
    response_model=MeAccess,
    summary="Права текущего пользователя",
    description=(
        "Возвращает флаги: может ли пользователь создавать глобальные хранилища, "
        "является ли админом (CAN_MANAGE_USERS) и есть ли у него ожидающая заявка."
    ),
    responses=error_responses(AuthenticationError),
)
async def my_access(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeAccess:
    can_create = await grant_service.has_global_grant(
        db, user_id=current_user.id, grant_type=GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE
    )
    can_manage = current_user.email == settings.ADMIN_EMAIL
    pending = await access_request_service.get_pending_request(
        db, current_user.id, GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE
    )
    return MeAccess(
        can_create_global_storage=can_create,
        can_manage_users=can_manage,
        pending_request=pending is not None,
    )
