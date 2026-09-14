"""
三七设计财务系统 - 审计日志路由
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from models import AuditLog, User, get_db
from security import get_current_user
from schemas import AuditLogDTO, AuditLogFilterDTO

router = APIRouter(prefix="/api/audit", tags=["审计日志"])

# ============================================================================
# 审计日志查询
# ============================================================================
@router.get("/logs", response_model=List[AuditLogDTO], summary="查询审计日志")
def get_audit_logs(
    action: Optional[str] = None,
    operator_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询审计日志
    - action: 操作类型（可选）
    - operator_id: 操作者ID（可选）
    - start_date: 开始时间（可选）
    - end_date: 结束时间（可选）
    """
    query = select(AuditLog)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    if operator_id:
        query = query.where(AuditLog.operator_id == operator_id)
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    logs = db.scalars(
        query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    ).all()
    
    return [{
        "id": log.id,
        "operator_id": log.operator_id,
        "operator_name": log.operator_name,
        "action": log.action,
        "target": log.target,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at
    } for log in logs]

@router.get("/logs/{log_id}", response_model=AuditLogDTO, summary="获取具体日志")
def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定的审计日志详情
    """
    log = db.get(AuditLog, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="日志不存在"
        )
    
    return {
        "id": log.id,
        "operator_id": log.operator_id,
        "operator_name": log.operator_name,
        "action": log.action,
        "target": log.target,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at
    }

@router.get("/statistics", summary="审计日志统计")
def get_audit_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取审计日志统计数据
    """
    from sqlalchemy import func
    
    query = select(AuditLog)
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # 按操作类型统计
    actions = db.scalars(
        select(AuditLog.action).where(
            AuditLog.created_at >= (start_date or datetime.min),
            AuditLog.created_at <= (end_date or datetime.max)
        ).distinct()
    ).all()
    
    action_stats = {}
    for action in actions:
        count = db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == action)
        ) or 0
        action_stats[action] = count
    
    # 按操作者统计
    total_logs = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= (start_date or datetime.min),
            AuditLog.created_at <= (end_date or datetime.max)
        )
    ) or 0
    
    return {
        "total_logs": total_logs,
        "by_action": action_stats,
        "start_date": start_date,
        "end_date": end_date
    }
