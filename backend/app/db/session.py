from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import database_url

url=database_url()
connect_args={"check_same_thread":False,"timeout":20} if url.startswith("sqlite") else {}
engine=create_engine(url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False,expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
