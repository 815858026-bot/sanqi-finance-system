from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MaterialInbound, MaterialOutbound, OfficeExpense, User, get_db
from security import get_current_user


router = APIRouter(prefix="/api/records", tags=["综合记录"])


@router.get("/summary")
def summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "office_expense_count": len(db.scalars(select(OfficeExpense)).all()),
        "material_inbound_count": len(db.scalars(select(MaterialInbound)).all()),
        "material_outbound_count": len(db.scalars(select(MaterialOutbound)).all()),
    }
