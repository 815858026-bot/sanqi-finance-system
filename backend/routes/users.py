"""
三七设计财务系统 - 用户管理路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import User, UserRole, AuditLog, get_db
from security import get_password_hash, get_current_user, check_admin_permission
from schemas import UserDTO, CreateUserDTO, UpdateUserDTO, UserListDTO

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# ============================================================================
# 用户查询
# ============================================================================
@router.get("", response_model=List[UserListDTO], summary="查询所有用户")
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    is_active: bool = None,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    查询用户列表
    - skip: 跳过的记录数
    - limit: 返回的最大记录数
    - role: 按角色过滤（可选）
    - is_active: 按状态过滤（可选）
    """
    query = select(User)
    
    if role:
        query = query.where(User.role == UserRole[role])
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    users = db.scalars(
        query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    ).all()
    
    return [{
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": user.created_at
    } for user in users]

@router.get("/{user_id}", response_model=UserDTO, summary="获取用户详情")
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取指定用户的详细信息
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 只有管理员或用户自己可以查看用户信息
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ACCOUNTANT_ADMIN] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限查看该用户信息"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "openid": user.openid,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }

# ============================================================================
# 用户创建
# ============================================================================
@router.post("", summary="创建新用户")
def create_user(
    dto: CreateUserDTO,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    创建新用户账号
    - 超级管理员可以创建任何角色的用户
    - 财务主管只能创建财务人员
    """
    # 权限检查：财务主管不能创建管理员和合伙人
    if current_user.role == UserRole.ACCOUNTANT_ADMIN and dto.role in [
        UserRole.SUPER_ADMIN,
        UserRole.PARTNER
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="财务主管无权创建该角色的账号"
        )
    
    # 检查用户名是否已存在
    if db.scalar(select(User).where(User.username == dto.username)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新用户
    new_user = User(
        username=dto.username,
        hashed_password=get_password_hash(dto.password),
        full_name=dto.full_name,
        role=dto.role,
        email=dto.email,
        phone=dto.phone
    )
    db.add(new_user)
    db.flush()
    
    # 记录审计日志
    audit_log = AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action="CREATE_USER",
        target=f"User #{new_user.id}",
        detail=f"创建账号: {dto.full_name}, 角色: {dto.role.value}"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": "用户创建成功",
        "user_id": new_user.id,
        "username": new_user.username
    }

# ============================================================================
# 用户更新
# ============================================================================
@router.patch("/{user_id}", summary="更新用户信息")
def update_user(
    user_id: int,
    dto: UpdateUserDTO,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    更新用户信息
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新字段
    if dto.full_name:
        user.full_name = dto.full_name
    if dto.email:
        user.email = dto.email
    if dto.phone:
        user.phone = dto.phone
    
    db.commit()
    
    # 记录审计日志
    audit_log = AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action="UPDATE_USER",
        target=f"User #{user_id}",
        detail=f"更新用户信息: {dto.full_name or user.full_name}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "用户信息已更新"}

# ============================================================================
# 用户状态管理
# ============================================================================
@router.patch("/{user_id}/status", summary="启用/停用用户账号")
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    启用或停用用户账号（离职时立即停用）
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自身账号状态"
        )
    
    user.is_active = is_active
    db.commit()
    
    # 记录审计日志
    audit_log = AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action="UPDATE_USER_STATUS",
        target=f"User #{user_id}",
        detail=f"账号状态修改为: {'启用' if is_active else '停用/离职'}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": f"用户账号已{('启用' if is_active else '停用')}"}

# ============================================================================
# 密码管理
# ============================================================================
@router.post("/{user_id}/reset-password", summary="重置用户密码")
def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    管理员重置用户密码
    """
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度至少为 6 个字符"
        )
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # 记录审计日志
    audit_log = AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action="RESET_PASSWORD",
        target=f"User #{user_id}",
        detail=f"重置密码: {user.full_name}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "密码已重置"}

# ============================================================================
# 微信管理
# ============================================================================
@router.post("/{user_id}/unbind-wechat", summary="解绑微信")
def unbind_wechat(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    超级管理员强制解绑微信
    用户自己也可以解绑自己的微信
    """
    # 权限检查：只有超级管理员可以强制解绑他人微信，用户可以解绑自己的
    if current_user.role != UserRole.SUPER_ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限解绑该用户的微信"
        )
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    old_openid = user.openid
    user.openid = None
    db.commit()
    
    # 记录审计日志
    audit_log = AuditLog(
        operator_id=current_user.id,
        operator_name=f"{current_user.full_name}({current_user.username})",
        action="UNBIND_WECHAT",
        target=f"User #{user_id}",
        detail=f"解绑微信: {old_openid}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "微信已解绑"}
