from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MaterialInbound, MaterialOutbound, OfficeExpense, ProjectPaymentPhase, User, get_db
from security import get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["财务看板"])


@router.get("/overview")
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payment_phases = db.scalars(select(ProjectPaymentPhase)).all()
    office_expenses = db.scalars(select(OfficeExpense)).all()
    material_inbounds = db.scalars(select(MaterialInbound)).all()
    material_outbounds = db.scalars(select(MaterialOutbound)).all()
    total_income = round(sum(float(item.actual_amount) for item in payment_phases), 2)
    office_total = sum(float(item.amount) for item in office_expenses)
    inbound_total = sum(float(item.total_amount) for item in material_inbounds)
    total_approved_expense = round(office_total + inbound_total, 2)
    pending_approval_count = sum(1 for item in material_outbounds if item.status.value == "pending")
    return {
        "total_income": total_income,
        "total_approved_expense": total_approved_expense,
        "net_profit": round(total_income - total_approved_expense, 2),
        "pending_approval_count": pending_approval_count,
    }
