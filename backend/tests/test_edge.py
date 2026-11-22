"""Gateway tests using its real SQLite queue; no network needed."""
import importlib.util,os,tempfile
from pathlib import Path

def load_edge(tmp_path):
    path=Path(__file__).resolve().parents[2]/'edge_gateway'/'main.py'
    spec=importlib.util.spec_from_file_location('edge_test_module',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DATA_FILE=str(tmp_path/'edge.sqlite')
    return module

def test_local_store_and_replay(monkeypatch,tmp_path):
    edge=load_edge(tmp_path)
    payload=edge.EventIn(event_id='LOCAL-001',reader_id='RD-DEMO',tag_epc='E200-TEST',direction='OUT')
    assert edge.accept(payload)['outcome']=='STORED_LOCALLY'
    assert edge.accept(payload)['outcome']=='ALREADY_STORED'
    assert edge.status()['pending']==1
    class FakeResponse:
        def raise_for_status(self):pass
        def json(self):return {'results':[{'event_id':'LOCAL-001','outcome':'ACCEPTED'}]}
    class FakeClient:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,*args,**kwargs):return FakeResponse()
    monkeypatch.setattr(edge.httpx,'Client',FakeClient)
    assert edge.sync_once()['sent']==1
    assert edge.status()['pending']==0
    assert edge.status()['synced']==1

def test_stays_pending_during_wan_failure(monkeypatch,tmp_path):
    edge=load_edge(tmp_path)
    edge.accept(edge.EventIn(event_id='LOCAL-002',reader_id='RD-DEMO',tag_epc='E200-TEST',direction='IN'))
    class BrokenClient:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,*args,**kwargs):raise edge.httpx.ConnectError('WAN disconnected')
    monkeypatch.setattr(edge.httpx,'Client',BrokenClient)
    assert edge.sync_once()['central_status']=='OFFLINE_OR_ERROR'
    assert edge.status()['pending']==1
