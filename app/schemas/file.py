import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_id: uuid.UUID
    original_filename: str
    mime_type: str
    size: int
    uploaded_by: uuid.UUID
    created_at: datetime
    deleted_at: datetime | None = None
