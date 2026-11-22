from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from app.db.base import Base
from app.db import models  # noqa
from app.core.config import database_url
config=context.config
config.set_main_option("sqlalchemy.url",database_url().replace("%","%%"))
target_metadata=Base.metadata

def migrations_offline():
    context.configure(url=database_url(),target_metadata=target_metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()

def migrations_online():
    from app.db.session import engine
    with engine.connect() as connection:
        # Prevent incompatible legacy Spring Boot farm tables from being silently reused.
        from sqlalchemy import inspect
        inspector=inspect(connection)
        if inspector.has_table("farms"):
            columns={c["name"] for c in inspector.get_columns("farms")}
            if "id" not in columns:
                raise RuntimeError("Incompatible existing farm schema detected. Use a separate database/schema for this FastAPI rewrite; do not migrate the shared Spring database in place.")
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()

if context.is_offline_mode():migrations_offline()
else:migrations_online()
