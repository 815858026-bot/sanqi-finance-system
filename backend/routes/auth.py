"""
三七设计财务系统 - 认证路由（JWT + 微信登录）
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from config import settings
from models import User, UserRole, get_db
from security import (
    get_password_hash, verify_password, create_access_token,
    get_current_user
)
from schemas import Token, UserLoginDTO

router = APIRouter(prefix="/api/auth", tags=["认证"])

# ============================================================================
# JWT 登录
# ============================================================================
@router.post("/login", response_model=Token, summary="用户登录（获取 JWT Token）")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录端点
    - username: 用户名
    - password: 密码
    
    返回: access_token, token_type, role, full_name
    """
    user = db.scalar(select(User).where(User.username == form_data.username))
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被停用"
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "full_name": user.full_name,
        "user_id": user.id
    }

# ============================================================================
# 微信登录
# ============================================================================
@router.get("/wechat/login", summary="微信授权登录链接生成")
def get_wechat_login_url():
    """
    返回微信 OAuth2 授权 URL
    前端重定向到此 URL 进行微信授权
    """
    redirect_uri = settings.wechat_callback_url
    scope = "snsapi_userinfo"
    state = "sanqi_finance_login"
    
    login_url = f"""
    https://open.weixin.qq.com/connect/oauth2/authorize?
    appid={settings.wechat_appid}
    &redirect_uri={redirect_uri}
    &response_type=code
    &scope={scope}
    &state={state}
    """.replace("\n", "").replace(" ", "")
    
    return {"login_url": login_url}

@router.get("/wechat/callback", summary="微信授权回调")
def wechat_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    微信授权回调处理
    - 用 code 换取 access_token
    - 获取用户信息
    - 创建或更新用户
    - 返回 JWT Token
    """
    # TODO: 实现微信 OAuth2 流程
    # 1. 用 code 换取 access_token
    # 2. 用 access_token 获取用户信息
    # 3. 检查用户是否存在
    # 4. 不存在则创建新用户
    # 5. 返回 JWT Token
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="微信登录功能开发中"
    )

# ============================================================================
# 当前用户信息
# ============================================================================
@router.get("/me", summary="获取当前登录用户信息")
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的详细信息
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "email": current_user.email,
        "phone": current_user.phone,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

@router.post("/refresh-token", response_model=Token, summary="刷新 Token")
def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    刷新用户的 JWT Token
    """
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": current_user.role.value,
        "full_name": current_user.full_name,
        "user_id": current_user.id
    }
