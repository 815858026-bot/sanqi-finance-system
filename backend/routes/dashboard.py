"""看板聚合接口。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import ApprovalStatus, ExpenseRequest, OfficeExpense, Project, SalarySlip, User, get_db
from security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


def _money(value: Decimal | None) -> float:
    return float(value or 0)


@router.get("/overview", summary="看板概览")
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = current_user
    projects = db.scalars(select(Project)).all()
    expenses = db.scalars(select(ExpenseRequest)).all()
    office_expenses = db.scalars(select(OfficeExpense)).all()
    salary_slips = db.scalars(select(SalarySlip)).all()

    total_income = sum((Decimal(project.contract_amount) for project in projects), Decimal("0"))
    total_approved_expense = sum((Decimal(expense.amount) for expense in expenses if expense.status in {ApprovalStatus.AWAITING_PAYMENT, ApprovalStatus.PAID}), Decimal("0"))
    total_office_expense = sum((Decimal(expense.amount) for expense in office_expenses), Decimal("0"))
    total_salary = sum((Decimal(slip.net_salary) for slip in salary_slips if slip.status == ApprovalStatus.PAID), Decimal("0"))
    pending_approval_count = sum(1 for expense in expenses if expense.status in {ApprovalStatus.PENDING, ApprovalStatus.PENDING_LEVEL_2, ApprovalStatus.PENDING_LEVEL_3})
    pending_approval_count += sum(1 for slip in salary_slips if slip.status in {ApprovalStatus.PENDING, ApprovalStatus.PENDING_LEVEL_2, ApprovalStatus.PENDING_LEVEL_3})

    return {
        "project_count": len(projects),
        "salary_slip_count": len(salary_slips),
        "total_income": _money(total_income),
        "total_approved_expense": _money(total_approved_expense + total_office_expense + total_salary),
        "net_profit": _money(total_income - total_approved_expense - total_office_expense - total_salary),
        "pending_approval_count": pending_approval_count,
    }
