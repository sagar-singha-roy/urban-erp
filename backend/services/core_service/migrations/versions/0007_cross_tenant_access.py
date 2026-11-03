"""ADM-R02 cross-tenant access management and the department master.

Revision ID: 0007_cross_tenant_access
Revises: 0006_gis_postgis_columns
"""
from alembic import op

from app.db.models import (
    AccessChangeHistory, AccessReviewCampaign, AccessReviewItem, CrossTenantAccessGrant, CrossTenantAccessScope,
    CrossTenantGrantTarget, CrossTenantPermissionRule, TenantDepartment,
)
from app.db.session import Base

revision = "0007_cross_tenant_access"
down_revision = "0006_gis_postgis_columns"
branch_labels = None
depends_on = None

TABLES = [
    TenantDepartment.__table__, CrossTenantAccessGrant.__table__, CrossTenantGrantTarget.__table__, CrossTenantAccessScope.__table__,
    CrossTenantPermissionRule.__table__, AccessReviewCampaign.__table__, AccessReviewItem.__table__, AccessChangeHistory.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=list(reversed(TABLES)))
