"""考勤、请假、会议、费用、库存与工资记录。"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from models import (
    ApprovalStatus,
    AttendanceRecord,
    AuditLog,
    ExpenseRequest,
    LeaveRecord,
    LeaveType,
    LeaveUnit,
    Material,
    MaterialReceipt,
    MaterialUsage,
    MeetingRecord,
    OfficeExpense,
    PaymentRecord,
    Project,
    SalaryConfig,
    SalarySlip,
    User,
    UserRole,
    get_db,
)
from schemas import (
    AttendanceCreateDTO,
    AttendanceUpdateDTO,
    ExpenseRequestCreateDTO,
    LeaveCreateDTO,
    MaterialCreateDTO,
    MaterialReceiptCreateDTO,
    MaterialUsageCreateDTO,
    MeetingCreateDTO,
    OfficeExpenseCreateDTO,
    SalaryCalculationDTO,
    SalaryConfigCreateDTO,
    SalaryConfigUpdateDTO,
)
from security import get_current_user

router = APIRouter(prefix="/api/records", tags=["记录管理"])

WORK_START = time(9, 0)
WORK_END = time(18, 0)
FULL_DAY_HOURS = Decimal("8")


def _money(value: Decimal | None) -> float:
    return float(value or 0)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _log(db: Session, current_user: User, action: str, target: str, detail: str, before_data: str | None = None, after_data: str | None = None) -> None:
    db.add(AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action=action,
        target=target,
        detail=detail,
        before_data=before_data,
        after_data=after_data,
    ))


def _require_roles(current_user: User, *roles: UserRole) -> None:
    if current_user.role not in set(roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限执行该操作")


def _attendance_value(work_date: date, check_in: time | None, check_out: time | None) -> Decimal:
    if work_date.weekday() == 1:
        return Decimal("0.00")
    if check_in and check_out:
        return Decimal("1.00")
    if check_in or check_out:
        return Decimal("0.50")
    return Decimal("0.00")


def _leave_quantity(dto: LeaveCreateDTO) -> Decimal:
    if dto.quantity is not None:
        return _quantize(Decimal(dto.quantity))
    if dto.unit == LeaveUnit.DAY:
        return Decimal("1.00")
    if not dto.start_time or not dto.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="按小时请假必须提供开始和结束时间")
    minutes = (datetime.combine(date.today(), dto.end_time) - datetime.combine(date.today(), dto.start_time)).total_seconds() / 60
    if minutes <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请假结束时间必须晚于开始时间")
    return _quantize(Decimal(minutes) / Decimal("60"))


def _scheduled_days(year_month: str) -> Decimal:
    year, month = map(int, year_month.split("-"))
    days_in_month = calendar.monthrange(year, month)[1]
    total = Decimal("0")
    for day in range(1, days_in_month + 1):
        current_day = date(year, month, day)
        if current_day.weekday() != 1:
            total += Decimal("1")
    return total


def _deductible_leave_days(leave: LeaveRecord, config: SalaryConfig) -> Decimal:
    quantity = Decimal(leave.quantity)
    leave_days = quantity if leave.unit == LeaveUnit.DAY else _quantize(quantity / FULL_DAY_HOURS)
    if leave.leave_type == LeaveType.UNPAID:
        return leave_days
    if leave.leave_type == LeaveType.PERSONAL and not config.is_personal_leave_paid:
        return leave_days
    if leave.leave_type == LeaveType.SICK and not config.is_sick_leave_paid:
        return leave_days
    return Decimal("0")


def _approval_status(level: int) -> ApprovalStatus:
    return {
        1: ApprovalStatus.PENDING_LEVEL_2,
        2: ApprovalStatus.PENDING_LEVEL_3,
        3: ApprovalStatus.APPROVED,
    }[level]


@router.get("/attendance", summary="查看考勤记录")
def list_attendance(employee_id: int | None = None, month: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(AttendanceRecord)
    if employee_id:
        query = query.where(AttendanceRecord.employee_id == employee_id)
    if month:
        query = query.where(func.strftime("%Y-%m", AttendanceRecord.work_date) == month)
    rows = db.scalars(query.order_by(AttendanceRecord.work_date.desc())).all()
    return [{
        "id": row.id,
        "employee_id": row.employee_id,
        "work_date": row.work_date,
        "check_in": row.check_in,
        "check_out": row.check_out,
        "is_late": row.is_late,
        "is_early_leave": row.is_early_leave,
        "attendance_days": float(row.attendance_days),
        "notes": row.notes,
    } for row in rows]


@router.post("/attendance", summary="记录或补打考勤")
def create_attendance(dto: AttendanceCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    record = db.scalar(select(AttendanceRecord).where(and_(AttendanceRecord.employee_id == dto.employee_id, AttendanceRecord.work_date == dto.work_date)))
    is_late = bool(dto.check_in and dto.check_in > WORK_START)
    is_early_leave = bool(dto.check_out and dto.check_out < WORK_END)
    attendance_days = _attendance_value(dto.work_date, dto.check_in, dto.check_out)
    if record:
        before = f"{record.check_in}-{record.check_out}"
        record.check_in = dto.check_in
        record.check_out = dto.check_out
        record.notes = dto.notes
        record.is_late = is_late
        record.is_early_leave = is_early_leave
        record.attendance_days = attendance_days
        _log(db, current_user, "UPDATE_ATTENDANCE", f"Attendance #{record.id}", "修改考勤记录", before_data=before, after_data=f"{dto.check_in}-{dto.check_out}")
    else:
        record = AttendanceRecord(
            employee_id=dto.employee_id,
            work_date=dto.work_date,
            check_in=dto.check_in,
            check_out=dto.check_out,
            notes=dto.notes,
            is_late=is_late,
            is_early_leave=is_early_leave,
            attendance_days=attendance_days,
            created_by=current_user.id,
        )
        db.add(record)
        _log(db, current_user, "CREATE_ATTENDANCE", f"Employee #{dto.employee_id}", "新增考勤记录")
    db.commit()
    return {"message": "考勤记录已保存", "attendance_days": float(attendance_days)}


@router.patch("/attendance/{attendance_id}", summary="修改考勤记录")
def update_attendance(attendance_id: int, dto: AttendanceUpdateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    record = db.get(AttendanceRecord, attendance_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考勤记录不存在")
    check_in = dto.check_in if dto.check_in is not None else record.check_in
    check_out = dto.check_out if dto.check_out is not None else record.check_out
    record.check_in = check_in
    record.check_out = check_out
    record.notes = dto.notes if dto.notes is not None else record.notes
    record.is_late = bool(check_in and check_in > WORK_START)
    record.is_early_leave = bool(check_out and check_out < WORK_END)
    record.attendance_days = _attendance_value(record.work_date, check_in, check_out)
    _log(db, current_user, "UPDATE_ATTENDANCE", f"Attendance #{attendance_id}", "修改考勤记录")
    db.commit()
    return {"message": "考勤记录更新成功"}


@router.get("/attendance/summary", summary="考勤统计")
def attendance_summary(employee_id: int, month: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id == employee_id, func.strftime("%Y-%m", AttendanceRecord.work_date) == month)).all()
    attendance_days = sum((Decimal(row.attendance_days) for row in rows), Decimal("0"))
    late_count = sum(1 for row in rows if row.is_late)
    early_leave_count = sum(1 for row in rows if row.is_early_leave)
    scheduled_days = _scheduled_days(month)
    return {
        "employee_id": employee_id,
        "month": month,
        "scheduled_days": float(scheduled_days),
        "attendance_days": float(attendance_days),
        "late_count": late_count,
        "early_leave_count": early_leave_count,
        "attendance_rate": float(_quantize((attendance_days / scheduled_days * Decimal("100")) if scheduled_days else Decimal("0"))),
    }


@router.get("/leaves", summary="查看请假记录")
def list_leaves(employee_id: int | None = None, month: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(LeaveRecord)
    if employee_id:
        query = query.where(LeaveRecord.employee_id == employee_id)
    if month:
        query = query.where(func.strftime("%Y-%m", LeaveRecord.leave_date) == month)
    rows = db.scalars(query.order_by(LeaveRecord.leave_date.desc(), LeaveRecord.created_at.desc())).all()
    return [{
        "id": row.id,
        "employee_id": row.employee_id,
        "leave_date": row.leave_date,
        "leave_type": row.leave_type.value,
        "unit": row.unit.value,
        "quantity": float(row.quantity),
        "start_time": row.start_time,
        "end_time": row.end_time,
        "reason": row.reason,
    } for row in rows]


@router.post("/leaves", summary="记录请假")
def create_leave(dto: LeaveCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    quantity = _leave_quantity(dto)
    leave = LeaveRecord(created_by=current_user.id, quantity=quantity, **dto.model_dump(exclude={"quantity"}))
    db.add(leave)
    _log(db, current_user, "CREATE_LEAVE", f"Employee #{dto.employee_id}", f"记录请假 {dto.leave_type.value} {float(quantity)}")
    db.commit()
    return {"message": "请假记录已保存", "quantity": float(quantity)}


@router.get("/leaves/summary", summary="请假统计")
def leave_summary(employee_id: int, month: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(LeaveRecord).where(LeaveRecord.employee_id == employee_id, func.strftime("%Y-%m", LeaveRecord.leave_date) == month)).all()
    totals: dict[str, Decimal] = {}
    all_days = Decimal("0")
    for row in rows:
        value = Decimal(row.quantity) if row.unit == LeaveUnit.DAY else _quantize(Decimal(row.quantity) / FULL_DAY_HOURS)
        totals[row.leave_type.value] = totals.get(row.leave_type.value, Decimal("0")) + value
        all_days += value
    return {"employee_id": employee_id, "month": month, "leave_days": float(all_days), "by_type": {key: float(value) for key, value in totals.items()}}


@router.get("/meetings", summary="会议纪要列表")
def list_meetings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(MeetingRecord).order_by(MeetingRecord.meeting_time.desc())).all()
    return [{
        "id": row.id,
        "meeting_time": row.meeting_time,
        "location": row.location,
        "participants": row.participants,
        "agenda": row.agenda,
        "decision": row.decision,
        "archived": row.archived,
    } for row in rows]


@router.post("/meetings", summary="创建会议纪要")
def create_meeting(dto: MeetingCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.PARTNER, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    meeting = MeetingRecord(created_by=current_user.id, **dto.model_dump())
    db.add(meeting)
    _log(db, current_user, "CREATE_MEETING", "Meeting", f"创建会议纪要 {dto.location}")
    db.commit()
    return {"message": "会议纪要已存档"}


@router.get("/office-expenses", summary="办公费用列表")
def list_office_expenses(month: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(OfficeExpense)
    if month:
        query = query.where(func.strftime("%Y-%m", OfficeExpense.expense_date) == month)
    rows = db.scalars(query.order_by(OfficeExpense.expense_date.desc())).all()
    return [{
        "id": row.id,
        "category": row.category,
        "amount": _money(row.amount),
        "expense_date": row.expense_date,
        "description": row.description,
    } for row in rows]


@router.post("/office-expenses", summary="记录办公费用")
def create_office_expense(dto: OfficeExpenseCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER)
    expense = OfficeExpense(created_by=current_user.id, **dto.model_dump())
    db.add(expense)
    _log(db, current_user, "CREATE_OFFICE_EXPENSE", "OfficeExpense", f"记录办公费用 {dto.category}")
    db.commit()
    return {"message": "办公费用已记录"}


@router.get("/office-expenses/summary", summary="办公费用月度汇总")
def office_expense_summary(month: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(OfficeExpense).where(func.strftime("%Y-%m", OfficeExpense.expense_date) == month)).all()
    by_category: dict[str, Decimal] = {}
    total = Decimal("0")
    for row in rows:
        amount = Decimal(row.amount)
        by_category[row.category] = by_category.get(row.category, Decimal("0")) + amount
        total += amount
    return {"month": month, "total": _money(total), "by_category": {key: _money(value) for key, value in by_category.items()}}


@router.get("/materials", summary="物料列表")
def list_materials(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    materials = db.scalars(select(Material).order_by(Material.created_at.desc())).all()
    return [{
        "id": item.id,
        "name": item.name,
        "unit": item.unit,
        "minimum_stock": _money(item.minimum_stock),
        "current_stock": _money(item.current_stock),
        "low_stock": Decimal(item.current_stock) <= Decimal(item.minimum_stock),
    } for item in materials]


@router.post("/materials", summary="创建物料")
def create_material(dto: MaterialCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    material = Material(created_by=current_user.id, **dto.model_dump())
    db.add(material)
    _log(db, current_user, "CREATE_MATERIAL", "Material", f"创建物料 {dto.name}")
    db.commit()
    return {"message": "物料已创建"}


@router.post("/materials/stock-in", summary="物料入库")
def stock_in_material(dto: MaterialReceiptCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    material = db.get(Material, dto.material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物料不存在")
    receipt = MaterialReceipt(created_by=current_user.id, **dto.model_dump())
    material.current_stock = _quantize(Decimal(material.current_stock) + Decimal(dto.quantity))
    db.add(receipt)
    _log(db, current_user, "MATERIAL_STOCK_IN", f"Material #{material.id}", f"入库 {float(dto.quantity)} {material.unit}")
    db.commit()
    return {"message": "入库成功", "current_stock": _money(Decimal(material.current_stock))}


@router.post("/materials/stock-out", summary="物料出库")
def stock_out_material(dto: MaterialUsageCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    material = db.get(Material, dto.material_id)
    project = db.get(Project, dto.project_id)
    if not material or not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物料或项目不存在")
    if Decimal(material.current_stock) < Decimal(dto.quantity):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="库存不足")
    usage = MaterialUsage(created_by=current_user.id, **dto.model_dump())
    material.current_stock = _quantize(Decimal(material.current_stock) - Decimal(dto.quantity))
    db.add(usage)
    _log(db, current_user, "MATERIAL_STOCK_OUT", f"Material #{material.id}", f"出库到项目 {project.name}")
    db.commit()
    return {"message": "出库成功", "current_stock": _money(Decimal(material.current_stock))}


@router.get("/materials/project-costs", summary="按工地统计材料成本")
def material_project_costs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(MaterialReceipt)).all()
    totals: dict[int, Decimal] = {}
    for row in rows:
        if row.project_id is None:
            continue
        totals[row.project_id] = totals.get(row.project_id, Decimal("0")) + Decimal(row.unit_price) * Decimal(row.quantity)
    projects = {project.id: project.name for project in db.scalars(select(Project)).all()}
    return [{"project_id": project_id, "project_name": projects.get(project_id, "未知项目"), "material_cost": _money(total)} for project_id, total in totals.items()]


@router.get("/salary-configs", summary="工资配置列表")
def list_salary_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(SalaryConfig).order_by(SalaryConfig.updated_at.desc())).all()
    return [{
        "id": row.id,
        "employee_id": row.employee_id,
        "job_title": row.job_title,
        "base_salary": _money(row.base_salary),
        "position_allowance": _money(row.position_allowance),
        "performance_bonus": _money(row.performance_bonus),
        "daily_salary": _money(row.daily_salary),
        "hourly_salary": _money(row.hourly_salary),
        "late_penalty": _money(row.late_penalty),
        "is_sick_leave_paid": row.is_sick_leave_paid,
        "is_personal_leave_paid": row.is_personal_leave_paid,
        "hire_date": row.hire_date,
    } for row in rows]


@router.post("/salary-configs", summary="创建工资配置")
def create_salary_config(dto: SalaryConfigCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    if db.scalar(select(SalaryConfig).where(SalaryConfig.employee_id == dto.employee_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该员工工资配置已存在")
    daily_salary = _quantize(Decimal(dto.base_salary) / Decimal("22"))
    hourly_salary = _quantize(daily_salary / FULL_DAY_HOURS)
    config = SalaryConfig(created_by=current_user.id, daily_salary=daily_salary, hourly_salary=hourly_salary, **dto.model_dump(exclude={"employee_id"}))
    config.employee_id = dto.employee_id
    db.add(config)
    _log(db, current_user, "CREATE_SALARY_CONFIG", f"Employee #{dto.employee_id}", "创建工资配置（不计算社保和个税）")
    db.commit()
    return {"message": "工资配置已创建", "daily_salary": _money(daily_salary), "hourly_salary": _money(hourly_salary)}


@router.patch("/salary-configs/{employee_id}", summary="更新工资配置")
def update_salary_config(employee_id: int, dto: SalaryConfigUpdateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    config = db.scalar(select(SalaryConfig).where(SalaryConfig.employee_id == employee_id))
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工资配置不存在")
    for key, value in dto.model_dump(exclude_none=True).items():
        setattr(config, key, value)
    if dto.base_salary is not None:
        config.daily_salary = _quantize(Decimal(config.base_salary) / Decimal("22"))
        config.hourly_salary = _quantize(Decimal(config.daily_salary) / FULL_DAY_HOURS)
    _log(db, current_user, "UPDATE_SALARY_CONFIG", f"Employee #{employee_id}", "更新工资配置（不计算社保和个税）")
    db.commit()
    return {"message": "工资配置已更新"}


@router.post("/salary-slips/calculate", summary="计算工资单")
def calculate_salary(dto: SalaryCalculationDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    config = db.scalar(select(SalaryConfig).where(SalaryConfig.employee_id == dto.employee_id))
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="请先创建工资配置")
    year_month = dto.year_month
    attendance_rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id == dto.employee_id, func.strftime("%Y-%m", AttendanceRecord.work_date) == year_month)).all()
    leave_rows = db.scalars(select(LeaveRecord).where(LeaveRecord.employee_id == dto.employee_id, func.strftime("%Y-%m", LeaveRecord.leave_date) == year_month)).all()
    attendance_days = sum((Decimal(row.attendance_days) for row in attendance_rows), Decimal("0"))
    late_count = sum(1 for row in attendance_rows if row.is_late)
    early_leave_count = sum(1 for row in attendance_rows if row.is_early_leave)
    leave_days = Decimal("0")
    deductible_leave_days = Decimal("0")
    for leave in leave_rows:
        converted = Decimal(leave.quantity) if leave.unit == LeaveUnit.DAY else _quantize(Decimal(leave.quantity) / FULL_DAY_HOURS)
        leave_days += converted
        deductible_leave_days += _deductible_leave_days(leave, config)
    leave_deduction = _quantize(Decimal(config.daily_salary) * deductible_leave_days)
    late_penalty_amount = _quantize(Decimal(config.late_penalty) * Decimal(late_count))
    gross_income = _quantize(Decimal(config.base_salary) + Decimal(config.position_allowance) + Decimal(config.performance_bonus))
    net_salary = _quantize(gross_income - leave_deduction - late_penalty_amount)
    slip = db.scalar(select(SalarySlip).where(SalarySlip.employee_id == dto.employee_id, SalarySlip.year_month == year_month))
    slip_number = f"SAL-{year_month.replace('-', '')}-{dto.employee_id:03d}"
    if not slip:
        slip = SalarySlip(
            slip_number=slip_number,
            employee_id=dto.employee_id,
            year_month=year_month,
            prepared_by=current_user.id,
        )
        db.add(slip)
    slip.base_salary = _quantize(Decimal(config.base_salary))
    slip.position_allowance = _quantize(Decimal(config.position_allowance))
    slip.performance_bonus = _quantize(Decimal(config.performance_bonus))
    slip.gross_income = gross_income
    slip.leave_deduction = leave_deduction
    slip.late_penalty_amount = late_penalty_amount
    slip.net_salary = net_salary
    slip.attendance_days = _quantize(attendance_days)
    slip.leave_days = _quantize(leave_days)
    slip.late_count = late_count
    slip.early_leave_count = early_leave_count
    slip.status = ApprovalStatus.PENDING
    slip.remark = dto.remark or "工资计算未包含社保与个人所得税"
    _log(db, current_user, "CALCULATE_SALARY", f"SalarySlip {slip_number}", f"计算工资单，未计算社保和个税")
    db.commit()
    return {
        "message": "工资单已生成",
        "slip_number": slip_number,
        "scheduled_days": float(_scheduled_days(year_month)),
        "attendance_days": float(slip.attendance_days),
        "leave_days": float(slip.leave_days),
        "gross_income": _money(gross_income),
        "leave_deduction": _money(leave_deduction),
        "late_penalty_amount": _money(late_penalty_amount),
        "social_insurance": 0,
        "personal_income_tax": 0,
        "net_salary": _money(net_salary),
    }


@router.get("/salary-slips", summary="工资单列表")
def list_salary_slips(month: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(SalarySlip)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.PARTNER, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER}:
        query = query.where(SalarySlip.employee_id == current_user.id)
    if month:
        query = query.where(SalarySlip.year_month == month)
    rows = db.scalars(query.order_by(SalarySlip.created_at.desc())).all()
    return [{
        "id": row.id,
        "slip_number": row.slip_number,
        "employee_id": row.employee_id,
        "year_month": row.year_month,
        "gross_income": _money(row.gross_income),
        "leave_deduction": _money(row.leave_deduction),
        "late_penalty_amount": _money(row.late_penalty_amount),
        "social_insurance": 0,
        "personal_income_tax": 0,
        "net_salary": _money(row.net_salary),
        "attendance_days": float(row.attendance_days),
        "leave_days": float(row.leave_days),
        "late_count": row.late_count,
        "early_leave_count": row.early_leave_count,
        "status": row.status.value,
        "pay_date": row.pay_date,
        "remark": row.remark,
    } for row in rows]


@router.get("/salary-slips/{slip_id}", summary="工资单详情")
def get_salary_slip(slip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(SalarySlip, slip_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工资单不存在")
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.PARTNER, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT, UserRole.CASHIER} and row.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限查看该工资单")
    return {
        "id": row.id,
        "slip_number": row.slip_number,
        "employee_id": row.employee_id,
        "year_month": row.year_month,
        "base_salary": _money(row.base_salary),
        "position_allowance": _money(row.position_allowance),
        "performance_bonus": _money(row.performance_bonus),
        "gross_income": _money(row.gross_income),
        "leave_deduction": _money(row.leave_deduction),
        "late_penalty_amount": _money(row.late_penalty_amount),
        "social_insurance": 0,
        "personal_income_tax": 0,
        "net_salary": _money(row.net_salary),
        "attendance_days": float(row.attendance_days),
        "leave_days": float(row.leave_days),
        "late_count": row.late_count,
        "early_leave_count": row.early_leave_count,
        "status": row.status.value,
        "pay_date": row.pay_date,
        "remark": row.remark,
    }


@router.post("/expense-requests", summary="创建支出单")
def create_expense_request(dto: ExpenseRequestCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_roles(current_user, UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)
    if dto.project_id and not db.get(Project, dto.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    expense = ExpenseRequest(created_by=current_user.id, **dto.model_dump())
    db.add(expense)
    _log(db, current_user, "CREATE_EXPENSE_REQUEST", "ExpenseRequest", "创建支出单")
    db.commit()
    return {"message": "支出单已创建", "id": expense.id}


@router.get("/expense-requests", summary="支出单列表")
def list_expense_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ExpenseRequest).order_by(ExpenseRequest.created_at.desc())).all()
    return [{
        "id": row.id,
        "project_id": row.project_id,
        "amount": _money(row.amount),
        "purpose": row.purpose,
        "invoice_attachment": row.invoice_attachment,
        "status": row.status.value,
        "created_by": row.created_by,
        "created_at": row.created_at,
    } for row in rows]


@router.get("/payments", summary="支付表列表")
def list_payments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentRecord).order_by(PaymentRecord.created_at.desc())).all()
    return [{
        "id": row.id,
        "expense_request_id": row.expense_request_id,
        "payee": row.payee,
        "amount": _money(row.amount),
        "payment_method": row.payment_method,
        "payment_date": row.payment_date,
        "attachment": row.attachment,
        "status": row.status.value,
        "cashier_id": row.cashier_id,
        "reviewed_by": row.reviewed_by,
    } for row in rows]
