"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(100), unique=True, nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create cameras table
    op.create_table(
        'cameras',
        sa.Column('id', sa.String(20), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('rtsp_main', sa.Text(), nullable=False),
        sa.Column('rtsp_sub', sa.Text(), nullable=True),
        sa.Column('storage_drive', sa.String(50), nullable=False),
        sa.Column('motion_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('segment_duration', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('status', sa.String(20), nullable=False, server_default='offline'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('config_json', postgresql.JSONB(), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create recordings table
    op.create_table(
        'recordings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('camera_id', sa.String(20), sa.ForeignKey('cameras.id'), nullable=False, index=True),
        sa.Column('file_path', sa.Text(), nullable=False, unique=True),
        sa.Column('file_size_mb', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True),
        sa.Column('codec', sa.String(10), nullable=False, server_default='H265'),
        sa.Column('is_protected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_encoded_av1', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_recordings_camera_id'), 'recordings', ['camera_id'])
    op.create_index(op.f('ix_recordings_started_at'), 'recordings', ['started_at'])

    # Create motion_events table
    op.create_table(
        'motion_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('camera_id', sa.String(20), sa.ForeignKey('cameras.id'), nullable=False, index=True),
        sa.Column('recording_id', sa.BigInteger(), sa.ForeignKey('recordings.id'), nullable=True),
        sa.Column('zone_name', sa.String(50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True),
        sa.Column('snapshot_path', sa.Text(), nullable=True),
        sa.Column('video_offset_s', sa.Integer(), nullable=True),
        sa.Column('severity', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('notified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_motion_events_camera_id'), 'motion_events', ['camera_id'])
    op.create_index(op.f('ix_motion_events_started_at'), 'motion_events', ['started_at'])

    # Create system_logs table
    op.create_table(
        'system_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('level', sa.String(10), nullable=False),
        sa.Column('service', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True),
    )
    op.create_index(op.f('ix_system_logs_created_at'), 'system_logs', ['created_at'])

    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('type', sa.String(30), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('status', sa.String(10), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create app_settings table
    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('app_settings')
    op.drop_table('notification_logs')
    op.drop_index(op.f('ix_system_logs_created_at'), table_name='system_logs')
    op.drop_table('system_logs')
    op.drop_index(op.f('ix_motion_events_started_at'), table_name='motion_events')
    op.drop_index(op.f('ix_motion_events_camera_id'), table_name='motion_events')
    op.drop_table('motion_events')
    op.drop_index(op.f('ix_recordings_started_at'), table_name='recordings')
    op.drop_index(op.f('ix_recordings_camera_id'), table_name='recordings')
    op.drop_table('recordings')
    op.drop_table('cameras')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
