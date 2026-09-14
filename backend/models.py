from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ACCOUNTANT_ADMIN = "accountant_admin"
    ACCOUNTANT = "accountant"
    PARTNER = "partner"


class CooperationType(str, enum.Enum):
    HALF_PACKAGE = "半包"
    FULL_CASE = "全案"


class PaymentStageStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    RECEIVED = "received"


class OfficeExpenseCategory(str, enum.Enum):
    RENT = "房租"
    PROPERTY = "物业费"
    WATER = "水费"
    ELECTRICITY = "电费"
    INTERNET = "网费"
    MISC = "其他杂费"


class OfficeExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MeetingStatus(str, enum.Enum):
    DRAFT = "draft"
    ARCHIVED = "archived"


engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, future=True, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    openid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    operator_name: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100), index=True)
    target: Mapped[str] = mapped_column(String(200))
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    contract_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    client_name: Mapped[str] = mapped_column(String(120))
    contract_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    cooperation_type: Mapped[CooperationType] = mapped_column(Enum(CooperationType), default=CooperationType.HALF_PACKAGE)
    contract_total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), default="进行中")
    payment_stages: Mapped[list[PaymentStage]] = relationship(back_populates="project", cascade="all, delete-orphan")


class PaymentStage(Base, TimestampMixin):
    __tablename__ = "payment_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    stage_name: Mapped[str] = mapped_column(String(100))
    trigger_description: Mapped[str] = mapped_column(String(200))
    target_progress: Mapped[Optional[int]] = mapped_column(nullable=True)
    planned_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    received_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    received_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[PaymentStageStatus] = mapped_column(Enum(PaymentStageStatus), default=PaymentStageStatus.PENDING)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project: Mapped[Project] = relationship(back_populates="payment_stages")


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    is_supervisor_record: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship()
    project: Mapped[Optional[Project]] = relationship()


class MeetingMinute(Base, TimestampMixin):
    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    meeting_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    location: Mapped[str] = mapped_column(String(200))
    host: Mapped[str] = mapped_column(String(100))
    attendees: Mapped[str] = mapped_column(Text)
    topics: Mapped[str] = mapped_column(Text)
    decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.DRAFT)
    signed_off_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    signed_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    signed_off_by: Mapped[Optional[User]] = relationship(foreign_keys=[signed_off_by_id])
    created_by: Mapped[Optional[User]] = relationship(foreign_keys=[created_by_id])


class OfficeExpense(Base, TimestampMixin):
    __tablename__ = "office_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_name: Mapped[str] = mapped_column(String(120))
    project_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    category: Mapped[OfficeExpenseCategory] = mapped_column(Enum(OfficeExpenseCategory), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    payer: Mapped[str] = mapped_column(String(100))
    receipt_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_day: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[OfficeExpenseStatus] = mapped_column(Enum(OfficeExpenseStatus), default=OfficeExpenseStatus.PENDING)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[Optional[User]] = relationship(foreign_keys=[approved_by_id])
    created_by: Mapped[Optional[User]] = relationship(foreign_keys=[created_by_id])


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
