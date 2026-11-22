from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)

class Farm(Base):
    __tablename__="farms"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(140),unique=True,index=True)
    location:Mapped[str]=mapped_column(String(140),default="")
    active:Mapped[bool]=mapped_column(Boolean,default=True)

class Barn(Base):
    __tablename__="barns"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    farm_id:Mapped[str]=mapped_column(ForeignKey("farms.id"),index=True)
    code:Mapped[str]=mapped_column(String(64))
    capacity:Mapped[int]=mapped_column(Integer,default=500)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    __table_args__=(UniqueConstraint("farm_id","code"),)

class Gate(Base):
    __tablename__="gates"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"),index=True)
    name:Mapped[str]=mapped_column(String(100))
    direction_mode:Mapped[str]=mapped_column(String(20),default="BIDIRECTIONAL")
    active:Mapped[bool]=mapped_column(Boolean,default=True)

class Reader(Base):
    __tablename__="readers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    gate_id:Mapped[str]=mapped_column(ForeignKey("gates.id"),index=True)
    code:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    model:Mapped[str]=mapped_column(String(100),default="RFID Simulator")
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    last_seen_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class Cattle(Base):
    __tablename__="cattle"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    animal_code:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"),index=True)
    breed:Mapped[str]=mapped_column(String(100),default="Unknown")
    weight_kg:Mapped[float|None]=mapped_column(Float,nullable=True)
    status:Mapped[str]=mapped_column(String(40),default="ACTIVE")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Tag(Base):
    __tablename__="tags"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    cattle_id:Mapped[str]=mapped_column(ForeignKey("cattle.id"),index=True)
    epc:Mapped[str]=mapped_column(String(100),unique=True,index=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    assigned_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class User(Base):
    __tablename__="users"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    email:Mapped[str]=mapped_column(String(180),unique=True,index=True)
    full_name:Mapped[str]=mapped_column(String(120),default="")
    password_hash:Mapped[str]=mapped_column(String(300))
    role:Mapped[str]=mapped_column(String(35),default="BARN_SUPERVISOR")
    farm_id:Mapped[str|None]=mapped_column(ForeignKey("farms.id"),nullable=True)
    barn_id:Mapped[str|None]=mapped_column(ForeignKey("barns.id"),nullable=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)

class ReadEvent(Base):
    __tablename__="rfid_read_events"
    id:Mapped[str]=mapped_column(String(100),primary_key=True)
    reader_id:Mapped[str]=mapped_column(ForeignKey("readers.id"),index=True)
    tag_epc:Mapped[str]=mapped_column(String(100),index=True)
    direction:Mapped[str]=mapped_column(String(4))
    observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    received_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    outcome:Mapped[str]=mapped_column(String(40),default="PENDING")
    detail:Mapped[str]=mapped_column(Text,default="")

class Movement(Base):
    __tablename__="movements"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey("rfid_read_events.id"),unique=True,index=True)
    cattle_id:Mapped[str]=mapped_column(ForeignKey("cattle.id"),index=True)
    gate_id:Mapped[str]=mapped_column(ForeignKey("gates.id"),index=True)
    barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"),index=True)
    direction:Mapped[str]=mapped_column(String(4))
    occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Presence(Base):
    __tablename__="presence"
    cattle_id:Mapped[str]=mapped_column(ForeignKey("cattle.id"),primary_key=True)
    barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"),index=True)
    state:Mapped[str]=mapped_column(String(20),default="INSIDE")
    last_event_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class Alert(Base):
    __tablename__="alerts"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    cattle_id:Mapped[str|None]=mapped_column(ForeignKey("cattle.id"),nullable=True)
    barn_id:Mapped[str|None]=mapped_column(ForeignKey("barns.id"),nullable=True)
    event_id:Mapped[str|None]=mapped_column(String(100),nullable=True)
    type:Mapped[str]=mapped_column(String(40),index=True)
    severity:Mapped[str]=mapped_column(String(12),default="HIGH")
    message:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(20),default="OPEN")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    resolved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class Transfer(Base):
    __tablename__="transfers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    cattle_id:Mapped[str]=mapped_column(ForeignKey("cattle.id"),index=True)
    source_barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"))
    target_barn_id:Mapped[str]=mapped_column(ForeignKey("barns.id"))
    status:Mapped[str]=mapped_column(String(24),default="PENDING")
    reason:Mapped[str]=mapped_column(Text,default="")
    requested_by:Mapped[str]=mapped_column(ForeignKey("users.id"))
    approved_by:Mapped[str|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class HealthRecord(Base):
    __tablename__="health_records"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    cattle_id:Mapped[str]=mapped_column(ForeignKey("cattle.id"),index=True)
    type:Mapped[str]=mapped_column(String(22))
    description:Mapped[str]=mapped_column(Text)
    vaccine:Mapped[str|None]=mapped_column(String(100),nullable=True)
    status:Mapped[str|None]=mapped_column(String(50),nullable=True)
    event_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    author_id:Mapped[str]=mapped_column(ForeignKey("users.id"))
    source_id:Mapped[str|None]=mapped_column(String(100),unique=True,nullable=True)

class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    actor_id:Mapped[str|None]=mapped_column(String(100),nullable=True)
    action:Mapped[str]=mapped_column(String(100),index=True)
    target_type:Mapped[str]=mapped_column(String(60))
    target_id:Mapped[str]=mapped_column(String(100))
    details:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Transmission(Base):
    __tablename__="external_transmissions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    payload_type:Mapped[str]=mapped_column(String(50))
    status:Mapped[str]=mapped_column(String(24),default="SIMULATED")
    destination:Mapped[str]=mapped_column(String(300),default="Unconfigured mock")
    detail:Mapped[str]=mapped_column(Text,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class GatewaySync(Base):
    __tablename__="gateway_syncs"
    gateway_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    last_sync_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    accepted_count:Mapped[int]=mapped_column(Integer,default=0)

class MissingPolicy(Base):
    __tablename__="missing_policies"
    farm_id:Mapped[str]=mapped_column(ForeignKey("farms.id"),primary_key=True)
    grace_minutes:Mapped[int]=mapped_column(Integer,default=60)
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
