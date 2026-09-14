"""审批与支付流程。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    ApprovalStatus,
    AuditLog,
    ExpenseApproval,
    ExpenseRequest,
    PaymentRecord,
    PaymentStatus,
    SalaryApproval,
    SalarySlip,
    User,
    UserRole,
    get_db,
)
from schemas import ExpenseApprovalDTO, MarkSalaryPaidDTO, PaymentCreateDTO, PaymentReviewDTO, SalaryApprovalDTO
from security import get_current_user

router = APIRouter(prefix="/api/approval", tags=["审批与支付"])
APPROVAL_SEQUENCE = {"admin": 1, "partner001": 2, "partner002": 3}


def _log(db: Session, current_user: User, action: str, target: str, detail: str) -> None:
    db.add(AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action=action,
        target=target,
        detail=detail,
    ))


def _current_level(user: User) -> int:
    level = APPROVAL_SEQUENCE.get(user.username)
    if not level:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号不在三级审批链中")
    return level


def _next_salary_status(level: int) -> ApprovalStatus:
    return {
        1: ApprovalStatus.PENDING_LEVEL_2,
        2: ApprovalStatus.PENDING_LEVEL_3,
        3: ApprovalStatus.AWAITING_PAYMENT,
    }[level]


def _next_expense_status(level: int) -> ApprovalStatus:
    return {
        1: ApprovalStatus.PENDING_LEVEL_2,
        2: ApprovalStatus.PENDING_LEVEL_3,
        3: ApprovalStatus.AWAITING_PAYMENT,
    }[level]


@router.get("/pending", summary="待审批与待支付总览")
def pending_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    salary_rows = db.scalars(select(SalarySlip).where(SalarySlip.status.in_([
        ApprovalStatus.PENDING,
        ApprovalStatus.PENDING_LEVEL_2,
        ApprovalStatus.PENDING_LEVEL_3,
        ApprovalStatus.AWAITING_PAYMENT,
    ]))).all()
    expense_rows = db.scalars(select(ExpenseRequest).where(ExpenseRequest.status.in_([
        ApprovalStatus.PENDING,
        ApprovalStatus.PENDING_LEVEL_2,
        ApprovalStatus.PENDING_LEVEL_3,
        ApprovalStatus.AWAITING_PAYMENT,
    ]))).all()
    payment_rows = db.scalars(select(PaymentRecord).where(PaymentRecord.status == PaymentStatus.PENDING)).all()
    return {
        "salary_slips": [{"id": row.id, "slip_number": row.slip_number, "status": row.status.value, "net_salary": float(row.net_salary)} for row in salary_rows],
        "expense_requests": [{"id": row.id, "amount": float(row.amount), "status": row.status.value, "purpose": row.purpose} for row in expense_rows],
        "payment_reviews": [{"id": row.id, "expense_request_id": row.expense_request_id, "amount": float(row.amount), "status": row.status.value} for row in payment_rows],
        "viewer_role": current_user.role.value,
    }


@router.post("/salary-slips/{slip_id}/approve", summary="审批工资单")
def approve_salary_slip(slip_id: int, dto: SalaryApprovalDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    slip = db.get(SalarySlip, slip_id)
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工资单不存在")
    level = _current_level(current_user)
    existing = db.scalars(select(SalaryApproval).where(SalaryApproval.salary_slip_id == slip_id).order_by(SalaryApproval.level.asc())).all()
    expected_level = len(existing) + 1
    if level != expected_level:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"当前应由第 {expected_level} 级审批")
    approval = SalaryApproval(salary_slip_id=slip_id, approver_id=current_user.id, level=level, approved=dto.approved, comment=dto.comment)
    db.add(approval)
    slip.status = ApprovalStatus.REJECTED if not dto.approved else _next_salary_status(level)
    _log(db, current_user, "APPROVE_SALARY", f"SalarySlip #{slip_id}", f"第{level}级{'通过' if dto.approved else '驳回'}")
    db.commit()
    return {"message": "工资单审批已记录", "status": slip.status.value}


@router.post("/salary-slips/{slip_id}/pay", summary="登记工资发放")
def mark_salary_paid(slip_id: int, dto: MarkSalaryPaidDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.CASHIER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员或出纳可登记发薪")
    slip = db.get(SalarySlip, slip_id)
    if not slip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工资单不存在")
    if slip.status != ApprovalStatus.AWAITING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工资单尚未完成三级审批")
    slip.status = ApprovalStatus.PAID
    slip.pay_date = dto.pay_date
    slip.remark = dto.remark or slip.remark
    _log(db, current_user, "PAY_SALARY", f"SalarySlip #{slip_id}", "登记工资发放")
    db.commit()
    return {"message": "工资发放已记录", "status": slip.status.value}


@router.post("/expense-requests/{expense_id}/approve", summary="审批支出单")
def approve_expense_request(expense_id: int, dto: ExpenseApprovalDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expense = db.get(ExpenseRequest, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支出单不存在")
    level = _current_level(current_user)
    existing = db.scalars(select(ExpenseApproval).where(ExpenseApproval.expense_request_id == expense_id).order_by(ExpenseApproval.level.asc())).all()
    expected_level = len(existing) + 1
    if level != expected_level:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"当前应由第 {expected_level} 级审批")
    approval = ExpenseApproval(expense_request_id=expense_id, approver_id=current_user.id, level=level, approved=dto.approved, comment=dto.comment)
    db.add(approval)
    expense.status = ApprovalStatus.REJECTED if not dto.approved else _next_expense_status(level)
    _log(db, current_user, "APPROVE_EXPENSE", f"ExpenseRequest #{expense_id}", f"第{level}级{'通过' if dto.approved else '驳回'}")
    db.commit()
    return {"message": "支出单审批已记录", "status": expense.status.value}


@router.post("/expense-requests/{expense_id}/payment", summary="出纳填写支付表")
def create_payment(expense_id: int, dto: PaymentCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.CASHIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅出纳可填写支付表")
    expense = db.get(ExpenseRequest, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支出单不存在")
    if expense.status != ApprovalStatus.AWAITING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="支出单尚未完成三级审批")
    if db.scalar(select(PaymentRecord).where(PaymentRecord.expense_request_id == expense_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该支出单支付表已存在")
    payment = PaymentRecord(expense_request_id=expense_id, cashier_id=current_user.id, **dto.model_dump())
    db.add(payment)
    _log(db, current_user, "CREATE_PAYMENT", f"ExpenseRequest #{expense_id}", "填写支付表")
    db.commit()
    return {"message": "支付表已提交复核", "payment_id": payment.id}


@router.post("/payments/{payment_id}/review", summary="财务复核支付表")
def review_payment(payment_id: int, dto: PaymentReviewDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅财务可复核支付表")
    payment = db.get(PaymentRecord, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="支付表不存在")
    expense = db.get(ExpenseRequest, payment.expense_request_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联支出单不存在")
    if not dto.approved:
        payment.status = PaymentStatus.PENDING
        _log(db, current_user, "REJECT_PAYMENT_REVIEW", f"Payment #{payment_id}", dto.comment or "支付表复核未通过")
        db.commit()
        return {"message": "支付表已退回复核", "status": payment.status.value}
    payment.reviewed_by = current_user.id
    payment.reviewed_at = datetime.utcnow()
    payment.status = PaymentStatus.REVIEWED
    expense.status = ApprovalStatus.PAID
    _log(db, current_user, "REVIEW_PAYMENT", f"Payment #{payment_id}", "支付表复核通过，支出单标记已支付")
    db.commit()
    return {"message": "支付表复核通过", "expense_status": expense.status.value}
