import calendar
import os
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from config import settings
from models import AuditLog, OfficeExpense, OfficeExpenseCategory, OfficeExpenseStatus, User, UserRole, get_db
from schemas import OfficeExpenseCreateDTO
from security import get_current_user

router = APIRouter(prefix="/api/records", tags=["办公费用"])


def _serialize_expense(expense: OfficeExpense) -> dict:
    return {
        "id": expense.id,
        "item_name": expense.item_name,
        "project_name": expense.project_name,
        "category": expense.category.value,
        "amount": float(expense.amount),
        "payment_date": expense.payment_date,
        "payer": expense.payer,
        "receipt_path": expense.receipt_path,
        "note": expense.note,
        "is_recurring": expense.is_recurring,
        "reminder_day": expense.reminder_day,
        "status": expense.status.value,
        "approved_by": expense.approved_by.full_name if expense.approved_by else None,
        "approved_at": expense.approved_at,
    }


@router.get("", summary="查询办公费用")
def list_office_expenses(
    category: OfficeExpenseCategory | None = None,
    status_filter: OfficeExpenseStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(OfficeExpense)
    if category:
        query = query.where(OfficeExpense.category == category)
    if status_filter:
        query = query.where(OfficeExpense.status == status_filter)
    expenses = db.scalars(query.order_by(OfficeExpense.payment_date.desc(), OfficeExpense.id.desc())).all()
    return [_serialize_expense(expense) for expense in expenses]


@router.post("", summary="登记办公费用")
def create_office_expense(
    dto: OfficeExpenseCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限录入办公费用")
    expense = OfficeExpense(**dto.model_dump(), created_by_id=current_user.id)
    db.add(expense)
    db.flush()
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="CREATE_OFFICE_EXPENSE",
            target=f"Expense #{expense.id}",
            detail=f"登记办公费用 {expense.item_name} 金额 {float(expense.amount):.2f}",
        )
    )
    db.commit()
    db.refresh(expense)
    return _serialize_expense(expense)


@router.post("/bulk", summary="批量导入办公费用")
def bulk_import_office_expenses(
    items: list[OfficeExpenseCreateDTO],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限批量导入办公费用")
    created_ids = []
    for item in items:
        expense = OfficeExpense(**item.model_dump(), created_by_id=current_user.id)
        db.add(expense)
        db.flush()
        created_ids.append(expense.id)
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="BULK_IMPORT_OFFICE_EXPENSE",
            target="OfficeExpense",
            detail=f"批量导入 {len(created_ids)} 条办公费用",
        )
    )
    db.commit()
    return {"message": "批量导入成功", "created_ids": created_ids}


@router.get("/statistics/monthly", summary="办公费用月度统计")
def monthly_statistics(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="月份范围必须在 1-12")
    expenses = db.scalars(
        select(OfficeExpense).where(
            extract("year", OfficeExpense.payment_date) == year,
            extract("month", OfficeExpense.payment_date) == month,
        )
    ).all()
    total = sum(Decimal(expense.amount) for expense in expenses)
    by_category = {}
    for expense in expenses:
        by_category.setdefault(expense.category.value, Decimal("0"))
        by_category[expense.category.value] += Decimal(expense.amount)
    return {
        "year": year,
        "month": month,
        "total": float(total),
        "by_category": {key: float(value) for key, value in by_category.items()},
        "count": len(expenses),
    }


@router.get("/statistics/categories", summary="办公费用分类统计")
def category_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(OfficeExpense.category, func.sum(OfficeExpense.amount), func.count(OfficeExpense.id)).group_by(OfficeExpense.category)
    ).all()
    return [
        {"category": category.value, "total": float(total or 0), "count": count}
        for category, total, count in rows
    ]


@router.get("/reminders", summary="定期费用提醒")
def recurring_expense_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    expenses = db.scalars(select(OfficeExpense).where(OfficeExpense.is_recurring == True)).all()
    items = []
    for expense in expenses:
        reminder_day = expense.reminder_day or expense.payment_date.day
        due_day = min(reminder_day, calendar.monthrange(today.year, today.month)[1])
        due_date = date(today.year, today.month, due_day)
        if due_date < today:
            next_month = today.month + 1
            next_year = today.year
            if next_month == 13:
                next_month = 1
                next_year += 1
            due_day = min(reminder_day, calendar.monthrange(next_year, next_month)[1])
            due_date = date(next_year, next_month, due_day)
        items.append(
            {
                "expense_id": expense.id,
                "item_name": expense.item_name,
                "category": expense.category.value,
                "next_due_date": due_date,
                "amount": float(expense.amount),
                "payer": expense.payer,
            }
        )
    return sorted(items, key=lambda item: item["next_due_date"])


@router.post("/{expense_id}/approve", summary="审批办公费用")
def approve_expense(
    expense_id: int,
    approve: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限审批办公费用")
    expense = db.get(OfficeExpense, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="办公费用不存在")
    expense.status = OfficeExpenseStatus.APPROVED if approve else OfficeExpenseStatus.REJECTED
    expense.approved_by_id = current_user.id
    expense.approved_at = datetime.utcnow()
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="APPROVE_OFFICE_EXPENSE" if approve else "REJECT_OFFICE_EXPENSE",
            target=f"Expense #{expense.id}",
            detail=f"{('通过' if approve else '驳回')}办公费用 {expense.item_name}",
        )
    )
    db.commit()
    return {"message": f"办公费用已{'审批通过' if approve else '驳回'}"}


@router.post("/upload", summary="上传费用凭证")
def upload_expense_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    os.makedirs(settings.upload_dir, exist_ok=True)
    receipt_dir = os.path.join(settings.upload_dir, "expenses")
    os.makedirs(receipt_dir, exist_ok=True)
    filename = f"{uuid4().hex}_{file.filename}"
    destination = os.path.join(receipt_dir, filename)
    with open(destination, "wb") as output:
        output.write(file.file.read())
    return {"receipt_path": destination.replace("./static", "/static")}
