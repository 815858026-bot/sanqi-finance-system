"""项目与收款管理。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import CollectionPlan, CollectionRecord, Project, User, UserRole, get_db
from schemas import CollectionPlanCreateDTO, CollectionRecordCreateDTO, ProjectCreateDTO, ProjectUpdateDTO
from security import get_current_user

router = APIRouter(prefix="/api/projects", tags=["项目与收款"])


def _money(value: Decimal | None) -> float:
    return float(value or 0)


def _ensure_finance_editor(current_user: User) -> None:
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅财务可创建或修改项目")


def _audit(db: Session, current_user: User, action: str, target: str, detail: str) -> None:
    from models import AuditLog

    db.add(AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action=action,
        target=target,
        detail=detail,
    ))


@router.get("", summary="项目列表")
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    project_ids = [project.id for project in projects]
    plan_rows = db.scalars(select(CollectionPlan).where(CollectionPlan.project_id.in_(project_ids)) if project_ids else select(CollectionPlan).where(False)).all()
    record_rows = db.scalars(select(CollectionRecord).where(CollectionRecord.project_id.in_(project_ids)) if project_ids else select(CollectionRecord).where(False)).all()
    plan_totals: dict[int, Decimal] = {}
    record_totals: dict[int, Decimal] = {}
    for plan in plan_rows:
        plan_totals[plan.project_id] = plan_totals.get(plan.project_id, Decimal("0")) + Decimal(plan.planned_amount)
    for record in record_rows:
        record_totals[record.project_id] = record_totals.get(record.project_id, Decimal("0")) + Decimal(record.amount)
    return [{
        "id": project.id,
        "name": project.name,
        "contract_number": project.contract_number,
        "client_name": project.client_name,
        "site_name": project.site_name,
        "cooperation_mode": project.cooperation_mode.value,
        "contract_amount": _money(project.contract_amount),
        "status": project.status,
        "planned_collection": _money(plan_totals.get(project.id)),
        "received_amount": _money(record_totals.get(project.id)),
        "receivable_amount": _money(Decimal(project.contract_amount) - record_totals.get(project.id, Decimal("0"))),
        "created_at": project.created_at,
    } for project in projects]


@router.post("", summary="创建项目")
def create_project(dto: ProjectCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_finance_editor(current_user)
    if db.scalar(select(Project).where(Project.contract_number == dto.contract_number)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="合同号已存在")
    project = Project(**dto.model_dump(), created_by=current_user.id)
    db.add(project)
    db.flush()
    _audit(db, current_user, "CREATE_PROJECT", f"Project #{project.id}", f"创建项目 {project.name}")
    db.commit()
    db.refresh(project)
    return {"message": "项目创建成功", "id": project.id}


@router.patch("/{project_id}", summary="更新项目")
def update_project(project_id: int, dto: ProjectUpdateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_finance_editor(current_user)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    for key, value in dto.model_dump(exclude_none=True).items():
        setattr(project, key, value)
    _audit(db, current_user, "UPDATE_PROJECT", f"Project #{project.id}", f"更新项目 {project.name}")
    db.commit()
    return {"message": "项目更新成功"}


@router.post("/{project_id}/plans", summary="新增收款计划")
def create_collection_plan(project_id: int, dto: CollectionPlanCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_finance_editor(current_user)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    plan = CollectionPlan(project_id=project_id, **dto.model_dump())
    db.add(plan)
    _audit(db, current_user, "CREATE_COLLECTION_PLAN", f"Project #{project_id}", f"新增收款计划 {dto.stage_name}")
    db.commit()
    return {"message": "收款计划已创建"}


@router.get("/{project_id}/plans", summary="收款计划列表")
def list_collection_plans(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plans = db.scalars(select(CollectionPlan).where(CollectionPlan.project_id == project_id).order_by(CollectionPlan.created_at.asc())).all()
    return [{
        "id": plan.id,
        "stage_name": plan.stage_name,
        "planned_amount": _money(plan.planned_amount),
        "planned_date": plan.planned_date,
    } for plan in plans]


@router.post("/{project_id}/collections", summary="登记实际收款")
def create_collection_record(project_id: int, dto: CollectionRecordCreateDTO, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_finance_editor(current_user)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    record = CollectionRecord(project_id=project_id, created_by=current_user.id, **dto.model_dump())
    db.add(record)
    _audit(db, current_user, "CREATE_COLLECTION_RECORD", f"Project #{project_id}", f"登记收款 {_money(dto.amount)}")
    db.commit()
    return {"message": "收款已登记"}


@router.get("/{project_id}/collections", summary="查看项目收款进度")
def list_collection_records(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    rows = db.scalars(select(CollectionRecord).where(CollectionRecord.project_id == project_id).order_by(CollectionRecord.received_date.desc())).all()
    received_total = sum((Decimal(item.amount) for item in rows), Decimal("0"))
    return {
        "project_id": project_id,
        "contract_amount": _money(project.contract_amount),
        "received_amount": _money(received_total),
        "receivable_amount": _money(Decimal(project.contract_amount) - received_total),
        "records": [{
            "id": item.id,
            "plan_id": item.plan_id,
            "amount": _money(item.amount),
            "received_date": item.received_date,
            "remark": item.remark,
        } for item in rows],
    }
