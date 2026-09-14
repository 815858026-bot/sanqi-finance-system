import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AttendanceRecord, AuditLog, Project, User, UserRole, get_db
from schemas import AttendanceCreateDTO
from security import get_current_user

router = APIRouter(prefix="/api/attendance", tags=["考勤管理"])

WORK_START = time(9, 0)
WORK_END = time(18, 0)
REST_DAY = 1  # Tuesday


def _can_manage_attendance(current_user: User, user_id: int) -> bool:
    return current_user.role in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT} or current_user.id == user_id


def _serialize_record(record: AttendanceRecord) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "user_name": record.user.full_name,
        "attendance_date": record.attendance_date,
        "check_in_time": record.check_in_time,
        "check_out_time": record.check_out_time,
        "project_id": record.project_id,
        "project_name": record.project.name if record.project else None,
        "is_supervisor_record": record.is_supervisor_record,
        "notes": record.notes,
        "is_late": bool(record.check_in_time and record.check_in_time.time() > WORK_START),
        "is_early_leave": bool(record.check_out_time and record.check_out_time.time() < WORK_END),
        "is_rest_day": record.attendance_date.weekday() == REST_DAY,
    }


@router.get("", summary="查询考勤记录")
def list_attendance_records(
    start_date: date | None = None,
    end_date: date | None = None,
    user_id: int | None = None,
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(AttendanceRecord)
    if start_date:
        query = query.where(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        query = query.where(AttendanceRecord.attendance_date <= end_date)
    if user_id:
        query = query.where(AttendanceRecord.user_id == user_id)
    if project_id:
        query = query.where(AttendanceRecord.project_id == project_id)
    records = db.scalars(query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.id.desc())).all()
    return [_serialize_record(record) for record in records]


@router.post("", summary="登记打卡")
def create_attendance_record(
    dto: AttendanceCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _can_manage_attendance(current_user, dto.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限登记该员工考勤")
    user = db.get(User, dto.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")
    if dto.project_id:
        project = db.get(Project, dto.project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工地项目不存在")
    record = AttendanceRecord(**dto.model_dump())
    db.add(record)
    db.flush()
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="CREATE_ATTENDANCE",
            target=f"Attendance #{record.id}",
            detail=f"登记 {user.full_name} 于 {dto.attendance_date} 的考勤",
        )
    )
    db.commit()
    db.refresh(record)
    return _serialize_record(record)


@router.get("/statistics", summary="考勤统计")
def attendance_statistics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束日期不能早于开始日期")

    query = select(AttendanceRecord).where(
        AttendanceRecord.attendance_date >= start_date,
        AttendanceRecord.attendance_date <= end_date,
    )
    if user_id:
        query = query.where(AttendanceRecord.user_id == user_id)
    records = db.scalars(query.order_by(AttendanceRecord.attendance_date.asc())).all()

    grouped: dict[int, dict[date, list[AttendanceRecord]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        grouped[record.user_id][record.attendance_date].append(record)

    if user_id:
        users = [db.get(User, user_id)] if db.get(User, user_id) else []
    else:
        users = db.scalars(select(User).where(User.is_active == True)).all()

    expected_days = 0
    cursor = start_date
    while cursor <= end_date:
        if cursor.weekday() != REST_DAY:
            expected_days += 1
        cursor += timedelta(days=1)

    items = []
    total_present = total_late = total_early = total_absent = 0
    for user in users:
        if not user:
            continue
        days = grouped[user.id]
        present_days = len(days)
        late_count = 0
        early_count = 0
        for day_records in days.values():
            earliest_in = min((r.check_in_time for r in day_records if r.check_in_time), default=None)
            latest_out = max((r.check_out_time for r in day_records if r.check_out_time), default=None)
            if earliest_in and earliest_in.time() > WORK_START:
                late_count += 1
            if latest_out and latest_out.time() < WORK_END:
                early_count += 1
        absent_days = max(expected_days - present_days, 0)
        total_present += present_days
        total_late += late_count
        total_early += early_count
        total_absent += absent_days
        attendance_rate = round((present_days / expected_days) * 100, 2) if expected_days else 100
        items.append(
            {
                "user_id": user.id,
                "user_name": user.full_name,
                "expected_days": expected_days,
                "present_days": present_days,
                "attendance_rate": attendance_rate,
                "late_count": late_count,
                "early_leave_count": early_count,
                "absent_days": absent_days,
            }
        )

    overall_rate = round((total_present / (expected_days * len(items))) * 100, 2) if items and expected_days else 100
    return {
        "work_schedule": {"morning": "09:00-12:00", "afternoon": "14:00-18:00", "weekly_rest_day": "星期二"},
        "summary": {
            "expected_days": expected_days,
            "present_days": total_present,
            "attendance_rate": overall_rate,
            "late_count": total_late,
            "early_leave_count": total_early,
            "absent_days": total_absent,
        },
        "items": items,
    }


@router.get("/export", summary="导出考勤报表")
def export_attendance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = attendance_statistics(start_date, end_date, None, current_user, db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["员工", "应出勤", "实出勤", "出勤率", "迟到", "早退", "旷工"])
    for item in stats["items"]:
        writer.writerow([
            item["user_name"],
            item["expected_days"],
            item["present_days"],
            f"{item['attendance_rate']}%",
            item["late_count"],
            item["early_leave_count"],
            item["absent_days"],
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=attendance_{start_date}_{end_date}.csv"},
    )
