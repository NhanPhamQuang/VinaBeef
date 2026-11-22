"""Initial VinaBeef relational schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.db.base import Base
from app.db import models  # noqa: F401
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    # Project's initial schema is declared through SQLAlchemy metadata;
    # subsequent revisions should be generated with Alembic autogenerate.
    bind=op.get_bind()
    for table in Base.metadata.sorted_tables:table.create(bind,checkfirst=True)

def downgrade():
    bind=op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):table.drop(bind,checkfirst=True)
