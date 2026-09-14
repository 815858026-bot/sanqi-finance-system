from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AttendanceRecord, AttendanceStatus, Project, User, UserRole, add_audit_log, get_db
from schemas import AttendanceCheckDTO
from security import get_current_user


router = APIRouter(prefix="/api/attendance", tags=["考勤管理"])

WORK_START = time(9, 0)
WORK_END = time(18, 0)
TUESDAY = 1


def _minutes_late(check_time: datetime) -> int:
    start_dt = datetime.combine(check_time.date(), WORK_START)
    delta = int((check_time - start_dt).total_seconds() // 60)
    return max(delta, 0)


def _minutes_early(check_time: datetime) -> int:
    end_dt = datetime.combine(check_time.date(), WORK_END)
    delta = int((end_dt - check_time).total_seconds() // 60)
    return max(delta, 0)


def _calculate_hours(check_in: datetime | None, check_out: datetime | None) -> float:
    if not check_in or not check_out or check_out <= check_in:
        return 0.0
    total = (check_out - check_in).total_seconds() / 3600
    lunch_overlap_start = datetime.combine(check_in.date(), time(12, 0))
    lunch_overlap_end = datetime.combine(check_in.date(), time(14, 0))
    lunch_seconds = max(0.0, (min(check_out, lunch_overlap_end) - max(check_in, lunch_overlap_start)).total_seconds())
    return round(max(total - lunch_seconds / 3600, 0.0), 2)


def _derive_status(work_date: date, late_minutes: int, early_minutes: int) -> AttendanceStatus:
    if work_date.weekday() == TUESDAY:
        return AttendanceStatus.REST_DAY
    if late_minutes and early_minutes:
        return AttendanceStatus.LATE_AND_EARLY
    if late_minutes:
        return AttendanceStatus.LATE
    if early_minutes:
        return AttendanceStatus.EARLY_LEAVE
    return AttendanceStatus.NORMAL


def _record_to_dict(record: AttendanceRecord) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "user_name": record.user.full_name if record.user else None,
        "project_id": record.project_id,
        "project_name": record.project.name if record.project else None,
        "work_date": record.work_date,
        "check_in_time": record.check_in_time,
        "check_out_time": record.check_out_time,
        "work_hours": record.work_hours,
        "status": record.status.value,
        "late_minutes": record.late_minutes,
        "early_leave_minutes": record.early_leave_minutes,
        "notes": record.notes,
    }


@router.get("/work-calendar")
def work_calendar(current_user: User = Depends(get_current_user)):
    return {
        "work_hours": {"morning": "09:00-12:00", "afternoon": "14:00-18:00"},
        "weekly_rest_day": "Tuesday",
    }


@router.post("/checkin")
def checkin(dto: AttendanceCheckDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_time = dto.check_time or datetime.utcnow()
    work_date = check_time.date()
    record = db.scalar(
        select(AttendanceRecord)
        .where(AttendanceRecord.user_id == current_user.id, AttendanceRecord.work_date == work_date)
    )
    if record and record.check_in_time:
        raise HTTPException(status_code=400, detail="今日已打上班卡")

    if dto.project_id and not db.get(Project, dto.project_id):
        raise HTTPException(status_code=404, detail="关联工地不存在")

    if not record:
        record = AttendanceRecord(user_id=current_user.id, work_date=work_date)
        db.add(record)

    record.project_id = dto.project_id
    record.check_in_time = check_time
    record.notes = dto.notes
    record.late_minutes = _minutes_late(check_time) if work_date.weekday() != TUESDAY else 0
    record.status = AttendanceStatus.PENDING if work_date.weekday() != TUESDAY else AttendanceStatus.REST_DAY

    db.flush()
    add_audit_log(db, current_user, "ATTENDANCE_CHECKIN", f"Attendance #{record.id}", f"上班打卡 {work_date}")
    db.commit()
    db.refresh(record)
    return _record_to_dict(record)


@router.post("/checkout")
def checkout(dto: AttendanceCheckDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_time = dto.check_time or datetime.utcnow()
    work_date = check_time.date()
    record = db.scalar(
        select(AttendanceRecord)
        .where(AttendanceRecord.user_id == current_user.id, AttendanceRecord.work_date == work_date)
    )
    if not record or not record.check_in_time:
        raise HTTPException(status_code=400, detail="请先完成上班打卡")
    if record.check_out_time:
        raise HTTPException(status_code=400, detail="今日已打下班卡")

    record.check_out_time = check_time
    record.notes = dto.notes or record.notes
    record.early_leave_minutes = _minutes_early(check_time) if work_date.weekday() != TUESDAY else 0
    record.work_hours = _calculate_hours(record.check_in_time, check_time)
    record.status = _derive_status(work_date, record.late_minutes, record.early_leave_minutes)

    add_audit_log(db, current_user, "ATTENDANCE_CHECKOUT", f"Attendance #{record.id}", f"下班打卡 {work_date}")
    db.commit()
    db.refresh(record)
    return _record_to_dict(record)


@router.get("/records")
def list_records(
    user_id: int | None = None,
    project_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(AttendanceRecord)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        query = query.where(AttendanceRecord.user_id == current_user.id)
    elif user_id:
        query = query.where(AttendanceRecord.user_id == user_id)
    if project_id:
        query = query.where(AttendanceRecord.project_id == project_id)
    if start_date:
        query = query.where(AttendanceRecord.work_date >= start_date)
    if end_date:
        query = query.where(AttendanceRecord.work_date <= end_date)
    records = db.scalars(query.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc())).all()
    return [_record_to_dict(record) for record in records]


@router.get("/statistics")
def attendance_statistics(
    user_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    end_date = end_date or date.today()
    start_date = start_date or end_date.replace(day=1)

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    if current_user.role in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        users = [db.get(User, user_id)] if user_id else db.scalars(select(User).where(User.is_active == True)).all()
        users = [user for user in users if user]
    else:
        users = [current_user]

    expected_days = 0
    attended_days = 0
    late_count = 0
    early_leave_count = 0
    records_payload = []

    for user in users:
        workday = start_date
        while workday <= end_date:
            if workday.weekday() != TUESDAY:
                expected_days += 1
            workday += timedelta(days=1)

        records = db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.user_id == user.id,
                AttendanceRecord.work_date >= start_date,
                AttendanceRecord.work_date <= end_date,
            )
        ).all()
        unique_days = {record.work_date for record in records if record.work_date.weekday() != TUESDAY}
        attended_days += len(unique_days)
        late_count += sum(1 for record in records if record.late_minutes > 0)
        early_leave_count += sum(1 for record in records if record.early_leave_minutes > 0)
        records_payload.extend(_record_to_dict(record) for record in records)

    absent_days = max(expected_days - attended_days, 0)
    attendance_rate = round((attended_days / expected_days) * 100, 2) if expected_days else 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "weekly_rest_day": "Tuesday",
        "expected_workdays": expected_days,
        "attended_days": attended_days,
        "absent_days": absent_days,
        "attendance_rate": attendance_rate,
        "late_count": late_count,
        "early_leave_count": early_leave_count,
        "records": records_payload,
    }


@router.get("/export", response_class=PlainTextResponse)
def export_records(
    user_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = list_records(user_id, None, start_date, end_date, current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "员工", "工地", "上班", "下班", "工时", "状态", "迟到分钟", "早退分钟"])
    for record in records:
        writer.writerow([
            record["work_date"],
            record["user_name"],
            record["project_name"] or "",
            record["check_in_time"] or "",
            record["check_out_time"] or "",
            record["work_hours"],
            record["status"],
            record["late_minutes"],
            record["early_leave_minutes"],
        ])
    return output.getvalue()
