"""Router: /api/v1/audit-logs — admin audit trail."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_role
from backend.db.base import get_db
from backend.db.models.user import User
from backend.services.audit import list_audit_logs

router = APIRouter(tags=["audit-logs"])


@router.get("")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    rows = await list_audit_logs(db, limit=limit, offset=offset)
    return [
        {
            "id": row.id,
            "user_id": str(row.user_id) if row.user_id else None,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "detail": row.detail,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]
