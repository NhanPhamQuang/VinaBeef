from datetime import datetime,timezone,timedelta
from uuid import uuid4
from app.core.security import verify_password,hash_password

def fixtures(client,auth):
    barns=client.get('/api/barns',headers=auth).json()
    readers=client.get('/api/readers',headers=auth).json()
    cattle=client.get('/api/cattle?limit=500',headers=auth).json()
    assert len(barns)==120 and len(readers)>=12 and len(cattle)==240
    return barns,readers,cattle

def post_read(client,auth,reader,epc,direction,event=None):
    return client.post('/api/movements/read',headers=auth,json={'event_id':event or str(uuid4()),'reader_id':reader['id'],'tag_epc':epc,'direction':direction})

def test_healthz_and_login(client):
    assert client.get('/healthz').json()['status']=='ok'
    assert client.post('/api/auth/login',json={'email':'admin@vinabeef.test','password':'bad'}).status_code==401
    assert client.get('/api/cattle').status_code==401
    assert verify_password('testPass123',hash_password('testPass123'))

def test_cattle_registration_duplicate_and_history(client,auth):
    barns,readers,cattle=fixtures(client,auth)
    data={'animal_code':'T-TEST-01','barn_id':barns[0]['id'],'epc':'E200-T-TEST-01','breed':'Angus','weight_kg':470}
    r=client.post('/api/cattle',headers=auth,json=data);assert r.status_code==201,r.text
    animal_id=r.json()['id']
    assert client.post('/api/cattle',headers=auth,json=data).status_code==409
    assert client.get(f'/api/cattle/{animal_id}',headers=auth).json()['tags'][0]['epc']==data['epc']
    new=client.post(f'/api/cattle/{animal_id}/tags',headers=auth,json={'epc':'E200-T-TEST-01-NEW'})
    assert new.status_code==201
    assert len(client.get(f'/api/cattle/{animal_id}',headers=auth).json()['tags'])==2
    assert len(client.get('/api/audit',headers=auth).json())>=2

def test_rfid_process_replay_and_presence(client,auth):
    barns,readers,cattle=fixtures(client,auth)
    reader=readers[0]
    gate=next(g for g in client.get('/api/gates',headers=auth).json() if g['id']==reader['gate_id'])
    animal=next(c for c in cattle if c['barn_id']==gate['barn_id'] and c['epc'])
    before=client.get('/api/dashboard',headers=auth).json()
    id=str(uuid4())
    out=post_read(client,auth,reader,animal['epc'],'OUT',id)
    assert out.status_code==200,out.text
    assert out.json()['outcome']=='ACCEPTED'
    assert post_read(client,auth,reader,animal['epc'],'OUT',id).json()['outcome']=='DUPLICATE'
    after=client.get('/api/dashboard',headers=auth).json()
    assert after['movements']==before['movements']+1
    assert after['outside']==before['outside']+1
    assert post_read(client,auth,reader,animal['epc'],'IN').json()['outcome']=='ACCEPTED'
    assert client.get('/api/dashboard',headers=auth).json()['outside']==before['outside']

def test_unknown_tag_and_wrong_barn_alerts(client,auth):
    barns,readers,cattle=fixtures(client,auth)
    r=post_read(client,auth,readers[0],'UNKNOWN-RFID-0000','OUT');assert r.status_code==200
    assert r.json()['outcome']=='UNKNOWN_TAG'
    gate=next(g for g in client.get('/api/gates',headers=auth).json() if g['id']==readers[0]['gate_id'])
    other=next(c for c in cattle if c['barn_id']!=gate['barn_id'] and c['epc'])
    assert post_read(client,auth,readers[0],other['epc'],'OUT').json()['outcome']=='ACCEPTED'
    kinds=[a['type'] for a in client.get('/api/alerts',headers=auth).json()]
    assert 'UNKNOWN_TAG' in kinds and 'WRONG_BARN' in kinds

def test_mobile_scan_health_idempotency(client,auth):
    _,_,cattle=fixtures(client,auth);animal=cattle[0]
    r=client.get(f"/api/health/scan/{animal['epc']}",headers=auth);assert r.status_code==200 and r.json()['id']==animal['id']
    payload={'cattle_id':animal['id'],'type':'VACCINATION','description':'Vaccinated on site','vaccine':'MockVax','source_id':'MOBILE-123'}
    a=client.post('/api/health',headers=auth,json=payload);assert a.status_code==201,a.text
    b=client.post('/api/health',headers=auth,json=payload);assert b.status_code==201
    assert a.json()['id']==b.json()['id']
    assert len(client.get(f"/api/cattle/{animal['id']}/history",headers=auth).json()['health'])==1

def test_transfer_workflow(client,auth):
    barns,_,cattle=fixtures(client,auth);animal=cattle[0];target=next(b for b in barns if b['id']!=animal['barn_id'])
    r=client.post('/api/transfers',headers=auth,json={'cattle_id':animal['id'],'target_barn_id':target['id'],'reason':'Relocation test'})
    assert r.status_code==201,r.text
    transfer=r.json();assert transfer['status']=='PENDING'
    assert client.patch(f"/api/transfers/{transfer['id']}/complete",headers=auth).status_code==409
    assert client.patch(f"/api/transfers/{transfer['id']}/approve",headers=auth).status_code==200
    assert client.patch(f"/api/transfers/{transfer['id']}/complete",headers=auth).json()['status']=='COMPLETED'
    assert client.get(f"/api/cattle/{animal['id']}",headers=auth).json()['barn_id']==target['id']

def test_rbac_scope_restrictions(client,supervisor,auth):
    barns,_,cattle=fixtures(client,auth)
    outside=next(c for c in cattle if c['barn_id']!=barns[0]['id'])
    assert client.get(f"/api/cattle/{outside['id']}",headers=supervisor).status_code==403
    assert client.get('/api/audit',headers=supervisor).status_code==403
    assert client.post('/api/users',headers=supervisor,json={'email':'bad@test.com','full_name':'X','password':'12345678','role':'SYSTEM_ADMIN'}).status_code==403

def test_gateway_authenticated_replay(client,auth):
    _,readers,cattle=fixtures(client,auth)
    event={'event_id':'GATEWAY-REPLAY-001','reader_id':readers[0]['id'],'tag_epc':cattle[0]['epc'],'direction':'OUT'}
    data={'gateway_id':'edge-test','events':[event]}
    assert client.post('/api/gateway/sync',json=data).status_code==401
    h={'X-Gateway-Key':'vinabeef-local-gateway-demo-key'}
    r=client.post('/api/gateway/sync',json=data,headers=h)
    assert r.status_code==200,r.text
    assert r.json()['results'][0]['outcome']=='ACCEPTED'
    again=client.post('/api/gateway/sync',json=data,headers=h)
    assert again.status_code==200
    assert again.json()['results'][0]['outcome']=='DUPLICATE'
    assert client.get('/api/dashboard',headers=auth).json()['movements']==1

def test_reports_and_mock_integration(client,auth):
    r=client.get('/api/reports/export?entity=cattle',headers=auth)
    assert r.status_code==200 and r.text.startswith('id,animal_code')
    t=client.post('/api/integrations/surveillance-export',headers=auth)
    assert t.status_code==200 and t.json()['status']=='SIMULATED'
