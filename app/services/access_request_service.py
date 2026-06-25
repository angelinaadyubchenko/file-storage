import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_audit_logger
from app.exceptions import Conflict, NotFound
from app.models.access_request import AccessRequest
from app.models.enums import AccessRequestStatus, GlobalGrantType
from app.models.user import User
from app.services import grant_service

audit = get_audit_logger()


async def get_pending_request(
    db: AsyncSession, user_id: uuid.UUID, grant_type: GlobalGrantType
) -> AccessRequest | None:
    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.user_id == user_id,
            AccessRequest.grant_type == grant_type,
            AccessRequest.status == AccessRequestStatus.PENDING,
        )
    )
    return result.scalar_one_or_none()


async def create_request(
    db: AsyncSession, user: User, grant_type: GlobalGrantType
) -> AccessRequest:
    if await grant_service.has_global_grant(db, user_id=user.id, grant_type=grant_type):
        raise Conflict("You already have this right")

    existing = await get_pending_request(db, user.id, grant_type)
    if existing is not None:
        return existing

    request = AccessRequest(
        user_id=user.id, grant_type=grant_type, status=AccessRequestStatus.PENDING
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    audit.info("access_request_created user=%s grant=%s", user.id, grant_type.value)
    return request


async def list_requests(
    db: AsyncSession, status: AccessRequestStatus | None = None
) -> list[tuple[AccessRequest, str]]:
    query = select(AccessRequest, User.email).join(User, User.id == AccessRequest.user_id)
    if status is not None:
        query = query.where(AccessRequest.status == status)
    query = query.order_by(AccessRequest.created_at.desc())
    result = await db.execute(query)
    return [(row[0], row[1]) for row in result.all()]


async def _get_or_404(db: AsyncSession, request_id: uuid.UUID) -> AccessRequest:
    request = await db.get(AccessRequest, request_id)
    if request is None:
        raise NotFound("Access request not found")
    return request


async def approve_request(
    db: AsyncSession, request_id: uuid.UUID, admin: User
) -> AccessRequest:
    request = await _get_or_404(db, request_id)
    if request.status != AccessRequestStatus.PENDING:
        raise Conflict("Request has already been decided")

    await grant_service.grant_global_access(
        db, user_id=request.user_id, grant_type=request.grant_type
    )
    request.status = AccessRequestStatus.APPROVED
    request.decided_by = admin.id
    request.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(request)
    audit.info("access_request_approved id=%s by=%s", request.id, admin.id)
    return request


async def reject_request(
    db: AsyncSession, request_id: uuid.UUID, admin: User
) -> AccessRequest:
    request = await _get_or_404(db, request_id)
    if request.status != AccessRequestStatus.PENDING:
        raise Conflict("Request has already been decided")

    request.status = AccessRequestStatus.REJECTED
    request.decided_by = admin.id
    request.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(request)
    audit.info("access_request_rejected id=%s by=%s", request.id, admin.id)
    return request
