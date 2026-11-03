"""ADM-A04 GIS tables.

Row-level security for these tables is applied at service startup, with the other tenant tables.

Revision ID: 0002_gis_viewer
Revises: 0001_baseline
"""
from alembic import op

from app.db.models import GisFeatureModel, GisLayerModel, GisWorkspaceModel
from app.db.session import Base

revision = "0002_gis_viewer"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

TABLES = [GisLayerModel.__table__, GisFeatureModel.__table__, GisWorkspaceModel.__table__]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=list(reversed(TABLES)))
