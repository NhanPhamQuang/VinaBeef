"""RFID movement application service.

Reader evidence, accepted movements, and presence projections are separate.
Persist raw evidence and derived state in the same transaction; acknowledge only after commit.
"""
from datetime import datetime,timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.schemas import ReadIn
from app.db.models import ReadEvent,Movement,Presence,Alert,Tag,Cattle,Gate,Reader,Barn,now
from app.core.security import audit

def process_read(db:Session,data:ReadIn,actor="gateway") -> dict:
    existing=db.get(ReadEvent,data.event_id)
    if existing:
        return {"event_id":data.event_id,"outcome":"DUPLICATE","original_outcome":existing.outcome,"movement_id":get_movement_id(db,data.event_id)}
    reader=db.get(Reader,data.reader_id)
    if not reader or not reader.active:
        return {"event_id":data.event_id,"outcome":"REJECTED","reason":"Reader not registered or inactive"}
    gate=db.get(Gate,reader.gate_id)
    if not gate or not gate.active or (gate.direction_mode!="BIDIRECTIONAL" and gate.direction_mode!=data.direction):
        return {"event_id":data.event_id,"outcome":"REJECTED","reason":"Invalid gate direction or gate unavailable"}
    at=data.observed_at or now()
    if at.tzinfo is None:at=at.replace(tzinfo=timezone.utc)
    ev=ReadEvent(id=data.event_id,reader_id=reader.id,tag_epc=data.tag_epc,direction=data.direction,observed_at=at)
    db.add(ev)
    reader.last_seen_at=now()
    db.flush()
    tag=db.scalar(select(Tag).where(Tag.epc==data.tag_epc,Tag.active.is_(True)))
    if not tag:
        ev.outcome="UNKNOWN_TAG"
        db.add(Alert(event_id=ev.id,barn_id=gate.barn_id,type="UNKNOWN_TAG",message=f"Unregistered RFID: {data.tag_epc}"))
    else:
        animal=db.get(Cattle,tag.cattle_id)
        presence=db.get(Presence,animal.id) if animal else None
        if not animal or animal.status!="ACTIVE":
            ev.outcome="INACTIVE_CATTLE"
            db.add(Alert(event_id=ev.id,barn_id=gate.barn_id,cattle_id=tag.cattle_id,type="INACTIVE_CATTLE",message="An inactive animal was scanned"))
        else:
            wrong_barn=animal.barn_id!=gate.barn_id
            late=bool(presence and presence.last_event_at and at<presence.last_event_at.replace(tzinfo=presence.last_event_at.tzinfo or timezone.utc))
            same_direction=bool(presence and presence.state==("INSIDE" if data.direction=="IN" else "OUTSIDE") and presence.barn_id==gate.barn_id)
            if same_direction and not late:
                ev.outcome="DIRECTION_CONFLICT"
                db.add(Alert(event_id=ev.id,barn_id=gate.barn_id,cattle_id=animal.id,type="DIRECTION_CONFLICT",severity="MEDIUM",message="Repeated direction without an intervening opposite movement"))
            else:
                movement=Movement(event_id=ev.id,cattle_id=animal.id,gate_id=gate.id,barn_id=gate.barn_id,direction=data.direction,occurred_at=at)
                db.add(movement)
                ev.outcome="ACCEPTED_LATE" if late else "ACCEPTED"
                if not late:
                    if presence:
                        presence.barn_id=gate.barn_id;presence.state="INSIDE" if data.direction=="IN" else "OUTSIDE";presence.last_event_at=at
                    else:db.add(Presence(cattle_id=animal.id,barn_id=gate.barn_id,state="INSIDE" if data.direction=="IN" else "OUTSIDE",last_event_at=at))
                if wrong_barn and not late:
                    db.add(Alert(event_id=ev.id,barn_id=gate.barn_id,cattle_id=animal.id,type="WRONG_BARN",message=f"{animal.animal_code} observed at a non-assigned barn"))
    audit(db,actor,"RFID_READ","read_event",ev.id,{"outcome":ev.outcome})
    result={"event_id":ev.id,"outcome":ev.outcome,"movement_id":None}
    db.commit()
    result["movement_id"]=get_movement_id(db,ev.id)
    return result

def get_movement_id(db,event_id):
    x=db.scalar(select(Movement).where(Movement.event_id==event_id))
    return x.id if x else None
