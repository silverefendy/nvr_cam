"""Small helper for writing admin/security audit entries."""
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.models.audit_log import AuditLog

logger = get_logger(__name__, service="audit")


async def write_audit_log(
    db: AsyncSession,
    *,
    action: str,
    user_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                ip_address=ip_address,
            )
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.warning(f"Failed to write audit log: {exc}")


async def list_audit_logs(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(min(max(limit, 1), 200))
    )
    return result.scalars().all()
