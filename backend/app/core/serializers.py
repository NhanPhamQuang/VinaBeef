from datetime import datetime

def record(obj,fields=None):
    if obj is None:return None
    if fields is None:
        fields=[c.key for c in obj.__table__.columns]
    d={k:getattr(obj,k) for k in fields}
    return {k:v.isoformat() if isinstance(v,datetime) else v for k,v in d.items()}

def records(xs,fields=None):return [record(x,fields) for x in xs]
