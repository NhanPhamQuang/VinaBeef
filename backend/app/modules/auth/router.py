from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User
from app.core.schemas import LoginIn
from app.core.security import verify_password,create_token,current_user
from app.core.serializers import record
router=APIRouter(prefix="/auth",tags=["Authentication"])

@router.post("/login")
def login(payload:LoginIn,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==payload.email.lower().strip()))
    if not user or not user.active or not verify_password(payload.password,user.password_hash):raise HTTPException(401,"Incorrect credentials")
    return {"access_token":create_token(user),"token_type":"bearer","user":record(user,["id","email","full_name","role","farm_id","barn_id"])}

@router.get("/me")
def me(user:User=Depends(current_user)):
    return record(user,["id","email","full_name","role","farm_id","barn_id"])
