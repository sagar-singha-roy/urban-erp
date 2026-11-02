"""Kafka event outbox and consumer inbox.

Revision ID: 0003_event_outbox
Revises: 0002_gis_viewer
"""
from alembic import op

from app.db.models import EventInbox, EventOutbox
from app.db.session import Base

revision = "0003_event_outbox"
down_revision = "0002_gis_viewer"
branch_labels = None
depends_on = None

TABLES = [EventOutbox.__table__, EventInbox.__table__]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=TABLES)
