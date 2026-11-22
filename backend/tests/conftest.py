import os,tempfile
from pathlib import Path
os.environ['APP_ENV']='development'
os.environ['DEMO_MODE']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.gettempdir())/'vinabeef_backend_pytest.db')
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db.base import Base
from app.db.session import engine

@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:yield c

@pytest.fixture()
def auth(client):
    r=client.post('/api/auth/login',json={'email':'admin@vinabeef.test','password':'Demo@123456'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}

@pytest.fixture()
def supervisor(client):
    r=client.post('/api/auth/login',json={'email':'supervisor@vinabeef.test','password':'Demo@123456'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}
