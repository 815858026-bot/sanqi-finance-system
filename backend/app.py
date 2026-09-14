"""
三万设计财务系统 - FastAPI 主应用程序
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import init_db, Base, engine, SessionLocal, User, UserRole
from security import get_password_hash

# 导入路由
from routes import approval, attendance, audit, auth, dashboard, meetings, projects, records, users

# ============================================================================
# FastAPI 应用信息
# ============================================================================
app = FastAPI(
    title=settings.app_name,
    description="三万设计 - 企业级财务管理系统 | 支持完整项目算账、合伙人审批、离职接管、微信登录、数据备份。",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================================
# CORS 中間件
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 戒殶环境，用于子域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 执业Satic 文件
# ============================================================================
os.makedirs("./static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="./static"), name="static")

# ============================================================================
# 数据库初始化
# ============================================================================
@app.on_event("startup")
def startup_event():
    """
    应用启动時的初始化操作
    """
    # 创建数据库表
    init_db()
    
    # 创建默认用户
    db = SessionLocal()
    try:
        from sqlalchemy import select
        if not db.scalar(select(User)):
            default_users = [
                User(
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    full_name="李总(合伙人1)",
                    role=UserRole.SUPER_ADMIN,
                    email="admin@sanqidesign.com",
                    phone="13800138000"
                ),
                User(
                    username="partner2",
                    hashed_password=get_password_hash("123456"),
                    full_name="张总(合伙人2)",
                    role=UserRole.PARTNER,
                    email="partner2@sanqidesign.com",
                    phone="13800138001"
                ),
                User(
                    username="partner3",
                    hashed_password=get_password_hash("123456"),
                    full_name="王总(合伙人3)",
                    role=UserRole.PARTNER,
                    email="partner3@sanqidesign.com",
                    phone="13800138002"
                ),
                User(
                    username="acc_admin",
                    hashed_password=get_password_hash("123456"),
                    full_name="财务主管",
                    role=UserRole.ACCOUNTANT_ADMIN,
                    email="acc_admin@sanqidesign.com",
                    phone="13800138003"
                ),
                User(
                    username="cw01",
                    hashed_password=get_password_hash("123456"),
                    full_name="财务小王",
                    role=UserRole.ACCOUNTANT,
                    email="cw01@sanqidesign.com",
                    phone="13800138004"
                ),
            ]
            db.add_all(default_users)
            db.commit()
            print("\n" + "="*60)
            print("✅ [系统初始化] 默认用户已创建")
            print("="*60)
            print("测试账户:")
            print("  - admin / admin123 (超级管理员)")
            print("  - partner2 / 123456 (合伙人2)")
            print("  - partner3 / 123456 (合伙人3)")
            print("  - acc_admin / 123456 (财务主管)")
            print("  - cw01 / 123456 (财务人员)")
            print("="*60 + "\n")
    finally:
        db.close()

# ============================================================================
# 路由注册
# ============================================================================
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(attendance.router)
app.include_router(meetings.router)
app.include_router(records.router)
app.include_router(approval.router)
app.include_router(dashboard.router)
app.include_router(audit.router)

# ============================================================================
# 根路由
# ============================================================================
@app.get("/", summary="应用根路由", tags=["基础"])
def root():
    """
    应用根路由。
    访问 /docs 查看 Swagger API 文档。
    """
    return {
        "message": "三万设计 - 企业级财务管理系统",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", summary="健康检查", tags=["基础"])
def health_check():
    """
    系统健康检查端点。
    """
    return {
        "status": "ok",
        "service": "sanqi-finance-system",
        "version": settings.app_version
    }

# ============================================================================
# 错误处理
# ============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局错误处理器
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "status": "error"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
