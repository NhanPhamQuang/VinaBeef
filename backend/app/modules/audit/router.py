from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User,AuditLog
from app.core.security import require_roles
from app.core.serializers import records
router=APIRouter(prefix="/audit",tags=["Audit ledger"])

@router.get("")
def audit_entries(limit:int=150,db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN"))):
    return records(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit,500))).all())
