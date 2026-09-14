"""三七设计财务系统 - FastAPI 主应用程序。"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from config import settings
from models import SessionLocal, User, UserRole, init_db
from routes import approval, audit, auth, dashboard, projects, records, users
from security import get_password_hash

app = FastAPI(
    title=settings.app_name,
    description="三七设计企业财务与人力资源管理系统，覆盖考勤、请假、项目收款、库存、工资、支出审批和审计日志。工资计算按当前需求不计算社保和个人所得税。",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("./static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="./static"), name="static")


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    db = SessionLocal()
    try:
        if not db.scalar(select(User)):
            default_users = [
                User(username="admin", hashed_password=get_password_hash("admin123"), full_name="合伙人1（超级管理员）", role=UserRole.SUPER_ADMIN, email="admin@sanqidesign.com", phone="13800138000"),
                User(username="partner001", hashed_password=get_password_hash("123456"), full_name="合伙人2", role=UserRole.PARTNER, email="partner001@sanqidesign.com", phone="13800138001"),
                User(username="partner002", hashed_password=get_password_hash("123456"), full_name="合伙人3", role=UserRole.PARTNER, email="partner002@sanqidesign.com", phone="13800138002"),
                User(username="finance001", hashed_password=get_password_hash("123456"), full_name="财务主管", role=UserRole.ACCOUNTANT_ADMIN, email="finance001@sanqidesign.com", phone="13800138003"),
                User(username="finance002", hashed_password=get_password_hash("123456"), full_name="财务专员", role=UserRole.ACCOUNTANT, email="finance002@sanqidesign.com", phone="13800138004"),
                User(username="cashier001", hashed_password=get_password_hash("123456"), full_name="出纳", role=UserRole.CASHIER, email="cashier001@sanqidesign.com", phone="13800138005"),
            ]
            db.add_all(default_users)
            db.commit()
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(records.router)
app.include_router(approval.router)
app.include_router(dashboard.router)
app.include_router(audit.router)


@app.get("/", summary="应用根路由", tags=["基础"])
def root():
    return {"message": settings.app_name, "version": settings.app_version, "docs": "/docs", "redoc": "/redoc"}


@app.get("/health", summary="健康检查", tags=["基础"])
def health_check():
    return {"status": "ok", "service": "sanqi-finance-system", "version": settings.app_version}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": str(exc), "status": "error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
