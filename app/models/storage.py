import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StorageType


class Storage(Base):
    __tablename__ = "storages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[StorageType] = mapped_column(
        SAEnum(StorageType, name="storage_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="storages", foreign_keys=[owner_id])  
    policy: Mapped["StoragePolicy"] = relationship(
        back_populates="storage", uselist=False, cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(back_populates="storage")  
    grants: Mapped[list["StorageGrant"]] = relationship(  
        back_populates="storage", cascade="all, delete-orphan"
    )


class StoragePolicy(Base):

    __tablename__ = "storage_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storages.id"), unique=True, nullable=False
    )
    max_file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_storage_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allowed_mime_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    allowed_extensions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    storage: Mapped["Storage"] = relationship(back_populates="policy")
