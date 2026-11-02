"""ADM-S04 quota and usage management.

Revision ID: 0005_quota_usage
Revises: 0004_white_label
"""
from alembic import op

from app.db.models import (
    ApiQuotaPolicy, ApiUsageMinute, SmsCreditAllocation, SmsMessage, StorageAllocation, StorageObject,
    UsageAlertEvent, UsageAlertRule, UsageThresholdLevel,
)
from app.db.session import Base

revision = "0005_quota_usage"
down_revision = "0004_white_label"
branch_labels = None
depends_on = None

TABLES = [
    StorageAllocation.__table__, StorageObject.__table__, SmsCreditAllocation.__table__, SmsMessage.__table__,
    ApiQuotaPolicy.__table__, ApiUsageMinute.__table__, UsageThresholdLevel.__table__,
    UsageAlertRule.__table__, UsageAlertEvent.__table__,
]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=TABLES)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=TABLES)
