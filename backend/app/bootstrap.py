"""Idempotent local demo seed. NEVER creates demo users when APP_ENV=production."""
import os
from sqlalchemy import select,func
from app.core.config import APP_ENV,DEMO_MODE,validate_environment
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.db.models import Farm,Barn,Gate,Reader,User,Cattle,Tag,Presence
from app.db.base import Base

LOCATIONS=[("Dak Lak","Buon Ma Thuot, Dak Lak"),("Gia Lai","Pleiku, Gia Lai"),("Dong Nai","Long Thanh, Dong Nai")]

def seed_demo(db):
    if not DEMO_MODE:return
    if db.scalar(select(func.count(Farm.id))):return
    farms=[];barns=[];readers=[]
    for idx,(name,location) in enumerate(LOCATIONS):
        f=Farm(name=name,location=location);db.add(f);db.flush();farms.append(f)
        for j in range(40):
            b=Barn(farm_id=f.id,code=f"{['DL','GL','DN'][idx]}-{j+1:03d}",capacity=500)
            db.add(b);db.flush();barns.append(b)
            if j<4:
                g=Gate(barn_id=b.id,name=f"Gate {j+1}",direction_mode="BIDIRECTIONAL")
                db.add(g);db.flush()
                r=Reader(gate_id=g.id,code=f"RD-{['DL','GL','DN'][idx]}-{j+1:03d}")
                db.add(r);readers.append(r)
    accounts=[("admin@vinabeef.test","System Administrator","SYSTEM_ADMIN",None,None),
              ("manager@vinabeef.test","Farm Manager","FARM_MANAGER",farms[0].id,None),
              ("supervisor@vinabeef.test","Barn Supervisor","BARN_SUPERVISOR",farms[0].id,barns[0].id),
              ("executive@vinabeef.test","Executive Management","EXECUTIVE",None,None)]
    for email,name,role,farm_id,barn_id in accounts:
        db.add(User(email=email,full_name=name,role=role,password_hash=hash_password("Demo@123456"),farm_id=farm_id,barn_id=barn_id))
    for idx in range(240):
        barn=barns[idx%len(barns)]
        c=Cattle(animal_code=f"COW-{idx+1:05d}",barn_id=barn.id,breed=["Brahman Cross","Angus Cross","Bonsmara"][idx%3],weight_kg=380+(idx*7)%190)
        db.add(c);db.flush()
        db.add(Tag(cattle_id=c.id,epc=f"E200341201{idx+1:010d}"))
        db.add(Presence(cattle_id=c.id,barn_id=barn.id,state="INSIDE"))
    db.commit()


def bootstrap():
    validate_environment()
    # Alembic runs from startup entrypoint in production; bootstrap is also safe for direct uvicorn demo.
    from app.db.models import Farm
    from app.db.session import engine
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if DEMO_MODE:seed_demo(db)
        elif APP_ENV=="production":
            admin_email=os.getenv("ADMIN_EMAIL","")
            admin_pass=os.getenv("ADMIN_PASSWORD","")
            if not admin_email or len(admin_pass)<12:raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD (12+ characters) required in production")
            if not db.scalar(select(User).where(User.email==admin_email.lower())):
                db.add(User(email=admin_email.lower(),full_name="Administrator",role="SYSTEM_ADMIN",password_hash=hash_password(admin_pass)))
                db.commit()

if __name__=="__main__":bootstrap()
