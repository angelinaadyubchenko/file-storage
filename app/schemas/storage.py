import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StorageType


class StoragePolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_file_size: int
    max_storage_size: int
    allowed_mime_types: list[str] | None = None
    allowed_extensions: list[str] | None = None


class StoragePolicyUpdate(BaseModel):

    max_file_size: int | None = Field(default=None, gt=0)
    max_storage_size: int | None = Field(default=None, gt=0)
    allowed_mime_types: list[str] | None = None
    allowed_extensions: list[str] | None = None


class StorageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    policy: StoragePolicyUpdate | None = None


class StorageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: StorageType
    owner_id: uuid.UUID
    created_at: datetime
    policy: StoragePolicyRead | None = None
    used_bytes: int | None = None
