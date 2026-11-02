"""ADM-T04 white-labelling and domain management.

Revision ID: 0004_white_label
Revises: 0003_event_outbox
"""
from alembic import op

from app.db.models import (
    BrandingAssetFile, BrandingAssetSet, BrandingProfile, DomainMapping, TenantCertificate, TenantDomain,
)
from app.db.session import Base

revision = "0004_white_label"
down_revision = "0003_event_outbox"
branch_labels = None
depends_on = None

TABLES = [
    BrandingProfile.__table__, BrandingAssetSet.__table__, BrandingAssetFile.__table__,
    TenantDomain.__table__, TenantCertificate.__table__, DomainMapping.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=TABLES)
