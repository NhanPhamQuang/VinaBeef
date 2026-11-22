import os,hmac,hashlib,secrets
from datetime import timedelta,datetime,timezone
import jwt
from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import JWT_SECRET
from app.db.session import get_db
from app.db.models import User,AuditLog,Barn

BEARER=HTTPBearer(auto_error=False)
ROLES={"SYSTEM_ADMIN","FARM_MANAGER","BARN_SUPERVISOR","EXECUTIVE"}

def hash_password(value:str)->str:
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",value.encode(),salt,260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"

def verify_password(value:str,encoded:str)->bool:
    try:
        _,n,salt,digest=encoded.split("$")
        output=hashlib.pbkdf2_hmac("sha256",value.encode(),bytes.fromhex(salt),int(n))
        return hmac.compare_digest(output,bytes.fromhex(digest))
    except (ValueError,TypeError): return False

def create_token(user:User)->str:
    return jwt.encode({"sub":user.id,"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},JWT_SECRET,algorithm="HS256")

def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(BEARER), db:Session=Depends(get_db))->User:
    if not credentials: raise HTTPException(401,"Authentication required")
    try: identifier=jwt.decode(credentials.credentials,JWT_SECRET,algorithms=["HS256"])["sub"]
    except (jwt.InvalidTokenError,KeyError): raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,identifier)
    if not user or not user.active: raise HTTPException(401,"Inactive account")
    return user

def require_roles(*roles):
    def checker(user:User=Depends(current_user)):
        if user.role not in roles:raise HTTPException(403,"Insufficient role permission")
        return user
    return checker

def ensure_barn_scope(db:Session,user:User,barn_id:str,edit:bool=False):
    if user.role=="SYSTEM_ADMIN":return
    if user.role=="EXECUTIVE":
        if edit:raise HTTPException(403,"Executive access is read-only")
        return
    barn=db.get(Barn,barn_id)
    if not barn:raise HTTPException(404,"Barn not found")
    if user.role=="FARM_MANAGER" and user.farm_id==barn.farm_id:return
    if user.role=="BARN_SUPERVISOR" and user.barn_id==barn_id:return
    raise HTTPException(403,"Resource outside assigned scope")

def audit(db:Session,user:User|str|None,action:str,target_type:str,target_id:str,details:dict|None=None):
    actor=user.id if isinstance(user,User) else user
    db.add(AuditLog(actor_id=actor,action=action,target_type=target_type,target_id=target_id,details=details or {}))
