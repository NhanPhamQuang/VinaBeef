import csv,io,os
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response,JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from app.db.session import get_db
from app.db.models import User,Farm,Barn,Cattle,Tag,Movement,Presence,Alert,HealthRecord,Reader,Gate,Transmission,now
from app.core.security import current_user,require_roles,audit
from app.core.serializers import record,records
router=APIRouter(tags=["Dashboard, reporting and surveillance"])

def filter_farm(db,user,query,table):
    if user.role=="FARM_MANAGER" and user.farm_id:return query.where(table.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:return query.where(table.id==user.barn_id)
    return query

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user:User=Depends(current_user)):
    barn_query=select(Barn.id,Barn.code,Barn.farm_id)
    if user.role=="FARM_MANAGER" and user.farm_id:barn_query=barn_query.where(Barn.farm_id==user.farm_id)
    if user.role=="BARN_SUPERVISOR" and user.barn_id:barn_query=barn_query.where(Barn.id==user.barn_id)
    barns=db.execute(barn_query).all();ids=[b.id for b in barns]
    if not ids:return {"farms":0,"barns":0,"cattle":0,"inside":0,"outside":0,"movements":0,"open_alerts":0,"recent_movements":[],"barn_summary":[]}
    animals=db.scalar(select(func.count(Cattle.id)).where(Cattle.barn_id.in_(ids))) or 0
    inside=db.scalar(select(func.count(Presence.cattle_id)).where(Presence.barn_id.in_(ids),Presence.state=="INSIDE")) or 0
    outside=db.scalar(select(func.count(Presence.cattle_id)).where(Presence.barn_id.in_(ids),Presence.state=="OUTSIDE")) or 0
    move=db.scalar(select(func.count(Movement.id)).where(Movement.barn_id.in_(ids))) or 0
    alerts=db.scalar(select(func.count(Alert.id)).where(Alert.barn_id.in_(ids),Alert.status!="RESOLVED")) or 0
    recent=records(db.scalars(select(Movement).where(Movement.barn_id.in_(ids)).order_by(Movement.occurred_at.desc()).limit(8)).all())
    return {"farms":len(set(b.farm_id for b in barns)),"barns":len(barns),"cattle":animals,"inside":inside,"outside":outside,"movements":move,"open_alerts":alerts,"recent_movements":recent,"barn_summary":[{"id":b.id,"code":b.code,"farm_id":b.farm_id,"animals":db.scalar(select(func.count(Cattle.id)).where(Cattle.barn_id==b.id)) or 0} for b in barns[:12]]}

@router.get("/reports/summary")
def report_summary(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return dashboard(db,user)

@router.get("/reports/export")
def export(entity:str="cattle",format:str="csv",db:Session=Depends(get_db),user:User=Depends(current_user)):
    if entity not in {"cattle","movements","health","alerts"}:raise HTTPException(400,"Unsupported export kind")
    if format not in {"csv","json"}:raise HTTPException(400,"Supported export formats: csv, json")
    model={"cattle":Cattle,"movements":Movement,"health":HealthRecord,"alerts":Alert}[entity]
    query=select(model)
    if user.role in {"FARM_MANAGER","BARN_SUPERVISOR"}:
        if model==Cattle:query=query.join(Barn,Cattle.barn_id==Barn.id)
        elif model==Movement:query=query.join(Barn,Movement.barn_id==Barn.id)
        elif model==HealthRecord:query=query.join(Cattle,HealthRecord.cattle_id==Cattle.id).join(Barn,Cattle.barn_id==Barn.id)
        else:query=query.join(Barn,Alert.barn_id==Barn.id)
        if user.role=="FARM_MANAGER":query=query.where(Barn.farm_id==user.farm_id)
        else:query=query.where(Barn.id==user.barn_id)
    rows=db.scalars(query.limit(10000)).all()
    fields=[x.key for x in model.__table__.columns]
    if format=="json":
        audit(db,user,"REPORT_EXPORT","report",entity,{"rows":len(rows),"format":"json"});db.commit()
        return JSONResponse([record(row) for row in rows],headers={"Content-Disposition":f'attachment; filename="vinabeef_{entity}.json"'})
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in rows:writer.writerow(record(row))
    audit(db,user,"REPORT_EXPORT","report",entity,{"rows":len(rows)});db.commit()
    return Response(output.getvalue(),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="vinabeef_{entity}.csv"'})

@router.get("/surveillance")
def surveillance(db:Session=Depends(get_db),user:User=Depends(current_user)):
    q=select(HealthRecord).where(HealthRecord.type=="OUTBREAK").order_by(HealthRecord.event_at.desc())
    if user.role=="BARN_SUPERVISOR" and user.barn_id:q=q.join(Cattle).where(Cattle.barn_id==user.barn_id)
    elif user.role=="FARM_MANAGER" and user.farm_id:q=q.join(Cattle).join(Barn,Cattle.barn_id==Barn.id).where(Barn.farm_id==user.farm_id)
    return records(db.scalars(q.limit(200)).all())

@router.get("/integrations/transmissions")
def transmissions(db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER","EXECUTIVE"))):
    return records(db.scalars(select(Transmission).order_by(Transmission.created_at.desc()).limit(100)).all())

@router.post("/integrations/surveillance-export")
def mock_transmit(db:Session=Depends(get_db),user:User=Depends(require_roles("SYSTEM_ADMIN","FARM_MANAGER"))):
    # No authoritative API schema supplied by assignment: simulate, do not send private health data to arbitrary URLs.
    count=db.scalar(select(func.count(HealthRecord.id)).where(HealthRecord.type=="OUTBREAK")) or 0
    t=Transmission(payload_type="SURVEILLANCE",status="SIMULATED",destination="No national endpoint configured",detail=f"{count} outbreak observations considered; no external request sent")
    db.add(t);db.flush();audit(db,user,"EXTERNAL_EXPORT_SIMULATION","transmission",t.id);db.commit();return record(t)
