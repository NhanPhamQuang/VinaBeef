"""Optional realistic-scale synthetic fixture. Run only on a DEMO database you own.

Usage: from backend directory: python ../scripts/seed_25k.py --count 25000
"""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select,func
from app.db.session import SessionLocal
from app.db.models import Barn,Cattle,Tag,Presence

parser=argparse.ArgumentParser()
parser.add_argument('--count',type=int,default=25000)
parser.add_argument('--yes-this-is-a-demo-database',action='store_true')
args=parser.parse_args()
if not args.yes_this_is_a_demo_database:
    raise SystemExit('Refusing to modify database. Pass --yes-this-is-a-demo-database for a dedicated demo database.')
with SessionLocal() as db:
    barn_ids=list(db.scalars(select(Barn.id).order_by(Barn.code)))
    if not barn_ids:raise SystemExit('Run backend bootstrap first')
    current=db.scalar(select(func.count(Cattle.id))) or 0
    if current>=args.count:raise SystemExit(f'{current} animals already present; no change')
    print(f'Adding {args.count-current} synthetic cattle records across {len(barn_ids)} barns')
    for start in range(current,args.count,1000):
        end=min(args.count,start+1000)
        cattle=[]
        for i in range(start,end):
            c=Cattle(animal_code=f'SCALE-{i+1:07d}',barn_id=barn_ids[i%len(barn_ids)],breed='Synthetic Demo',weight_kg=350.0+(i%200))
            cattle.append(c)
        db.add_all(cattle);db.flush()
        db.add_all([Tag(cattle_id=c.id,epc=f'SCALEEPC{i+1:013d}') for i,c in zip(range(start,end),cattle)])
        db.add_all([Presence(cattle_id=c.id,barn_id=c.barn_id,state='INSIDE') for c in cattle])
        db.commit();print('Seeded',end)
