"""Add camera groups, schedule, and dual stream properties

Revision ID: 002
Revises: 001b
Create Date: 2026-07-26 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    """Helper: return an Inspector bound to the current migration connection."""
    from alembic import context as alembic_ctx
    if alembic_ctx.is_offline_mode():
        return None
    bind = op.get_bind()
    return inspect(bind)


def table_exists(name) -> bool:
    insp = _get_inspector()
    if insp is None:
        return False
    try:
        return insp.has_table(name)
    except Exception:
        return False


def column_exists(table, column) -> bool:
    insp = _get_inspector()
    if insp is None:
        return False
    try:
        columns = [c['name'] for c in insp.get_columns(table)]
        return column in columns
    except Exception:
        return False


def upgrade() -> None:
    # 1. Create camera_groups table if it does not exist
    if not table_exists("camera_groups"):
        op.create_table(
            'camera_groups',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('color', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        )

    # 2. Add columns to cameras table if they do not exist
    if not column_exists("cameras", "rtsp_url_main"):
        op.add_column("cameras", sa.Column("rtsp_url_main", sa.String(length=500), nullable=True))

    if not column_exists("cameras", "rtsp_url_sub"):
        op.add_column("cameras", sa.Column("rtsp_url_sub", sa.String(length=500), nullable=True))

    if not column_exists("cameras", "recording_schedule"):
        op.add_column("cameras", sa.Column("recording_schedule", sa.String(length=20), server_default="24h", nullable=False))

    if not column_exists("cameras", "schedule_start_time"):
        op.add_column("cameras", sa.Column("schedule_start_time", sa.String(length=5), nullable=True))

    if not column_exists("cameras", "schedule_end_time"):
        op.add_column("cameras", sa.Column("schedule_end_time", sa.String(length=5), nullable=True))

    if not column_exists("cameras", "schedule_days"):
        op.add_column("cameras", sa.Column("schedule_days", sa.String(length=50), nullable=True))

    if not column_exists("cameras", "group_id"):
        op.add_column("cameras", sa.Column("group_id", sa.Integer(), sa.ForeignKey("camera_groups.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    if column_exists("cameras", "group_id"):
        op.drop_column("cameras", "group_id")
    if column_exists("cameras", "schedule_days"):
        op.drop_column("cameras", "schedule_days")
    if column_exists("cameras", "schedule_end_time"):
        op.drop_column("cameras", "schedule_end_time")
    if column_exists("cameras", "schedule_start_time"):
        op.drop_column("cameras", "schedule_start_time")
    if column_exists("cameras", "recording_schedule"):
        op.drop_column("cameras", "recording_schedule")
    if column_exists("cameras", "rtsp_url_sub"):
        op.drop_column("cameras", "rtsp_url_sub")
    if column_exists("cameras", "rtsp_url_main"):
        op.drop_column("cameras", "rtsp_url_main")
    if table_exists("camera_groups"):
        op.drop_table("camera_groups")
