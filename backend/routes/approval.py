from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MeetingMinute, MeetingStatus, OfficeExpense, OfficeExpenseStatus, User, UserRole, get_db
from security import get_current_user

router = APIRouter(prefix="/api/approval", tags=["审批中心"])


@router.get("/pending", summary="待审批事项")
def list_pending_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expenses = []
    meetings = []
    if current_user.role in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.PARTNER}:
        expenses = db.scalars(
            select(OfficeExpense).where(OfficeExpense.status == OfficeExpenseStatus.PENDING).order_by(OfficeExpense.payment_date.desc())
        ).all()
        meetings = db.scalars(
            select(MeetingMinute).where(
                MeetingMinute.status == MeetingStatus.DRAFT,
                MeetingMinute.signed_off_by_id.is_(None),
            ).order_by(MeetingMinute.meeting_time.desc())
        ).all()
    return {
        "pending_expenses": [
            {
                "id": expense.id,
                "item_name": expense.item_name,
                "category": expense.category.value,
                "amount": float(expense.amount),
                "payment_date": expense.payment_date,
                "payer": expense.payer,
            }
            for expense in expenses
        ],
        "pending_meetings": [
            {
                "id": meeting.id,
                "title": meeting.title,
                "meeting_time": meeting.meeting_time,
                "host": meeting.host,
                "location": meeting.location,
            }
            for meeting in meetings
        ],
    }
