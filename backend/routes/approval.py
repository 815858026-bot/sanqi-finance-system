from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MaterialOutbound, MaterialOutboundStatus, User, UserRole, get_db
from security import get_current_user, require_roles


router = APIRouter(prefix="/api/approval", tags=["审批流程"])


@router.get("/pending")
def pending_approvals(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.OFFICE_ADMIN, UserRole.PARTNER)),
    db: Session = Depends(get_db),
):
    pending_outbounds = db.scalars(
        select(MaterialOutbound).where(MaterialOutbound.status == MaterialOutboundStatus.PENDING).order_by(MaterialOutbound.created_at.desc())
    ).all()
    return {
        "material_outbounds": [
            {
                "id": item.id,
                "project_name": item.project_name,
                "requester_name": item.requester_name,
                "issue_date": item.issue_date,
                "status": item.status.value,
                "items": [
                    {"material_name": row.material_name, "quantity": row.quantity}
                    for row in item.items
                ],
            }
            for item in pending_outbounds
        ]
    }
