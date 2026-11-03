"""Baseline schema.

For a database that already has these tables, run `alembic stamp 0001_baseline` instead.

Revision ID: 0001_baseline
"""
from alembic import op

from app.db import models  # noqa: F401
from app.db.session import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    raise NotImplementedError("The baseline cannot be downgraded.")
