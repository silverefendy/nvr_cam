"""Add audit logs table

Revision ID: 001b
Revises: 001
Create Date: 2026-07-26 00:00:01
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001b"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(80) NOT NULL,
            target_type VARCHAR(80) NULL,
            target_id VARCHAR(120) NULL,
            detail JSONB NULL,
            ip_address VARCHAR(64) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at "
        "ON audit_logs (created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id "
        "ON audit_logs (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_action "
        "ON audit_logs (action)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_user_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_created_at")
    op.execute("DROP TABLE IF EXISTS audit_logs")
