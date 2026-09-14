import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models import AuditLog, MeetingMinute, MeetingStatus, User, UserRole, get_db
from schemas import MeetingMinuteCreateDTO
from security import get_current_user

router = APIRouter(prefix="/api/meetings", tags=["会议纪要"])


@router.get("", summary="查询会议纪要")
def list_meetings(
    status_filter: MeetingStatus | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(MeetingMinute)
    if status_filter:
        query = query.where(MeetingMinute.status == status_filter)
    meetings = db.scalars(query.order_by(MeetingMinute.meeting_time.desc())).all()
    result = []
    for meeting in meetings:
        if keyword and keyword not in f"{meeting.title}{meeting.location}{meeting.topics}{meeting.content}":
            continue
        result.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "meeting_time": meeting.meeting_time,
                "location": meeting.location,
                "host": meeting.host,
                "attendees": meeting.attendees.split("\n") if meeting.attendees else [],
                "topics": meeting.topics,
                "decisions": meeting.decisions,
                "content": meeting.content,
                "attachment_path": meeting.attachment_path,
                "status": meeting.status.value,
                "signed_off_by": meeting.signed_off_by.full_name if meeting.signed_off_by else None,
                "signed_off_at": meeting.signed_off_at,
            }
        )
    return result


@router.post("", summary="创建会议纪要")
def create_meeting(
    dto: MeetingMinuteCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限创建会议纪要")
    meeting = MeetingMinute(
        title=dto.title,
        meeting_time=dto.meeting_time,
        location=dto.location,
        host=dto.host,
        attendees="\n".join(dto.attendees),
        topics=dto.topics,
        decisions=dto.decisions,
        content=dto.content,
        attachment_path=dto.attachment_path,
        created_by_id=current_user.id,
    )
    db.add(meeting)
    db.flush()
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="CREATE_MEETING",
            target=f"Meeting #{meeting.id}",
            detail=f"创建会议纪要 {meeting.title}",
        )
    )
    db.commit()
    return {"message": "会议纪要创建成功", "meeting_id": meeting.id}


@router.post("/{meeting_id}/archive", summary="归档会议纪要")
def archive_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = db.get(MeetingMinute, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会议纪要不存在")
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限归档会议纪要")
    meeting.status = MeetingStatus.ARCHIVED
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="ARCHIVE_MEETING",
            target=f"Meeting #{meeting.id}",
            detail=f"归档会议纪要 {meeting.title}",
        )
    )
    db.commit()
    return {"message": "会议纪要已归档"}


@router.post("/{meeting_id}/sign", summary="会议纪要签批")
def sign_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = db.get(MeetingMinute, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会议纪要不存在")
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.PARTNER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限签批会议纪要")
    meeting.signed_off_by_id = current_user.id
    meeting.signed_off_at = datetime.utcnow()
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="SIGN_MEETING",
            target=f"Meeting #{meeting.id}",
            detail=f"签批会议纪要 {meeting.title}",
        )
    )
    db.commit()
    return {"message": "会议纪要已签批"}


@router.post("/upload", summary="上传会议附件")
def upload_meeting_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    os.makedirs(settings.upload_dir, exist_ok=True)
    meeting_dir = os.path.join(settings.upload_dir, "meetings")
    os.makedirs(meeting_dir, exist_ok=True)
    filename = f"{uuid4().hex}_{file.filename}"
    destination = os.path.join(meeting_dir, filename)
    with open(destination, "wb") as output:
        output.write(file.file.read())
    return {"attachment_path": destination.replace("./static", "/static")}
