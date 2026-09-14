from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from models import CooperationType, OfficeExpenseCategory, UserRole


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


class PaymentStageCreateDTO(BaseModel):
    stage_name: str
    trigger_description: str
    target_progress: Optional[int] = Field(default=None, ge=0, le=100)
    planned_percentage: Decimal = Field(ge=0, le=100)
    planned_amount: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None


class PaymentStageReceiveDTO(BaseModel):
    received_amount: Decimal = Field(gt=0)
    received_date: date
    notes: Optional[str] = None


class ProjectCreateDTO(BaseModel):
    name: str
    contract_number: str
    client_name: str
    contract_amount: Decimal = Field(ge=0)
    cooperation_type: CooperationType
    contract_total_price: Decimal = Field(ge=0)
    payment_stages: List[PaymentStageCreateDTO] = Field(default_factory=list)


class AttendanceCreateDTO(BaseModel):
    user_id: int
    attendance_date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    project_id: Optional[int] = None
    is_supervisor_record: bool = False
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.check_in_time and self.check_out_time and self.check_out_time < self.check_in_time:
            raise ValueError("下班时间不能早于上班时间")
        return self


class MeetingMinuteCreateDTO(BaseModel):
    title: str
    meeting_time: datetime
    location: str
    host: str
    attendees: List[str]
    topics: str
    decisions: Optional[str] = None
    content: str
    attachment_path: Optional[str] = None


class OfficeExpenseCreateDTO(BaseModel):
    item_name: str
    project_name: Optional[str] = None
    category: OfficeExpenseCategory
    amount: Decimal = Field(gt=0)
    payment_date: date
    payer: str
    receipt_path: Optional[str] = None
    note: Optional[str] = None
    is_recurring: bool = False
    reminder_day: Optional[int] = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def validate_reminder(self):
        if self.is_recurring and not self.reminder_day:
            raise ValueError("定期费用必须设置提醒日期")
        return self
