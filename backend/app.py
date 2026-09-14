"""
三七设计财务系统 - FastAPI 主应用程序
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from config import settings
from models import SessionLocal, User, UserRole, init_db
from security import get_password_hash
from routes import approval, audit, auth, dashboard, records, users
from routes.attendance import router as attendance_router
from routes.materials import router as materials_router
from routes.meetings import router as meetings_router
from routes.office_expenses import router as office_expenses_router
from routes.projects import router as projects_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    description="三七设计财务系统，支持考勤、会议纪要、项目收款、办公费用和物料库存管理。",
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

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _seed_default_users() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User)):
            return
        default_users = [
            User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="李总(超级管理员)",
                role=UserRole.SUPER_ADMIN,
                email="admin@sanqidesign.com",
                phone="13800138000",
            ),
            User(
                username="partner2",
                hashed_password=get_password_hash("123456"),
                full_name="张总(合伙人2)",
                role=UserRole.PARTNER,
                email="partner2@sanqidesign.com",
                phone="13800138001",
            ),
            User(
                username="partner3",
                hashed_password=get_password_hash("123456"),
                full_name="王总(合伙人3)",
                role=UserRole.PARTNER,
                email="partner3@sanqidesign.com",
                phone="13800138002",
            ),
            User(
                username="acc_admin",
                hashed_password=get_password_hash("123456"),
                full_name="财务主管",
                role=UserRole.ACCOUNTANT_ADMIN,
                email="acc_admin@sanqidesign.com",
                phone="13800138003",
            ),
            User(
                username="cw01",
                hashed_password=get_password_hash("123456"),
                full_name="财务小王",
                role=UserRole.ACCOUNTANT,
                email="cw01@sanqidesign.com",
                phone="13800138004",
            ),
            User(
                username="supervisor01",
                hashed_password=get_password_hash("123456"),
                full_name="监理赵工",
                role=UserRole.SUPERVISOR,
                email="supervisor01@sanqidesign.com",
                phone="13800138005",
            ),
            User(
                username="office01",
                hashed_password=get_password_hash("123456"),
                full_name="办公室管理员",
                role=UserRole.OFFICE_ADMIN,
                email="office01@sanqidesign.com",
                phone="13800138006",
            ),
        ]
        db.add_all(default_users)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    init_db()
    _seed_default_users()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects_router)
app.include_router(attendance_router)
app.include_router(meetings_router)
app.include_router(office_expenses_router)
app.include_router(materials_router)
app.include_router(records.router)
app.include_router(approval.router)
app.include_router(dashboard.router)
app.include_router(audit.router)


@app.get("/", tags=["基础"], summary="应用根路由")
def root():
    return {
        "message": "三七设计财务系统",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["基础"], summary="健康检查")
def health_check():
    return {
        "status": "ok",
        "service": "sanqi-finance-system",
        "version": settings.app_version,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": str(exc), "status": "error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
