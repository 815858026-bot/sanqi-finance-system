from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Meeting, User, UserRole, add_audit_log, get_db
from schemas import MeetingCreateDTO, MeetingUpdateDTO
from security import get_current_user, require_roles


router = APIRouter(prefix="/api/meetings", tags=["会议纪要"])


def _meeting_to_dict(meeting: Meeting) -> dict:
    return {
        "id": meeting.id,
        "title": meeting.title,
        "meeting_time": meeting.meeting_time,
        "location": meeting.location,
        "host_id": meeting.host_id,
        "host_name": meeting.host_name,
        "attendees": meeting.attendees,
        "agenda": meeting.agenda,
        "resolution": meeting.resolution,
        "minutes": meeting.minutes,
        "attachment_name": meeting.attachment_name,
        "attachment_url": meeting.attachment_url,
        "is_archived": meeting.is_archived,
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
    }


@router.get("")
def list_meetings(archived: bool | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Meeting)
    if archived is not None:
        query = query.where(Meeting.is_archived == archived)
    meetings = db.scalars(query.order_by(Meeting.meeting_time.desc())).all()
    return [_meeting_to_dict(meeting) for meeting in meetings]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_meeting(
    dto: MeetingCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.PARTNER)),
    db: Session = Depends(get_db),
):
    meeting = Meeting(
        title=dto.title,
        meeting_time=dto.meeting_time,
        location=dto.location,
        host_id=current_user.id,
        host_name=dto.host_name or current_user.full_name,
        attendees=dto.attendees,
        agenda=dto.agenda,
        resolution=dto.resolution,
        minutes=dto.minutes,
        attachment_name=dto.attachment_name,
        attachment_url=dto.attachment_url,
    )
    db.add(meeting)
    db.flush()
    add_audit_log(db, current_user, "CREATE_MEETING", f"Meeting #{meeting.id}", f"创建会议 {meeting.title}")
    db.commit()
    db.refresh(meeting)
    return _meeting_to_dict(meeting)


@router.get("/{meeting_id}")
def get_meeting(meeting_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return _meeting_to_dict(meeting)


@router.patch("/{meeting_id}")
def update_meeting(
    meeting_id: int,
    dto: MeetingUpdateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.PARTNER)),
    db: Session = Depends(get_db),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")

    for key, value in dto.model_dump(exclude_unset=True).items():
        setattr(meeting, key, value)

    add_audit_log(db, current_user, "UPDATE_MEETING", f"Meeting #{meeting.id}", f"更新会议 {meeting.title}")
    db.commit()
    db.refresh(meeting)
    return _meeting_to_dict(meeting)


@router.post("/{meeting_id}/archive")
def archive_meeting(
    meeting_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.PARTNER)),
    db: Session = Depends(get_db),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    meeting.is_archived = True
    add_audit_log(db, current_user, "ARCHIVE_MEETING", f"Meeting #{meeting.id}", f"归档会议 {meeting.title}")
    db.commit()
    return {"message": "会议已归档"}
