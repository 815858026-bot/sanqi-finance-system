from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import (
    PaymentStatus,
    Project,
    ProjectPaymentPhase,
    User,
    UserRole,
    add_audit_log,
    get_db,
)
from schemas import (
    PaymentPhaseCreateDTO,
    PaymentPhaseRecordDTO,
    ProjectCreateDTO,
    ProjectUpdateDTO,
)
from security import get_current_user, require_roles


router = APIRouter(prefix="/api/projects", tags=["项目管理"])


def _project_summary(project: Project) -> dict:
    planned = sum(Decimal(str(phase.planned_amount)) for phase in project.payment_phases)
    received = sum(Decimal(str(phase.actual_amount)) for phase in project.payment_phases)
    progress = float((received / planned) * 100) if planned else 0.0
    return {
        "id": project.id,
        "name": project.name,
        "contract_number": project.contract_number,
        "client_name": project.client_name,
        "contract_amount": float(project.contract_amount),
        "total_price": float(project.total_price),
        "cooperation_type": project.cooperation_type.value,
        "status": project.status.value,
        "description": project.description,
        "receivable_amount": float(planned),
        "received_amount": float(received),
        "collection_progress": round(progress, 2),
        "payment_phases": [
            {
                "id": phase.id,
                "phase_number": phase.phase_number,
                "phase_name": phase.phase_name,
                "trigger_progress": phase.trigger_progress,
                "payment_percent": phase.payment_percent,
                "planned_amount": float(phase.planned_amount),
                "actual_amount": float(phase.actual_amount),
                "due_date": phase.due_date,
                "payment_date": phase.payment_date,
                "status": phase.status.value,
            }
            for phase in sorted(project.payment_phases, key=lambda item: item.phase_number)
        ],
    }


@router.get("")
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).unique().all()
    return [_project_summary(project) for project in projects]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    dto: ProjectCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)),
    db: Session = Depends(get_db),
):
    if db.scalar(select(Project).where(Project.contract_number == dto.contract_number)):
        raise HTTPException(status_code=400, detail="合同号已存在")

    project = Project(
        name=dto.name,
        contract_number=dto.contract_number,
        client_name=dto.client_name,
        contract_amount=dto.contract_amount,
        total_price=dto.total_price if dto.total_price is not None else dto.contract_amount,
        cooperation_type=dto.cooperation_type,
        status=dto.status,
        description=dto.description,
    )
    db.add(project)
    db.flush()
    add_audit_log(db, current_user, "CREATE_PROJECT", f"Project #{project.id}", f"创建项目 {project.name}")
    db.commit()
    db.refresh(project)
    return _project_summary(project)


@router.post("/{project_id}/payment-phases")
def set_payment_phases(
    project_id: int,
    phases: list[PaymentPhaseCreateDTO],
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN)),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    total_percent = round(sum(phase.payment_percent for phase in phases), 2)
    if total_percent > 100.0 + 1e-6:
        raise HTTPException(status_code=400, detail="收款阶段占比总和不能超过 100%")

    db.query(ProjectPaymentPhase).filter(ProjectPaymentPhase.project_id == project_id).delete()
    for phase in phases:
        db.add(
            ProjectPaymentPhase(
                project_id=project_id,
                phase_number=phase.phase_number,
                phase_name=phase.phase_name,
                trigger_progress=phase.trigger_progress,
                payment_percent=phase.payment_percent,
                planned_amount=phase.planned_amount,
                due_date=phase.due_date,
            )
        )

    add_audit_log(db, current_user, "SET_PAYMENT_PHASES", f"Project #{project.id}", f"设置 {len(phases)} 个收款阶段")
    db.commit()
    db.refresh(project)
    return _project_summary(project)["payment_phases"]


@router.get("/{project_id}/payment-phases")
def list_payment_phases(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _project_summary(project)["payment_phases"]


@router.post("/payment-phases/{phase_id}/record")
def record_payment(
    phase_id: int,
    dto: PaymentPhaseRecordDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)),
    db: Session = Depends(get_db),
):
    phase = db.get(ProjectPaymentPhase, phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="收款阶段不存在")

    phase.actual_amount = Decimal(str(phase.actual_amount)) + dto.actual_amount
    phase.payment_date = dto.payment_date
    phase.status = PaymentStatus.PAID if Decimal(str(phase.actual_amount)) >= Decimal(str(phase.planned_amount)) else PaymentStatus.PARTIAL

    add_audit_log(db, current_user, "RECORD_PAYMENT", f"PaymentPhase #{phase.id}", f"登记收款 {dto.actual_amount}")
    db.commit()
    db.refresh(phase)
    return {
        "id": phase.id,
        "actual_amount": float(phase.actual_amount),
        "planned_amount": float(phase.planned_amount),
        "status": phase.status.value,
        "payment_date": phase.payment_date,
    }


@router.get("/collection-statistics")
def collection_statistics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.scalars(select(Project)).all()
    summary = [_project_summary(project) for project in projects]
    total_receivable = sum(item["receivable_amount"] for item in summary)
    total_received = sum(item["received_amount"] for item in summary)
    return {
        "total_receivable": round(total_receivable, 2),
        "total_received": round(total_received, 2),
        "total_outstanding": round(total_receivable - total_received, 2),
        "projects": summary,
    }


@router.get("/{project_id}")
def get_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _project_summary(project)


@router.patch("/{project_id}")
def update_project(
    project_id: int,
    dto: ProjectUpdateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT)),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    updates = dto.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(project, key, value)

    add_audit_log(db, current_user, "UPDATE_PROJECT", f"Project #{project.id}", f"更新项目 {project.name}")
    db.commit()
    db.refresh(project)
    return _project_summary(project)
