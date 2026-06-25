from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.openapi import error_responses
from app.db.session import get_db
from app.exceptions import AuthenticationError, EmailAlreadyRegistered, InvalidCredentials
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description=(
        "Создаёт нового пользователя и автоматически его личное хранилище "
        "с политикой по умолчанию. Email должен быть уникальным, пароль — от 6 символов."
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
