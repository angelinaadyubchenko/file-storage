import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "ivan@example.com", "password": "secret123"}}
    )

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "ivan@example.com", "password": "secret123"}}
    )

    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "2f6c9b7e-3d4a-4b1c-8e5f-1a2b3c4d5e6f",
                "email": "ivan@example.com",
                "created_at": "2026-06-25T12:00:00Z",
            }
        },
    )

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIuLi4ifQ.sig",
                "token_type": "bearer",
            }
        }
    )

    access_token: str
    token_type: str = "bearer"
