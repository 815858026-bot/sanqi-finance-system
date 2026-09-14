from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import settings


Base = declarative_base()


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    PARTNER = "partner"
    ACCOUNTANT_ADMIN = "accountant_admin"
    ACCOUNTANT = "accountant"
    SUPERVISOR = "supervisor"
    OFFICE_ADMIN = "office_admin"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CooperationType(str, Enum):
    HALF_PACKAGE = "half_package"
    FULL_CASE = "full_case"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


class AttendanceStatus(str, Enum):
    NORMAL = "normal"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    LATE_AND_EARLY = "late_and_early"
    REST_DAY = "rest_day"
    PENDING = "pending"


class MaterialOutboundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.ACCOUNTANT)
    email = Column(String(100))
    phone = Column(String(30))
    openid = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operator_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    target = Column(String(255), nullable=False)
    detail = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    contract_number = Column(String(80), unique=True, nullable=False, index=True)
    client_name = Column(String(100), nullable=False)
    contract_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_price = Column(Numeric(12, 2), default=0, nullable=False)
    cooperation_type = Column(SAEnum(CooperationType), default=CooperationType.HALF_PACKAGE, nullable=False)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    payment_phases = relationship("ProjectPaymentPhase", back_populates="project", cascade="all, delete-orphan")


class ProjectPaymentPhase(Base):
    __tablename__ = "project_payment_phases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    phase_number = Column(Integer, nullable=False)
    phase_name = Column(String(100), nullable=False)
    trigger_progress = Column(Integer, default=0, nullable=False)
    payment_percent = Column(Float, nullable=False)
    planned_amount = Column(Numeric(12, 2), nullable=False)
    actual_amount = Column(Numeric(12, 2), default=0, nullable=False)
    due_date = Column(Date)
    payment_date = Column(Date)
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="payment_phases")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    work_date = Column(Date, nullable=False, index=True)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    work_hours = Column(Float, default=0, nullable=False)
    status = Column(SAEnum(AttendanceStatus), default=AttendanceStatus.PENDING, nullable=False)
    late_minutes = Column(Integer, default=0, nullable=False)
    early_leave_minutes = Column(Integer, default=0, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    project = relationship("Project")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    meeting_time = Column(DateTime, nullable=False, index=True)
    location = Column(String(150), nullable=False)
    host_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    host_name = Column(String(100), nullable=False)
    attendees = Column(JSON, default=list, nullable=False)
    agenda = Column(Text)
    resolution = Column(Text)
    minutes = Column(Text, nullable=False)
    attachment_name = Column(String(255))
    attachment_url = Column(String(255))
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OfficeExpense(Base):
    __tablename__ = "office_expenses"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(120))
    expense_type = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False, index=True)
    payer = Column(String(100), nullable=False)
    receipt_url = Column(String(255))
    description = Column(Text)
    is_recurring = Column(Boolean, default=False, nullable=False)
    reminder_day = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    specification = Column(String(120))
    unit = Column(String(20), nullable=False)
    cost_price = Column(Numeric(12, 2), default=0, nullable=False)
    category = Column(String(40), nullable=False)
    warning_quantity = Column(Integer, default=0, nullable=False)
    image_url = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MaterialInventory(Base):
    __tablename__ = "material_inventory"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), unique=True, nullable=False, index=True)
    current_quantity = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    material = relationship("Material")


class MaterialInbound(Base):
    __tablename__ = "material_inbounds"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    purchase_date = Column(Date, nullable=False, index=True)
    supplier = Column(String(120), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    invoice_url = Column(String(255))
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operator_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    material = relationship("Material")


class MaterialOutbound(Base):
    __tablename__ = "material_outbounds"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    project_name = Column(String(120), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    requester_name = Column(String(100), nullable=False)
    purpose = Column(Text)
    issue_date = Column(Date, nullable=False, index=True)
    status = Column(SAEnum(MaterialOutboundStatus), default=MaterialOutboundStatus.PENDING, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("MaterialOutboundItem", back_populates="outbound", cascade="all, delete-orphan")
    project = relationship("Project")


class MaterialOutboundItem(Base):
    __tablename__ = "material_outbound_items"

    id = Column(Integer, primary_key=True, index=True)
    outbound_id = Column(Integer, ForeignKey("material_outbounds.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    material_name = Column(String(120), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    total_cost = Column(Numeric(12, 2), nullable=False)

    outbound = relationship("MaterialOutbound", back_populates="items")
    material = relationship("Material")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_audit_log(
    db,
    operator: Optional[User],
    action: str,
    target: str,
    detail: str,
    ip_address: Optional[str] = None,
) -> AuditLog:
    operator_name = f"{operator.full_name}({operator.username})" if operator else "系统"
    log = AuditLog(
        operator_id=operator.id if operator else None,
        operator_name=operator_name,
        action=action,
        target=target,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    return log
