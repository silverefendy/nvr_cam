"""Partition recordings and motion_events by monthly range on created_at

Revision ID: 003
Revises: 002
Create Date: 2026-07-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_partitioned(table_name: str) -> bool:
    """Check if table is already partitioned."""
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table(table_name):
        return False
    res = bind.execute(sa.text(
        f"SELECT 1 FROM pg_partitioned_table WHERE partrelid = '{table_name}'::regclass"
    )).fetchone()
    return res is not None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return insp.has_table(table_name)


def upgrade() -> None:
    # 1. Check if recordings is already partitioned
    if is_partitioned("recordings"):
        print("Table 'recordings' is already partitioned. Skipping upgrade.")
        return

    print("Converting 'recordings' and 'motion_events' to monthly partitioned tables...")

    # --- RECOVERY: handle DB left in a half-migrated state ---
    # If the old container crashed after rename but before DROP, the _old tables
    # already exist and the new partitioned tables may already be created too.
    # We detect this and skip the steps that already completed.

    recordings_old_exists = table_exists("recordings_old")
    motion_events_old_exists = table_exists("motion_events_old")

    # 2. Rename existing tables to temp names (skip if already done)
    if not motion_events_old_exists:
        op.rename_table("motion_events", "motion_events_old")
    if not recordings_old_exists:
        op.rename_table("recordings", "recordings_old")

    # 4. Create partitioned recordings table (skip if already created)
    if not table_exists("recordings"):
        op.execute("""
            CREATE TABLE recordings (
                id BIGINT NOT NULL DEFAULT nextval('recordings_id_seq'),
                camera_id VARCHAR(20) REFERENCES cameras(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                file_size_mb FLOAT,
                started_at TIMESTAMPTZ NOT NULL,
                ended_at TIMESTAMPTZ,
                duration_s INTEGER,
                codec VARCHAR(10) NOT NULL DEFAULT 'H265',
                is_protected BOOLEAN NOT NULL DEFAULT false,
                is_encoded_av1 BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (id, created_at)
            ) PARTITION BY RANGE (created_at);
        """)

        # 5. Create monthly partitions for recordings (from 2025 to 2027)
        for year in [2025, 2026, 2027]:
            for month in range(1, 13):
                partition_name = f"recordings_y{year}m{month:02d}"
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
                op.execute(f"CREATE TABLE {partition_name} PARTITION OF recordings FOR VALUES FROM ('{start_date}') TO ('{end_date}')")

        op.execute("CREATE TABLE recordings_default PARTITION OF recordings DEFAULT;")

        # 6. Copy existing recordings data
        op.execute("""
            INSERT INTO recordings (id, camera_id, file_path, file_size_mb, started_at, ended_at, duration_s, codec, is_protected, is_encoded_av1, created_at)
            SELECT id, camera_id, file_path, file_size_mb, started_at, ended_at, duration_s, codec, is_protected, is_encoded_av1, created_at FROM recordings_old;
        """)

    # 7. Create partitioned motion_events table (skip if already created)
    if not table_exists("motion_events"):
        op.execute("""
            CREATE TABLE motion_events (
                id BIGINT NOT NULL DEFAULT nextval('motion_events_id_seq'),
                camera_id VARCHAR(20) REFERENCES cameras(id) ON DELETE CASCADE,
                recording_id BIGINT,
                zone_name VARCHAR(50),
                started_at TIMESTAMPTZ NOT NULL,
                ended_at TIMESTAMPTZ,
                duration_s INTEGER,
                snapshot_path TEXT,
                video_offset_s INTEGER,
                severity SMALLINT NOT NULL DEFAULT 1,
                notified BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (id, created_at)
            ) PARTITION BY RANGE (created_at);
        """)

        # 8. Create monthly partitions for motion_events (from 2025 to 2027)
        for year in [2025, 2026, 2027]:
            for month in range(1, 13):
                partition_name = f"motion_events_y{year}m{month:02d}"
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
                op.execute(f"CREATE TABLE {partition_name} PARTITION OF motion_events FOR VALUES FROM ('{start_date}') TO ('{end_date}')")

        op.execute("CREATE TABLE motion_events_default PARTITION OF motion_events DEFAULT;")

        # 9. Copy existing motion_events data
        op.execute("""
            INSERT INTO motion_events (id, camera_id, recording_id, zone_name, started_at, ended_at, duration_s, snapshot_path, video_offset_s, severity, notified, created_at)
            SELECT id, camera_id, recording_id, zone_name, started_at, ended_at, duration_s, snapshot_path, video_offset_s, severity, notified, created_at FROM motion_events_old;
        """)

    # 10. Transfer sequence ownership away from _old tables so DROP succeeds,
    #     then drop the old tables.
    #     OWNED BY NONE detaches the sequence from any table; the new partitioned
    #     tables reference the sequence via DEFAULT nextval(...) which is enough.
    if table_exists("motion_events_old"):
        op.execute("ALTER SEQUENCE motion_events_id_seq OWNED BY NONE;")
        op.execute("DROP TABLE motion_events_old;")

    if table_exists("recordings_old"):
        op.execute("ALTER SEQUENCE recordings_id_seq OWNED BY NONE;")
        op.execute("DROP TABLE recordings_old;")

    # 11. Create indexes on the new partitioned tables (skip if already exist)
    bind = op.get_bind()
    insp = inspect(bind)
    existing_indexes = {idx['name'] for idx in insp.get_indexes('recordings')}
    if "ix_recordings_camera_id" not in existing_indexes:
        op.create_index("ix_recordings_camera_id", "recordings", ["camera_id"])
    if "ix_recordings_started_at" not in existing_indexes:
        op.create_index("ix_recordings_started_at", "recordings", ["started_at"])

    existing_indexes = {idx['name'] for idx in insp.get_indexes('motion_events')}
    if "ix_motion_events_camera_id" not in existing_indexes:
        op.create_index("ix_motion_events_camera_id", "motion_events", ["camera_id"])
    if "ix_motion_events_started_at" not in existing_indexes:
        op.create_index("ix_motion_events_started_at", "motion_events", ["started_at"])

    print("Partitioning migration completed successfully.")


def downgrade() -> None:
    if not is_partitioned("recordings"):
        print("Table 'recordings' is not partitioned. Skipping downgrade.")
        return

    print("Reverting monthly partitioning...")

    op.rename_table("motion_events", "motion_events_part")
    op.rename_table("recordings", "recordings_part")

    op.create_table(
        'recordings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('camera_id', sa.String(20), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False, unique=True),
        sa.Column('file_size_mb', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True),
        sa.Column('codec', sa.String(10), nullable=False, server_default='H265'),
        sa.Column('is_protected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_encoded_av1', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_recordings_camera_id'), 'recordings', ['camera_id'])
    op.create_index(op.f('ix_recordings_started_at'), 'recordings', ['started_at'])

    op.execute("""
        INSERT INTO recordings (id, camera_id, file_path, file_size_mb, started_at, ended_at, duration_s, codec, is_protected, is_encoded_av1, created_at)
        SELECT id, camera_id, file_path, file_size_mb, started_at, ended_at, duration_s, codec, is_protected, is_encoded_av1, created_at FROM recordings_part;
    """)

    op.create_table(
        'motion_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('camera_id', sa.String(20), sa.ForeignKey('cameras.id'), nullable=False),
        sa.Column('recording_id', sa.BigInteger(), sa.ForeignKey('recordings.id'), nullable=True),
        sa.Column('zone_name', sa.String(50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
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

    op.execute("""
        INSERT INTO motion_events (id, camera_id, recording_id, zone_name, started_at, ended_at, duration_s, snapshot_path, video_offset_s, severity, notified, created_at)
        SELECT id, camera_id, recording_id, zone_name, started_at, ended_at, duration_s, snapshot_path, video_offset_s, severity, notified, created_at FROM motion_events_part;
    """)

    op.execute("ALTER SEQUENCE motion_events_id_seq OWNED BY NONE;")
    op.execute("ALTER SEQUENCE recordings_id_seq OWNED BY NONE;")
    op.execute("DROP TABLE motion_events_part CASCADE;")
    op.execute("DROP TABLE recordings_part CASCADE;")
