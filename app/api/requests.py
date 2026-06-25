import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.api.openapi import error_responses
from app.db.session import get_db
from app.exceptions import AuthenticationError, Conflict, NotFound, PermissionDenied
from app.models.access_request import AccessRequest
from app.models.enums import AccessRequestStatus
from app.models.user import User
from app.schemas.access_request import AccessRequestCreate, AccessRequestRead
from app.services import access_request_service

router = APIRouter(tags=["access-requests"])


def _to_read(request: AccessRequest, email: str | None = None) -> AccessRequestRead:
    return AccessRequestRead(
        id=request.id,
        user_id=request.user_id,
        user_email=email,
        grant_type=request.grant_type,
        status=request.status,
        created_at=request.created_at,
    )


@router.post(
    "/access-requests",
    response_model=AccessRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Запросить право",
    description=(
        "Создаёт заявку на выдачу глобального права (по умолчанию CAN_CREATE_GLOBAL_STORAGE). "
        "Если право уже есть — 409. Повторная заявка не создаётся: возвращается текущая."
    ),
    responses=error_responses(AuthenticationError, Conflict),
)
async def create_access_request(
    payload: AccessRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccessRequestRead:
    request = await access_request_service.create_request(
        db, current_user, payload.grant_type
    )
    return _to_read(request, current_user.email)


@router.get(
    "/admin/access-requests",
    response_model=list[AccessRequestRead],
    summary="Список заявок (ожидающие)",
    description="Возвращает заявки в статусе «ожидает». Требуется глобальное право CAN_MANAGE_USERS.",
    responses=error_responses(AuthenticationError, PermissionDenied),
)
async def list_access_requests(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[AccessRequestRead]:
    rows = await access_request_service.list_requests(db, status=AccessRequestStatus.PENDING)
    return [_to_read(request, email) for request, email in rows]


@router.post(
    "/admin/access-requests/{request_id}/approve",
    response_model=AccessRequestRead,
    summary="Одобрить заявку",
    description="Одобряет заявку и выдаёт запрошенное право. Требуется CAN_MANAGE_USERS.",
    responses=error_responses(AuthenticationError, PermissionDenied, NotFound, Conflict),
)
async def approve_access_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AccessRequestRead:
    request = await access_request_service.approve_request(db, request_id, admin)
    return _to_read(request)


@router.post(
    "/admin/access-requests/{request_id}/reject",
    response_model=AccessRequestRead,
    summary="Отклонить заявку",
    description="Отклоняет заявку без выдачи права. Требуется CAN_MANAGE_USERS.",
    responses=error_responses(AuthenticationError, PermissionDenied, NotFound, Conflict),
)
async def reject_access_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AccessRequestRead:
    request = await access_request_service.reject_request(db, request_id, admin)
    return _to_read(request)
