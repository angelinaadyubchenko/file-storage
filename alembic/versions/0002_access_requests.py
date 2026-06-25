from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_access_requests"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


access_request_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="access_request_status", create_type=False
)
global_grant_type = postgresql.ENUM(
    "CAN_CREATE_GLOBAL_STORAGE", "CAN_MANAGE_USERS", name="global_grant_type", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    access_request_status.create(bind, checkfirst=True)

    op.create_table(
        "access_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grant_type", global_grant_type, nullable=False),
        sa.Column("status", access_request_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_access_requests_status", "access_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_table("access_requests")

    bind = op.get_bind()
    access_request_status.drop(bind, checkfirst=True)
