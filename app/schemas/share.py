import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShareTokenCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"expires_in_hours": 24, "max_downloads": 5}}
    )

    expires_in_hours: int = Field(default=24, gt=0, le=24 * 365)
    max_downloads: int | None = Field(default=None, gt=0)


class ShareTokenRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "d5f6a7b8-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
                "token": "Q1w2E3r4T5y6U7i8O9p0aSdFgHjKlZxCvBnM",
                "file_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                "created_by": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "expires_at": "2026-06-26T12:00:00Z",
                "max_downloads": 5,
                "downloads_count": 0,
                "revoked": False,
                "created_at": "2026-06-25T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    token: str
    file_id: uuid.UUID
    created_by: uuid.UUID
    expires_at: datetime
    max_downloads: int | None
    downloads_count: int
    revoked: bool
    created_at: datetime
