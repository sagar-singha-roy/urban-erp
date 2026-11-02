"""ADM-S04 option lists and pure rules."""
import datetime
from typing import List, Optional, Tuple

STORAGE_TYPES = ["Document Storage", "Image Storage", "GIS Data Storage", "Backup Storage", "Archive Storage"]
PROVIDER_PLATFORM = "Platform Database"
STORAGE_PROVIDERS = [PROVIDER_PLATFORM, "AWS S3", "Google Cloud Storage", "Azure Blob Storage", "Self-hosted Object Storage"]
# Providers whose real usage this platform can measure. Others report no figures rather than a false zero.
MEASURED_PROVIDERS = [PROVIDER_PLATFORM]
STORAGE_UNITS = {"MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
FILE_TYPES = ["pdf", "png", "jpg", "webp", "ico", "docx", "xlsx", "csv", "geojson", "shp", "zip"]
RECORD_STATUSES = ["Draft", "Active", "Inactive"]
TENANT_LEVELS = ["State", "ULB"]
SMS_PROVIDERS = ["MSG91", "Gupshup", "NIC SMS Gateway", "Other"]
SMS_CATEGORIES = ["Transactional", "Service Implicit", "Service Explicit", "Promotional", "OTP"]
API_GATEWAYS = ["NGINX Gateway"]
API_CATEGORIES = ["Citizen", "Staff", "Integration"]
PERIOD_MINUTE, PERIOD_HOUR, PERIOD_DAY = "Per Minute", "Per Hour", "Per Day"
QUOTA_PERIODS = [PERIOD_MINUTE, PERIOD_HOUR, PERIOD_DAY]
RESOURCE_STORAGE, RESOURCE_SMS, RESOURCE_API, RESOURCE_CONCURRENT = "Storage", "SMS Credits", "API Requests", "Concurrent Connections"
RESOURCE_TYPES = [RESOURCE_STORAGE, RESOURCE_SMS, RESOURCE_API, RESOURCE_CONCURRENT]
CONDITION_PERCENT, CONDITION_VALUE = "Usage Percentage", "Usage Value"
ALERT_CONDITIONS = [CONDITION_PERCENT, CONDITION_VALUE]
OPERATORS = [">=", ">", "<=", "<", "="]
SEVERITIES = ["Warning", "High", "Critical"]
CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS = "In-App", "Email", "SMS"
# Seeded once, then edited in the app. Nothing reads these numbers afterwards.
DEFAULT_LEVELS = [("Warning", 70.0), ("High", 85.0), ("Critical", 95.0)]


def to_bytes(amount: float, unit: str) -> int:
    return int(amount * STORAGE_UNITS[unit])


def is_effective(start: Optional[datetime.datetime], end: Optional[datetime.datetime], now: datetime.datetime) -> bool:
    return (start is None or start <= now) and (end is None or end >= now)


def percentage(used: float, total: float) -> float:
    return round(used / total * 100, 2) if total else 0.0


def compare(value: float, operator: str, threshold: float) -> bool:
    return {">=": value >= threshold, ">": value > threshold, "<=": value <= threshold, "<": value < threshold, "=": value == threshold}[operator]


def usage_status(percent: Optional[float], levels: List[Tuple[str, float]]) -> str:
    """The highest configured level reached, or Normal."""
    if percent is None:
        return "Not Connected"
    reached = "Normal"
    for name, threshold in sorted(levels, key=lambda level: level[1]):
        if percent >= threshold:
            reached = name
    return reached
