from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from models import CooperationType, PaymentStatus, ProjectStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


class UserLoginDTO(BaseModel):
    username: str
    password: str


class UserDTO(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    openid: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserListDTO(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime


class CreateUserDTO(BaseModel):
    username: str
    password: str = Field(min_length=6)
    full_name: str
    role: UserRole
    email: Optional[str] = None
    phone: Optional[str] = None


class UpdateUserDTO(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class AuditLogDTO(BaseModel):
    id: int
    operator_id: Optional[int] = None
    operator_name: str
    action: str
    target: str
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogFilterDTO(BaseModel):
    action: Optional[str] = None
    operator_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCreateDTO(BaseModel):
    name: str
    contract_number: str
    client_name: str
    contract_amount: Decimal = Decimal("0")
    total_price: Optional[Decimal] = None
    cooperation_type: CooperationType = CooperationType.HALF_PACKAGE
    status: ProjectStatus = ProjectStatus.ACTIVE
    description: Optional[str] = None


class ProjectUpdateDTO(BaseModel):
    name: Optional[str] = None
    contract_number: Optional[str] = None
    client_name: Optional[str] = None
    contract_amount: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    cooperation_type: Optional[CooperationType] = None
    status: Optional[ProjectStatus] = None
    description: Optional[str] = None


class PaymentPhaseCreateDTO(BaseModel):
    phase_number: int
    phase_name: str
    trigger_progress: int = 0
    payment_percent: float
    planned_amount: Decimal
    due_date: Optional[date] = None


class PaymentPhaseRecordDTO(BaseModel):
    actual_amount: Decimal
    payment_date: date


class AttendanceCheckDTO(BaseModel):
    check_time: Optional[datetime] = None
    project_id: Optional[int] = None
    notes: Optional[str] = None


class MeetingCreateDTO(BaseModel):
    title: str
    meeting_time: datetime
    location: str
    host_name: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    agenda: Optional[str] = None
    resolution: Optional[str] = None
    minutes: str
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None


class MeetingUpdateDTO(BaseModel):
    title: Optional[str] = None
    meeting_time: Optional[datetime] = None
    location: Optional[str] = None
    host_name: Optional[str] = None
    attendees: Optional[List[str]] = None
    agenda: Optional[str] = None
    resolution: Optional[str] = None
    minutes: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    is_archived: Optional[bool] = None


class OfficeExpenseCreateDTO(BaseModel):
    project_name: Optional[str] = None
    expense_type: str
    amount: Decimal
    payment_date: date
    payer: str
    receipt_url: Optional[str] = None
    description: Optional[str] = None
    is_recurring: bool = False
    reminder_day: Optional[int] = None


class OfficeExpenseBatchImportDTO(BaseModel):
    items: List[OfficeExpenseCreateDTO]


class MaterialCreateDTO(BaseModel):
    code: str
    name: str
    specification: Optional[str] = None
    unit: str
    cost_price: Decimal = Decimal("0")
    category: str
    warning_quantity: int = 0
    image_url: Optional[str] = None
    description: Optional[str] = None


class MaterialUpdateDTO(BaseModel):
    name: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[Decimal] = None
    category: Optional[str] = None
    warning_quantity: Optional[int] = None
    image_url: Optional[str] = None
    description: Optional[str] = None


class MaterialInboundCreateDTO(BaseModel):
    material_id: int
    purchase_date: date
    supplier: str
    unit_price: Decimal
    quantity: int
    invoice_url: Optional[str] = None


class MaterialOutboundItemDTO(BaseModel):
    material_id: int
    quantity: int


class MaterialOutboundCreateDTO(BaseModel):
    project_id: Optional[int] = None
    project_name: str
    requester_name: Optional[str] = None
    purpose: Optional[str] = None
    issue_date: date
    items: List[MaterialOutboundItemDTO]
