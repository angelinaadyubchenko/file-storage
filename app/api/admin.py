import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_global_grant
from app.api.openapi import error_responses
from app.db.session import get_db
from app.exceptions import AuthenticationError, GrantNotFound, NotFound, PermissionDenied
from app.models.enums import GlobalGrantType
from app.models.user import User
from app.schemas.grant import GlobalGrantCreate, GlobalGrantRead
from app.services import grant_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/grants",
    response_model=GlobalGrantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Выдать глобальный грант",
    description=(
        "Выдаёт пользователю глобальное право (например, на создание глобальных хранилищ "
        "или управление пользователями). Требуется глобальное право CAN_MANAGE_USERS. "
        "Если право уже выдано — возвращается имеющееся со статусом 200."
    ),
    responses={
        **error_responses(AuthenticationError, PermissionDenied, NotFound),
        200: {"model": GlobalGrantRead, "description": "Право уже было выдано, возвращается имеющееся"},
    },
)
async def issue_global_grant(
    payload: GlobalGrantCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_global_grant(GlobalGrantType.CAN_MANAGE_USERS)),
) -> GlobalGrantRead:
    grant, created = await grant_service.grant_global_access(
        db, user_id=payload.user_id, grant_type=payload.grant_type
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return grant


@router.delete(
    "/grants",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать глобальный грант",
    description="Отзывает у пользователя глобальное право. Требуется глобальное право CAN_MANAGE_USERS.",
    responses=error_responses(AuthenticationError, PermissionDenied, GrantNotFound),
)
async def revoke_global_grant(
    user_id: uuid.UUID = Query(...),
    grant_type: GlobalGrantType = Query(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_global_grant(GlobalGrantType.CAN_MANAGE_USERS)),
) -> None:
    await grant_service.revoke_global_access(db, user_id=user_id, grant_type=grant_type)
