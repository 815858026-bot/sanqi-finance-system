from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import AttendanceRecord, MeetingMinute, OfficeExpense, OfficeExpenseStatus, Project, User, get_db
from security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("/overview", summary="财务看板概览")
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = db.scalars(select(Project).options(selectinload(Project.payment_stages))).all()
    total_income = sum(
        Decimal(stage.received_amount or 0)
        for project in projects
        for stage in project.payment_stages
    )
    total_receivable = sum(Decimal(project.contract_total_price or 0) for project in projects)
    approved_expenses = db.scalars(
        select(OfficeExpense).where(OfficeExpense.status == OfficeExpenseStatus.APPROVED)
    ).all()
    pending_expenses = db.scalars(
        select(OfficeExpense).where(OfficeExpense.status == OfficeExpenseStatus.PENDING)
    ).all()
    total_approved_expense = sum(Decimal(expense.amount) for expense in approved_expenses)
    month_start = date.today().replace(day=1)
    attendance_records = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.attendance_date >= month_start)
    ).all()
    working_days = 0
    cursor = month_start
    while cursor <= date.today():
        if cursor.weekday() != 1:
            working_days += 1
        cursor += timedelta(days=1)
    attendance_users = {record.user_id for record in attendance_records}
    attendance_days = {(record.user_id, record.attendance_date) for record in attendance_records}
    attendance_rate = round((len(attendance_days) / (working_days * len(attendance_users))) * 100, 2) if attendance_users and working_days else 100
    meeting_count = len(db.scalars(select(MeetingMinute)).all())
    return {
        "total_income": float(total_income),
        "total_approved_expense": float(total_approved_expense),
        "net_profit": float(total_income - total_approved_expense),
        "pending_approval_count": len(pending_expenses),
        "attendance_rate": attendance_rate,
        "meeting_count": meeting_count,
        "receivable_total": float(total_receivable),
        "received_total": float(total_income),
        "outstanding_total": float(total_receivable - total_income),
    }
