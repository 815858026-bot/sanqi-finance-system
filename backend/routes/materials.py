from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    Material,
    MaterialInbound,
    MaterialInventory,
    MaterialOutbound,
    MaterialOutboundItem,
    MaterialOutboundStatus,
    Project,
    User,
    UserRole,
    add_audit_log,
    get_db,
)
from schemas import (
    MaterialCreateDTO,
    MaterialInboundCreateDTO,
    MaterialOutboundCreateDTO,
    MaterialUpdateDTO,
)
from security import get_current_user, require_roles


router = APIRouter(prefix="/api/materials", tags=["物料库存"])
ALLOWED_CATEGORIES = {"建材", "五金", "家居", "其他"}


def _inventory_for(db: Session, material_id: int) -> MaterialInventory:
    inventory = db.scalar(select(MaterialInventory).where(MaterialInventory.material_id == material_id))
    if not inventory:
        inventory = MaterialInventory(material_id=material_id, current_quantity=0)
        db.add(inventory)
        db.flush()
    return inventory


def _material_to_dict(db: Session, material: Material) -> dict:
    inventory = _inventory_for(db, material.id)
    return {
        "id": material.id,
        "code": material.code,
        "name": material.name,
        "specification": material.specification,
        "unit": material.unit,
        "cost_price": float(material.cost_price),
        "category": material.category,
        "warning_quantity": material.warning_quantity,
        "current_stock": inventory.current_quantity,
        "image_url": material.image_url,
        "description": material.description,
        "inventory_value": round(inventory.current_quantity * float(material.cost_price), 2),
        "created_at": material.created_at,
        "updated_at": material.updated_at,
    }


def _outbound_to_dict(outbound: MaterialOutbound) -> dict:
    return {
        "id": outbound.id,
        "project_id": outbound.project_id,
        "project_name": outbound.project_name,
        "requester_id": outbound.requester_id,
        "requester_name": outbound.requester_name,
        "purpose": outbound.purpose,
        "issue_date": outbound.issue_date,
        "status": outbound.status.value,
        "approved_by_id": outbound.approved_by_id,
        "approved_by_name": outbound.approved_by_name,
        "created_at": outbound.created_at,
        "items": [
            {
                "id": item.id,
                "material_id": item.material_id,
                "material_name": item.material_name,
                "quantity": item.quantity,
                "unit_cost": float(item.unit_cost),
                "total_cost": float(item.total_cost),
            }
            for item in outbound.items
        ],
    }


def _apply_outbound(db: Session, outbound: MaterialOutbound) -> None:
    for item in outbound.items:
        inventory = _inventory_for(db, item.material_id)
        if inventory.current_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"物料 {item.material_name} 库存不足")
        inventory.current_quantity -= item.quantity


@router.get("")
def list_materials(category: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Material)
    if category:
        query = query.where(Material.category == category)
    materials = db.scalars(query.order_by(Material.created_at.desc())).all()
    return [_material_to_dict(db, material) for material in materials]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_material(
    dto: MaterialCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
    db: Session = Depends(get_db),
):
    if dto.category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="不支持的物料分类")
    if db.scalar(select(Material).where(Material.code == dto.code)):
        raise HTTPException(status_code=400, detail="物料编号已存在")
    material = Material(**dto.model_dump())
    db.add(material)
    db.flush()
    db.add(MaterialInventory(material_id=material.id, current_quantity=0))
    add_audit_log(db, current_user, "CREATE_MATERIAL", f"Material #{material.id}", f"新增物料 {material.name}")
    db.commit()
    db.refresh(material)
    return _material_to_dict(db, material)


@router.get("/low-stock")
def low_stock(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    materials = db.scalars(select(Material)).all()
    items = []
    for material in materials:
        data = _material_to_dict(db, material)
        if data["current_stock"] < material.warning_quantity:
            items.append(data)
    return items


@router.get("/statistics")
def material_statistics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    materials = db.scalars(select(Material)).all()
    outbounds = db.scalars(select(MaterialOutbound)).all()
    total_value = 0.0
    material_stats = []
    project_costs = {}
    for material in materials:
        data = _material_to_dict(db, material)
        total_value += data["inventory_value"]
        inbound_qty = sum(item.quantity for item in db.scalars(select(MaterialInbound).where(MaterialInbound.material_id == material.id)).all())
        outbound_items = db.scalars(select(MaterialOutboundItem).where(MaterialOutboundItem.material_id == material.id)).all()
        outbound_qty = sum(item.quantity for item in outbound_items)
        material_stats.append({
            **data,
            "inbound_quantity": inbound_qty,
            "outbound_quantity": outbound_qty,
        })
    for outbound in outbounds:
        cost = sum(float(item.total_cost) for item in outbound.items)
        project_costs[outbound.project_name] = round(project_costs.get(outbound.project_name, 0.0) + cost, 2)
    return {
        "inventory_value": round(total_value, 2),
        "material_stats": material_stats,
        "project_costs": project_costs,
    }


@router.post("/inbounds", status_code=status.HTTP_201_CREATED)
def create_inbound(
    dto: MaterialInboundCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.ACCOUNTANT, UserRole.OFFICE_ADMIN)),
    db: Session = Depends(get_db),
):
    material = db.get(Material, dto.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    total_amount = dto.unit_price * dto.quantity
    inbound = MaterialInbound(
        material_id=material.id,
        purchase_date=dto.purchase_date,
        supplier=dto.supplier,
        unit_price=dto.unit_price,
        quantity=dto.quantity,
        total_amount=total_amount,
        invoice_url=dto.invoice_url,
        operator_id=current_user.id,
        operator_name=current_user.full_name,
    )
    db.add(inbound)
    inventory = _inventory_for(db, material.id)
    inventory.current_quantity += dto.quantity
    material.cost_price = dto.unit_price
    db.flush()
    add_audit_log(db, current_user, "CREATE_MATERIAL_INBOUND", f"MaterialInbound #{inbound.id}", f"入库 {material.name} x {dto.quantity}")
    db.commit()
    db.refresh(inbound)
    return {
        "id": inbound.id,
        "material_id": inbound.material_id,
        "quantity": inbound.quantity,
        "total_amount": float(inbound.total_amount),
        "current_stock": inventory.current_quantity,
    }


@router.get("/inbounds")
def list_inbounds(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(MaterialInbound).order_by(MaterialInbound.purchase_date.desc(), MaterialInbound.id.desc())).all()
    return [
        {
            "id": item.id,
            "material_id": item.material_id,
            "material_name": item.material.name if item.material else None,
            "purchase_date": item.purchase_date,
            "supplier": item.supplier,
            "unit_price": float(item.unit_price),
            "quantity": item.quantity,
            "total_amount": float(item.total_amount),
            "invoice_url": item.invoice_url,
            "operator_name": item.operator_name,
        }
        for item in items
    ]


@router.post("/outbounds", status_code=status.HTTP_201_CREATED)
def create_outbound(
    dto: MaterialOutboundCreateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.SUPERVISOR, UserRole.OFFICE_ADMIN, UserRole.ACCOUNTANT_ADMIN)),
    db: Session = Depends(get_db),
):
    if dto.project_id and not db.get(Project, dto.project_id):
        raise HTTPException(status_code=404, detail="关联工地不存在")
    outbound = MaterialOutbound(
        project_id=dto.project_id,
        project_name=dto.project_name,
        requester_id=current_user.id,
        requester_name=dto.requester_name or current_user.full_name,
        purpose=dto.purpose,
        issue_date=dto.issue_date,
        status=MaterialOutboundStatus.PENDING,
    )
    db.add(outbound)
    db.flush()

    for row in dto.items:
        if row.quantity <= 0:
            raise HTTPException(status_code=400, detail="领用数量必须大于 0")
        material = db.get(Material, row.material_id)
        if not material:
            raise HTTPException(status_code=404, detail=f"物料 {row.material_id} 不存在")
        db.add(
            MaterialOutboundItem(
                outbound_id=outbound.id,
                material_id=material.id,
                material_name=material.name,
                quantity=row.quantity,
                unit_cost=material.cost_price,
                total_cost=Decimal(str(material.cost_price)) * row.quantity,
            )
        )

    db.flush()
    if current_user.role in {UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.OFFICE_ADMIN}:
        outbound.status = MaterialOutboundStatus.APPROVED
        outbound.approved_by_id = current_user.id
        outbound.approved_by_name = current_user.full_name
        _apply_outbound(db, outbound)

    add_audit_log(db, current_user, "CREATE_MATERIAL_OUTBOUND", f"MaterialOutbound #{outbound.id}", f"创建领用单 {outbound.project_name}")
    db.commit()
    db.refresh(outbound)
    return _outbound_to_dict(outbound)


@router.get("/outbounds")
def list_outbounds(status_filter: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(MaterialOutbound)
    if current_user.role == UserRole.SUPERVISOR:
        query = query.where(MaterialOutbound.requester_id == current_user.id)
    if status_filter:
        query = query.where(MaterialOutbound.status == MaterialOutboundStatus(status_filter))
    outbounds = db.scalars(query.order_by(MaterialOutbound.issue_date.desc(), MaterialOutbound.id.desc())).unique().all()
    return [_outbound_to_dict(item) for item in outbounds]


@router.post("/outbounds/{outbound_id}/approve")
def approve_outbound(
    outbound_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN, UserRole.OFFICE_ADMIN)),
    db: Session = Depends(get_db),
):
    outbound = db.get(MaterialOutbound, outbound_id)
    if not outbound:
        raise HTTPException(status_code=404, detail="领用单不存在")
    if outbound.status == MaterialOutboundStatus.APPROVED:
        return _outbound_to_dict(outbound)
    _apply_outbound(db, outbound)
    outbound.status = MaterialOutboundStatus.APPROVED
    outbound.approved_by_id = current_user.id
    outbound.approved_by_name = current_user.full_name
    add_audit_log(db, current_user, "APPROVE_MATERIAL_OUTBOUND", f"MaterialOutbound #{outbound.id}", f"审批领用单 {outbound.id}")
    db.commit()
    db.refresh(outbound)
    return _outbound_to_dict(outbound)


@router.get("/{material_id}")
def get_material(material_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    return _material_to_dict(db, material)


@router.patch("/{material_id}")
def update_material(
    material_id: int,
    dto: MaterialUpdateDTO,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    for key, value in dto.model_dump(exclude_unset=True).items():
        setattr(material, key, value)
    add_audit_log(db, current_user, "UPDATE_MATERIAL", f"Material #{material.id}", f"更新物料 {material.name}")
    db.commit()
    db.refresh(material)
    return _material_to_dict(db, material)
