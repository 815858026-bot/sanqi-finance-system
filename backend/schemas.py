"""Pydantic 数据模型。"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models import LeaveType, LeaveUnit, ProjectMode, UserRole


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class Token(BaseSchema):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


class UserLoginDTO(BaseSchema):
    username: str
    password: str


class UserListDTO(BaseSchema):
    id: int
    username: str
    full_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserDTO(UserListDTO):
    openid: Optional[str] = None
    updated_at: datetime


class CreateUserDTO(BaseSchema):
    username: str
    password: str = Field(min_length=6)
    full_name: str
    role: UserRole
    email: Optional[str] = None
    phone: Optional[str] = None


class UpdateUserDTO(BaseSchema):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class AuditLogDTO(BaseSchema):
    id: int
    operator_id: Optional[int] = None
    operator_name: str
    action: str
    target: str
    detail: str
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogFilterDTO(BaseSchema):
    action: Optional[str] = None
    operator_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCreateDTO(BaseSchema):
    name: str
    contract_number: str
    client_name: str
    site_name: Optional[str] = None
    cooperation_mode: ProjectMode
    contract_amount: Decimal
    status: str = "进行中"


class ProjectUpdateDTO(BaseSchema):
    name: Optional[str] = None
    client_name: Optional[str] = None
    site_name: Optional[str] = None
    cooperation_mode: Optional[ProjectMode] = None
    contract_amount: Optional[Decimal] = None
    status: Optional[str] = None


class CollectionPlanCreateDTO(BaseSchema):
    stage_name: str
    planned_amount: Decimal
    planned_date: Optional[date] = None


class CollectionRecordCreateDTO(BaseSchema):
    plan_id: Optional[int] = None
    amount: Decimal
    received_date: date
    remark: Optional[str] = None


class AttendanceCreateDTO(BaseSchema):
    employee_id: int
    work_date: date
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    notes: Optional[str] = None


class AttendanceUpdateDTO(BaseSchema):
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    notes: Optional[str] = None


class LeaveCreateDTO(BaseSchema):
    employee_id: int
    leave_date: date
    leave_type: LeaveType
    unit: LeaveUnit
    quantity: Optional[Decimal] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None


class MeetingCreateDTO(BaseSchema):
    meeting_time: datetime
    location: str
    participants: str
    agenda: str
    decision: str


class OfficeExpenseCreateDTO(BaseSchema):
    category: str
    amount: Decimal
    expense_date: date
    description: Optional[str] = None


class MaterialCreateDTO(BaseSchema):
    name: str
    unit: str = "件"
    minimum_stock: Decimal = Decimal("0")


class MaterialReceiptCreateDTO(BaseSchema):
    material_id: int
    project_id: Optional[int] = None
    supplier: str
    purchase_date: date
    unit_price: Decimal
    quantity: Decimal
    invoice_attachment: Optional[str] = None


class MaterialUsageCreateDTO(BaseSchema):
    material_id: int
    project_id: int
    employee_id: Optional[int] = None
    usage_date: date
    quantity: Decimal
    remark: Optional[str] = None


class SalaryConfigCreateDTO(BaseSchema):
    employee_id: int
    job_title: str
    base_salary: Decimal
    position_allowance: Decimal = Decimal("0")
    performance_bonus: Decimal = Decimal("0")
    late_penalty: Decimal = Decimal("0")
    is_sick_leave_paid: bool = True
    is_personal_leave_paid: bool = False
    hire_date: Optional[date] = None


class SalaryConfigUpdateDTO(BaseSchema):
    job_title: Optional[str] = None
    base_salary: Optional[Decimal] = None
    position_allowance: Optional[Decimal] = None
    performance_bonus: Optional[Decimal] = None
    late_penalty: Optional[Decimal] = None
    is_sick_leave_paid: Optional[bool] = None
    is_personal_leave_paid: Optional[bool] = None
    hire_date: Optional[date] = None


class SalaryCalculationDTO(BaseSchema):
    employee_id: int
    year_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    remark: Optional[str] = None


class SalaryApprovalDTO(BaseSchema):
    approved: bool
    comment: Optional[str] = None


class MarkSalaryPaidDTO(BaseSchema):
    pay_date: date
    remark: Optional[str] = None


class ExpenseRequestCreateDTO(BaseSchema):
    project_id: Optional[int] = None
    amount: Decimal
    purpose: str
    invoice_attachment: Optional[str] = None


class ExpenseApprovalDTO(BaseSchema):
    approved: bool
    comment: Optional[str] = None


class PaymentCreateDTO(BaseSchema):
    payee: str
    amount: Decimal
    payment_method: str
    payment_date: date
    attachment: str = Field(min_length=1)


class PaymentReviewDTO(BaseSchema):
    approved: bool
    comment: Optional[str] = None
