import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccessRequestStatus, GlobalGrantType


class AccessRequestCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"grant_type": "CAN_CREATE_GLOBAL_STORAGE"}}
    )

    grant_type: GlobalGrantType = GlobalGrantType.CAN_CREATE_GLOBAL_STORAGE


class AccessRequestRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b",
                "user_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "user_email": "ivan@example.com",
                "grant_type": "CAN_CREATE_GLOBAL_STORAGE",
                "status": "pending",
                "created_at": "2026-06-25T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    grant_type: GlobalGrantType
    status: AccessRequestStatus
    created_at: datetime


class MeAccess(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "can_create_global_storage": False,
                "can_manage_users": False,
                "pending_request": True,
            }
        }
    )

    can_create_global_storage: bool
    can_manage_users: bool
    pending_request: bool
