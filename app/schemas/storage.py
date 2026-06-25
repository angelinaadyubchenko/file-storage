import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StorageType


class StoragePolicyRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "max_file_size": 104857600,
                "max_storage_size": 1073741824,
                "allowed_mime_types": ["image/png", "application/pdf"],
                "allowed_extensions": [".png", ".pdf"],
            }
        },
    )

    max_file_size: int
    max_storage_size: int
    allowed_mime_types: list[str] | None = None
    allowed_extensions: list[str] | None = None


class StoragePolicyUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_file_size": 52428800,
                "max_storage_size": 1073741824,
                "allowed_mime_types": ["image/png", "image/jpeg"],
                "allowed_extensions": [".png", ".jpg"],
            }
        }
    )

    max_file_size: int | None = Field(default=None, gt=0)
    max_storage_size: int | None = Field(default=None, gt=0)
    allowed_mime_types: list[str] | None = None
    allowed_extensions: list[str] | None = None


class StorageCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Документы команды",
                "type": "global",
                "policy": {"max_file_size": 52428800, "allowed_extensions": [".pdf", ".docx"]},
            }
        }
    )

    name: str = Field(min_length=1, max_length=255)
    type: StorageType
    policy: StoragePolicyUpdate | None = None


class StorageRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "7c1a2b3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
                "name": "Личное хранилище",
                "type": "personal",
                "owner_id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "created_at": "2026-06-25T12:00:00Z",
                "policy": {
                    "max_file_size": 104857600,
                    "max_storage_size": 1073741824,
                    "allowed_mime_types": None,
                    "allowed_extensions": None,
                },
                "used_bytes": 2048,
            }
        },
    )

    id: uuid.UUID
    name: str
    type: StorageType
    owner_id: uuid.UUID
    created_at: datetime
    policy: StoragePolicyRead | None = None
    used_bytes: int | None = None
