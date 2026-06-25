import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import GlobalGrantType, StorageGrantType


class GrantCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_user_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "grant_type": "STORAGE_READ",
            }
        }
    )

    target_user_id: uuid.UUID
    grant_type: StorageGrantType


class GrantRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "b3d4e5f6-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
                "user_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "storage_id": "7c1a2b3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
                "grant_type": "STORAGE_READ",
            }
        },
    )

    id: uuid.UUID
    user_id: uuid.UUID
    storage_id: uuid.UUID
    grant_type: StorageGrantType


class GlobalGrantCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "grant_type": "CAN_CREATE_GLOBAL_STORAGE",
            }
        }
    )

    user_id: uuid.UUID
    grant_type: GlobalGrantType


class GlobalGrantRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "c4e5f6a7-8b9c-4d0e-9f1a-2b3c4d5e6f7a",
                "user_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "grant_type": "CAN_CREATE_GLOBAL_STORAGE",
            }
        },
    )

    id: uuid.UUID
    user_id: uuid.UUID
    grant_type: GlobalGrantType
