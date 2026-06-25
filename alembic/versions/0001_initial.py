from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


storage_type = postgresql.ENUM(
    "personal", "global", name="storage_type", create_type=False
)
global_grant_type = postgresql.ENUM(
    "CAN_CREATE_GLOBAL_STORAGE", "CAN_MANAGE_USERS", name="global_grant_type", create_type=False
)
storage_grant_type = postgresql.ENUM(
    "STORAGE_READ",
    "STORAGE_WRITE",
    "STORAGE_DELETE",
    "STORAGE_MANAGE_ACCESS",
    name="storage_grant_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    storage_type.create(bind, checkfirst=True)
    global_grant_type.create(bind, checkfirst=True)
    storage_grant_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "storages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", storage_type, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "storage_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("storage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("max_file_size", sa.BigInteger(), nullable=False),
        sa.Column("max_storage_size", sa.BigInteger(), nullable=False),
        sa.Column("allowed_mime_types", postgresql.JSONB(), nullable=True),
        sa.Column("allowed_extensions", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("storage_id", name="uq_storage_policies_storage_id"),
    )

    op.create_table(
        "global_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grant_type", global_grant_type, nullable=False),
        sa.UniqueConstraint("user_id", "grant_type", name="uq_global_grant"),
    )

    op.create_table(
        "storage_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("grant_type", storage_grant_type, nullable=False),
        sa.UniqueConstraint("user_id", "storage_id", "grant_type", name="uq_storage_grant"),
    )

    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("storage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("storages.id"), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_files_storage_id", "files", ["storage_id"])

    op.create_table(
        "file_share_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_downloads", sa.Integer(), nullable=True),
        sa.Column("downloads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token", name="uq_file_share_tokens_token"),
    )
    op.create_index("ix_file_share_tokens_token", "file_share_tokens", ["token"])


def downgrade() -> None:
    op.drop_table("file_share_tokens")
    op.drop_index("ix_files_storage_id", table_name="files")
    op.drop_table("files")
    op.drop_table("storage_grants")
    op.drop_table("global_grants")
    op.drop_table("storage_policies")
    op.drop_table("storages")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    storage_grant_type.drop(bind, checkfirst=True)
    global_grant_type.drop(bind, checkfirst=True)
    storage_type.drop(bind, checkfirst=True)
