import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GlobalGrantType, StorageGrantType


class GlobalGrant(Base):
    __tablename__ = "global_grants"
    __table_args__ = (UniqueConstraint("user_id", "grant_type", name="uq_global_grant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    grant_type: Mapped[GlobalGrantType] = mapped_column(
        SAEnum(
            GlobalGrantType,
            name="global_grant_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="global_grants")  # noqa: F821


class StorageGrant(Base):
    __tablename__ = "storage_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "storage_id", "grant_type", name="uq_storage_grant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    storage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storages.id"), nullable=False
    )
    grant_type: Mapped[StorageGrantType] = mapped_column(
        SAEnum(
            StorageGrantType,
            name="storage_grant_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="storage_grants")  # noqa: F821
    storage: Mapped["Storage"] = relationship(back_populates="grants")  # noqa: F821
