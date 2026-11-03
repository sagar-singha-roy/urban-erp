"""ADM-R04 support impersonation.

Revision ID: 0008_impersonation
Revises: 0007_cross_tenant_access
"""
from alembic import op

from app.db.models import ImpersonationAction, ImpersonationApproval, ImpersonationPolicy, ImpersonationRequest, ImpersonationSession
from app.db.session import Base

revision = "0008_impersonation"
down_revision = "0007_cross_tenant_access"
branch_labels = None
depends_on = None

TABLES = [
    ImpersonationPolicy.__table__, ImpersonationRequest.__table__, ImpersonationApproval.__table__,
    ImpersonationSession.__table__, ImpersonationAction.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=list(reversed(TABLES)))
