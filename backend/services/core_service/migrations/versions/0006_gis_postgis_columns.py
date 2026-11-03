"""ADM-A04: parcels, wards and zones in PostGIS, and approved remote services.

The latitude, longitude and boundary_geometry columns stay, so existing readers keep working.

Revision ID: 0006_gis_postgis_columns
Revises: 0005_quota_usage
"""
from alembic import op

from app.db.models import GisApprovedService
from app.db.session import Base
from app.db.spatial import SPATIAL_STATEMENTS

revision = "0006_gis_postgis_columns"
down_revision = "0005_quota_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[GisApprovedService.__table__])
    for statement in SPATIAL_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_gis_parcel_geom ON property_parcels")
    op.execute("DROP TRIGGER IF EXISTS trg_gis_ward_geom ON wards")
    op.execute("DROP FUNCTION IF EXISTS gis_sync_parcel_geom()")
    op.execute("DROP FUNCTION IF EXISTS gis_sync_ward_geom()")
    op.execute("ALTER TABLE property_parcels DROP COLUMN IF EXISTS geom, DROP COLUMN IF EXISTS boundary_geom, DROP COLUMN IF EXISTS survey_status")
    op.execute("ALTER TABLE wards DROP COLUMN IF EXISTS geom")
    op.execute("ALTER TABLE zones DROP COLUMN IF EXISTS geom")
    Base.metadata.drop_all(bind=op.get_bind(), tables=[GisApprovedService.__table__])
