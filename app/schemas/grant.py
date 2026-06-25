import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import GlobalGrantType, StorageGrantType


class GrantCreate(BaseModel):
    target_user_id: uuid.UUID
    grant_type: StorageGrantType


class GrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    storage_id: uuid.UUID
    grant_type: StorageGrantType


class GlobalGrantCreate(BaseModel):
    user_id: uuid.UUID
    grant_type: GlobalGrantType


class GlobalGrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    grant_type: GlobalGrantType
