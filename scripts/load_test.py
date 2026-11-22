"""Simple sequential timing probe (not proof of full NFR-P01 under concurrent peak load).
Usage: python scripts/load_test.py --base http://localhost:8000 --email admin@vinabeef.test --password ... --count 200
"""
import argparse,uuid,time,statistics,json
import httpx
p=argparse.ArgumentParser();p.add_argument('--base',default='http://localhost:8000');p.add_argument('--email',default='admin@vinabeef.test');p.add_argument('--password',required=True);p.add_argument('--count',type=int,default=200);args=p.parse_args()
with httpx.Client(timeout=15) as client:
    login=client.post(args.base+'/api/auth/login',json={'email':args.email,'password':args.password});login.raise_for_status()
    h={'Authorization':'Bearer '+login.json()['access_token']}
    readers=client.get(args.base+'/api/readers',headers=h).json();cattle=client.get(args.base+'/api/cattle?limit=500',headers=h).json();gates=client.get(args.base+'/api/gates',headers=h).json()
    gate_by_id={g['id']:g for g in gates}
    specimens=[(r,c) for r in readers for c in cattle if c['barn_id']==gate_by_id[r['gate_id']]['barn_id'] and c.get('epc')]
    if not specimens:raise SystemExit('No compatible reader/cattle demo pairs')
    timings=[];outcomes={};errors=[]
    for i in range(args.count):
        r,c=specimens[i%len(specimens)]
        # alternate per specimen; tests every single new reading without event-id reuse
        direction='OUT' if (i//len(specimens))%2==0 else 'IN'
        body={'event_id':str(uuid.uuid4()),'reader_id':r['id'],'tag_epc':c['epc'],'direction':direction}
        start=time.perf_counter();res=client.post(args.base+'/api/movements/read',headers=h,json=body);elapsed=(time.perf_counter()-start)*1000
        timings.append(elapsed);outcomes[res.json().get('outcome','ERROR')]=outcomes.get(res.json().get('outcome','ERROR'),0)+1
        if res.status_code>=400:errors.append({'index':i,'http':res.status_code})
    ordered=sorted(timings)
    result={'scenario':'sequential synthetic probe (NOT representative concurrent peak)', 'events':args.count,'max_ms':round(max(timings),2),'mean_ms':round(statistics.mean(timings),2),'p95_ms':round(ordered[int(len(ordered)*.95)-1],2),'events_over_2s':sum(x>2000 for x in timings),'outcomes':outcomes,'http_errors':errors}
    print(json.dumps(result,indent=2))
