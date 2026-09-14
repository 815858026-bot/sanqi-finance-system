from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from models import OfficeExpense, User, UserRole, add_audit_log, get_db
from schemas import OfficeExpenseBatchImportDTO, OfficeExpenseCreateDTO
from security import get_current_user, require_roles


router = APIRouter(prefix="/api/office-expenses", tags=["办公费用"])
ALLOWED_TYPES = {"房租", "物业费", "水费", "电费", "网费", "其他杂费"}


def _expense_to_dict(expense: OfficeExpense) -> dict:
    return {
        "id": expense.id,
        "project_name": expense.project_name,
        "expense_type": expense.expense_type,
        "amount": float(expense.amount),
        "payment_date": expense.payment_date,
        "payer": expense.payer,
        "receipt_url": expense.receipt_url,
        "description": expense.description,
        "is_recurring": expense.is_recurring,
        "reminder_day": expense.reminder_day,
        "created_at": expense.created_at,
    }


@router.get("")
def list_expenses(
    expense_type: str | None = None,
    month: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(OfficeExpense)
    if expense_type:
        query = query.where(OfficeExpense.expense_type == expense_type)
    if month:
        year, mon = map(int, month.split("-"))
        query = query.where(extract("year", OfficeExpense.payment_date) == year, extract("month", OfficeExpense.payment_date) == mon)
    expenses = db.scalars(query.order_by(OfficeExpense.payment_date.desc(), OfficeExpense.id.desc())).all()
    return [_expense_to_dict(expense) for expense in expenses]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    dto: OfficeExpenseCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)),
    db: Session = Depends(get_db),
):
    if dto.expense_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="不支持的费用类型")
    expense = OfficeExpense(**dto.model_dump())
    db.add(expense)
    db.flush()
    add_audit_log(db, current_user, "CREATE_OFFICE_EXPENSE", f"OfficeExpense #{expense.id}", f"录入办公费用 {expense.expense_type}")
    db.commit()
    db.refresh(expense)
    return _expense_to_dict(expense)


@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
def batch_import(
    dto: OfficeExpenseBatchImportDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)),
    db: Session = Depends(get_db),
):
    created = []
    for item in dto.items:
        if item.expense_type not in ALLOWED_TYPES:
            continue
        expense = OfficeExpense(**item.model_dump())
        db.add(expense)
        created.append(expense)
    db.flush()
    add_audit_log(db, current_user, "BATCH_IMPORT_OFFICE_EXPENSE", "OfficeExpenseBatch", f"批量导入 {len(created)} 条办公费用")
    db.commit()
    return {"count": len(created)}


@router.get("/statistics")
def expense_statistics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expenses = db.scalars(select(OfficeExpense)).all()
    by_type = {}
    by_month = {}
    for expense in expenses:
        by_type[expense.expense_type] = round(by_type.get(expense.expense_type, 0) + float(expense.amount), 2)
        month_key = expense.payment_date.strftime("%Y-%m")
        by_month[month_key] = round(by_month.get(month_key, 0) + float(expense.amount), 2)
    return {
        "total_amount": round(sum(by_type.values()), 2),
        "by_type": by_type,
        "by_month": by_month,
    }


@router.get("/reminders")
def reminders(reference_date: date | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reference_date = reference_date or date.today()
    recurring = db.scalars(select(OfficeExpense).where(OfficeExpense.is_recurring == True)).all()
    items = []
    for expense in recurring:
        if expense.reminder_day and expense.reminder_day <= reference_date.day + 7:
            items.append({
                **_expense_to_dict(expense),
                "next_reminder": reference_date.replace(day=min(expense.reminder_day, 28)),
            })
    return items
