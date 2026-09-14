"""SQLAlchemy 模型定义。"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Generator, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, Time, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    SUPER_ADMIN = "admin"
    PARTNER = "partner"
    ACCOUNTANT_ADMIN = "finance_admin"
    ACCOUNTANT = "finance"
    CASHIER = "cashier"


class LeaveType(str, Enum):
    SICK = "病假"
    PERSONAL = "事假"
    MARRIAGE = "婚假"
    MATERNITY = "产假"
    PATERNITY = "陪产假"
    BEREAVEMENT = "丧假"
    UNPAID = "无薪假"


class LeaveUnit(str, Enum):
    DAY = "day"
    HOUR = "hour"


class ProjectMode(str, Enum):
    HALF_PACKAGE = "半包"
    FULL_CASE = "全案"


class ApprovalStatus(str, Enum):
    DRAFT = "草稿"
    PENDING = "待一级审批"
    PENDING_LEVEL_2 = "待二级审批"
    PENDING_LEVEL_3 = "待三级审批"
    APPROVED = "已审批"
    REJECTED = "已驳回"
    AWAITING_PAYMENT = "待支付"
    PAID = "已支付"


class PaymentStatus(str, Enum):
    PENDING = "待复核"
    REVIEWED = "已复核"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    openid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    operator_name: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80), index=True)
    target: Mapped[str] = mapped_column(String(160), index=True)
    detail: Mapped[str] = mapped_column(Text)
    before_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    check_out: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    is_early_leave: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_days: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    leave_date: Mapped[date] = mapped_column(Date, index=True)
    leave_type: Mapped[LeaveType] = mapped_column(SqlEnum(LeaveType), index=True)
    unit: Mapped[LeaveUnit] = mapped_column(SqlEnum(LeaveUnit))
    quantity: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MeetingRecord(Base):
    __tablename__ = "meeting_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    location: Mapped[str] = mapped_column(String(200))
    participants: Mapped[str] = mapped_column(Text)
    agenda: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    contract_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    client_name: Mapped[str] = mapped_column(String(120))
    site_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    cooperation_mode: Mapped[ProjectMode] = mapped_column(SqlEnum(ProjectMode))
    contract_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(40), default="进行中")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CollectionPlan(Base):
    __tablename__ = "collection_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    stage_name: Mapped[str] = mapped_column(String(80))
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    planned_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CollectionRecord(Base):
    __tablename__ = "collection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    plan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("collection_plans.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    received_date: Mapped[date] = mapped_column(Date, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OfficeExpense(Base):
    __tablename__ = "office_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    unit: Mapped[str] = mapped_column(String(30), default="件")
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaterialReceipt(Base):
    __tablename__ = "material_receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    supplier: Mapped[str] = mapped_column(String(120))
    purchase_date: Mapped[date] = mapped_column(Date, index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    invoice_attachment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaterialUsage(Base):
    __tablename__ = "material_usages"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SalaryConfig(Base):
    __tablename__ = "salary_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    job_title: Mapped[str] = mapped_column(String(100))
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    position_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    performance_bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    daily_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    hourly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    late_penalty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_sick_leave_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    is_personal_leave_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalarySlip(Base):
    __tablename__ = "salary_slips"
    __table_args__ = (UniqueConstraint("employee_id", "year_month", name="uq_salary_employee_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slip_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    position_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    performance_bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    gross_income: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    leave_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    late_penalty_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    attendance_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    leave_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    late_count: Mapped[int] = mapped_column(default=0)
    early_leave_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[ApprovalStatus] = mapped_column(SqlEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    prepared_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pay_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalaryApproval(Base):
    __tablename__ = "salary_approvals"
    __table_args__ = (UniqueConstraint("salary_slip_id", "level", name="uq_salary_approval_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    salary_slip_id: Mapped[int] = mapped_column(ForeignKey("salary_slips.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    level: Mapped[int] = mapped_column(index=True)
    approved: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExpenseRequest(Base):
    __tablename__ = "expense_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    purpose: Mapped[str] = mapped_column(Text)
    invoice_attachment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(SqlEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExpenseApproval(Base):
    __tablename__ = "expense_approvals"
    __table_args__ = (UniqueConstraint("expense_request_id", "level", name="uq_expense_approval_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_request_id: Mapped[int] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    level: Mapped[int] = mapped_column(index=True)
    approved: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_request_id: Mapped[int] = mapped_column(ForeignKey("expense_requests.id"), unique=True, index=True)
    payee: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str] = mapped_column(String(80))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    attachment: Mapped[str] = mapped_column(String(255))
    cashier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus), default=PaymentStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
