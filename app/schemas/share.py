import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShareTokenCreate(BaseModel):
    expires_in_hours: int = Field(default=24, gt=0, le=24 * 365)
    max_downloads: int | None = Field(default=None, gt=0)


class ShareTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    file_id: uuid.UUID
    created_by: uuid.UUID
    expires_at: datetime
    max_downloads: int | None
    downloads_count: int
    revoked: bool
    created_at: datetime
