from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import AuditLog, PaymentStage, PaymentStageStatus, Project, User, UserRole, get_db
from schemas import PaymentStageCreateDTO, PaymentStageReceiveDTO, ProjectCreateDTO
from security import get_current_user

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


@router.get("", summary="查询项目列表")
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = db.scalars(
        select(Project).options(selectinload(Project.payment_stages)).order_by(Project.created_at.desc())
    ).all()
    result = []
    for project in projects:
        received_total = sum(Decimal(stage.received_amount or 0) for stage in project.payment_stages)
        result.append(
            {
                "id": project.id,
                "name": project.name,
                "contract_number": project.contract_number,
                "client_name": project.client_name,
                "contract_amount": float(project.contract_amount or 0),
                "cooperation_type": project.cooperation_type.value,
                "contract_total_price": float(project.contract_total_price or 0),
                "status": project.status,
                "payment_stages": [
                    {
                        "id": stage.id,
                        "stage_name": stage.stage_name,
                        "trigger_description": stage.trigger_description,
                        "target_progress": stage.target_progress,
                        "planned_percentage": float(stage.planned_percentage or 0),
                        "planned_amount": float(stage.planned_amount or 0),
                        "received_amount": float(stage.received_amount or 0),
                        "received_date": stage.received_date,
                        "status": stage.status.value,
                        "notes": stage.notes,
                    }
                    for stage in sorted(project.payment_stages, key=lambda item: item.id)
                ],
                "payment_summary": {
                    "receivable": float(project.contract_total_price or 0),
                    "received": float(received_total),
                    "outstanding": float((project.contract_total_price or 0) - received_total),
                },
            }
        )
    return result


@router.post("", summary="创建项目")
def create_project(
    dto: ProjectCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限创建项目")
    if db.scalar(select(Project).where(Project.contract_number == dto.contract_number)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="合同号已存在")

    project = Project(
        name=dto.name,
        contract_number=dto.contract_number,
        client_name=dto.client_name,
        contract_amount=dto.contract_amount,
        cooperation_type=dto.cooperation_type,
        contract_total_price=dto.contract_total_price,
    )
    db.add(project)
    db.flush()

    stages = dto.payment_stages or [
        PaymentStageCreateDTO(stage_name="第一期", trigger_description="签约后支付", planned_percentage=Decimal("30")),
        PaymentStageCreateDTO(stage_name="第二期", trigger_description="施工进度达到 60%", target_progress=60, planned_percentage=Decimal("40")),
        PaymentStageCreateDTO(stage_name="第三期", trigger_description="完工时支付余款", target_progress=100, planned_percentage=Decimal("30")),
    ]

    for stage_dto in stages:
        planned_amount = stage_dto.planned_amount
        if planned_amount is None:
            planned_amount = dto.contract_total_price * stage_dto.planned_percentage / Decimal("100")
        db.add(
            PaymentStage(
                project_id=project.id,
                stage_name=stage_dto.stage_name,
                trigger_description=stage_dto.trigger_description,
                target_progress=stage_dto.target_progress,
                planned_percentage=stage_dto.planned_percentage,
                planned_amount=planned_amount,
                notes=stage_dto.notes,
            )
        )

    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="CREATE_PROJECT",
            target=f"Project #{project.id}",
            detail=f"创建项目 {project.name}，合作方式 {dto.cooperation_type.value}",
        )
    )
    db.commit()
    return {"message": "项目创建成功", "project_id": project.id}


@router.post("/{project_id}/payment-stages", summary="新增收款阶段")
def create_payment_stage(
    project_id: int,
    dto: PaymentStageCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限新增收款阶段")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    planned_amount = dto.planned_amount
    if planned_amount is None:
        planned_amount = (project.contract_total_price or 0) * dto.planned_percentage / Decimal("100")

    stage = PaymentStage(
        project_id=project_id,
        stage_name=dto.stage_name,
        trigger_description=dto.trigger_description,
        target_progress=dto.target_progress,
        planned_percentage=dto.planned_percentage,
        planned_amount=planned_amount,
        notes=dto.notes,
    )
    db.add(stage)
    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="CREATE_PAYMENT_STAGE",
            target=f"Project #{project_id}",
            detail=f"新增收款阶段 {dto.stage_name}",
        )
    )
    db.commit()
    return {"message": "收款阶段已新增", "stage_id": stage.id}


@router.post("/payment-stages/{stage_id}/receive", summary="登记阶段收款")
def receive_payment(
    stage_id: int,
    dto: PaymentStageReceiveDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您没有权限登记收款")
    stage = db.get(PaymentStage, stage_id)
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="收款阶段不存在")

    stage.received_amount = (stage.received_amount or 0) + dto.received_amount
    stage.received_date = dto.received_date
    if stage.received_amount >= stage.planned_amount:
        stage.status = PaymentStageStatus.RECEIVED
    else:
        stage.status = PaymentStageStatus.PARTIAL
    if dto.notes:
        stage.notes = dto.notes

    db.add(
        AuditLog(
            operator_id=current_user.id,
            operator_name=f"{current_user.full_name}({current_user.username})",
            action="RECEIVE_PAYMENT",
            target=f"PaymentStage #{stage_id}",
            detail=f"登记收款 {float(dto.received_amount):.2f}",
        )
    )
    db.commit()
    return {"message": "收款登记成功"}


@router.get("/receivables/statistics", summary="项目收款统计")
def receivable_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = db.scalars(select(Project).options(selectinload(Project.payment_stages))).all()
    total_receivable = Decimal("0")
    total_received = Decimal("0")
    per_project = []
    for project in projects:
        receivable = Decimal(project.contract_total_price or 0)
        received = sum(Decimal(stage.received_amount or 0) for stage in project.payment_stages)
        total_receivable += receivable
        total_received += received
        per_project.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "receivable": float(receivable),
                "received": float(received),
                "outstanding": float(receivable - received),
            }
        )
    return {
        "total_receivable": float(total_receivable),
        "total_received": float(total_received),
        "total_outstanding": float(total_receivable - total_received),
        "projects": per_project,
    }
