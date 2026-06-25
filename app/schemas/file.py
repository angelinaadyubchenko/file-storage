import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                "storage_id": "7c1a2b3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
                "original_filename": "отчёт.pdf",
                "mime_type": "application/pdf",
                "size": 20480,
                "uploaded_by": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "created_at": "2026-06-25T12:00:00Z",
                "deleted_at": None,
            }
        },
    )

    id: uuid.UUID
    storage_id: uuid.UUID
    original_filename: str
    mime_type: str
    size: int
    uploaded_by: uuid.UUID
    created_at: datetime
    deleted_at: datetime | None = None
