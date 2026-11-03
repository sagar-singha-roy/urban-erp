"""ADM-T04 validation rules. Pure functions, so every rule can be tested without a database."""
import hashlib
import ipaddress
import re
from typing import List, Optional, Tuple

from app.core.config import settings

MAX_ASSET_BYTES = 2 * 1024 * 1024
MAX_CUSTOM_CSS_CHARS = 20000

TENANT_LEVELS = ["State", "ULB"]
RECORD_STATUSES = ["Draft", "Active", "Inactive"]
# Families index.html/styles.scss already load. Tenants cannot add external fonts.
FONT_FAMILIES = ["Noto Sans", "Noto Sans Devanagari", "Noto Sans Telugu", "Noto Sans Bengali"]
LOGO_TYPES = ["State Government Logo", "ULB Logo", "Official Emblem", "Application Logo", "Department Logo"]
ASSET_KINDS = ["logo", "emblem", "favicon", "login_banner", "header_logo", "footer_logo", "watermark"]
DOMAIN_TYPES = ["Subdomain", "Custom Domain", "Dedicated Domain"]
DNS_PROVIDERS = ["Cloudflare", "AWS Route 53", "GoDaddy", "NIC", "Other"]
DNS_RECORD_TYPES = ["CNAME", "A", "AAAA", "TXT"]
VERIFICATION_METHODS = ["DNS TXT", "DNS CNAME", "HTTP File"]
DOMAIN_STATUSES = ["Pending", "Active", "Suspended", "Inactive"]
CERTIFICATE_MANUAL = "Manual Upload"
CERTIFICATE_ACME = "Let's Encrypt"
CERTIFICATE_PROVIDERS = [CERTIFICATE_ACME, CERTIFICATE_MANUAL]
CERTIFICATE_TYPES = ["Domain Validated", "Organisation Validated", "Extended Validation", "Wildcard"]
TARGET_APPLICATIONS = ["Urban Console"]
ROUTING_HOST = "Host Based"
ROUTING_REDIRECT = "Root Redirect"
ROUTING_STRATEGIES = [ROUTING_HOST, ROUTING_REDIRECT]

_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_ROUTE = re.compile(r"^/[A-Za-z0-9/_.-]{0,254}$")
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".test", ".example", ".invalid", ".onion", ".arpa")
# Anything that can load outside content or smuggle it past this filter. CSS escapes are refused for that reason.
_CSS_BLOCKED = re.compile(r"url\s*\(|image-set|expression\s*\(|javascript:|behavior\s*:|-moz-binding|src\s*\(|<|\\", re.IGNORECASE)
_CSS_AT_RULE = re.compile(r"@([a-zA-Z-]+)")


def validate_colour(value: Optional[str]) -> Optional[str]:
    if value in (None, ""):
        return None
    if not _COLOUR.match(value):
        raise ValueError("Colours must look like #1B8C77.")
    return value.upper()


def validate_custom_css(css: Optional[str]) -> Optional[str]:
    if not css or not css.strip():
        return None
    if len(css) > MAX_CUSTOM_CSS_CHARS:
        raise ValueError(f"Custom CSS must be {MAX_CUSTOM_CSS_CHARS} characters or fewer.")
    if _CSS_BLOCKED.search(css):
        raise ValueError("Custom CSS cannot load outside content or use escapes, url(), expression() or HTML.")
    for rule in _CSS_AT_RULE.findall(css):
        if rule.lower() != "media":
            raise ValueError("Custom CSS only allows @media rules.")
    return css.strip()


def sniff_image(data: bytes) -> Optional[str]:
    """Trust the bytes, never the file name or the browser's content type. SVG is refused because it can carry scripts."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"\x00\x00\x01\x00":
        return "image/x-icon"
    return None


def validate_asset(data: bytes) -> Tuple[str, str]:
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError("Each file must be 2 MB or smaller.")
    content_type = sniff_image(data)
    if not content_type:
        raise ValueError("Only PNG, JPEG, WebP and ICO images are accepted.")
    return content_type, hashlib.sha256(data).hexdigest()


def reserved_domains() -> List[str]:
    return [d.strip().lower().rstrip(".") for d in settings.PLATFORM_RESERVED_DOMAINS.split(",") if d.strip()]


def _is_ip_address(name: str) -> bool:
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False


def normalize_domain(value: str) -> str:
    """Return the one stored form of a name, so look-alike spellings cannot become separate claims."""
    name = (value or "").strip().rstrip(".").lower()
    if not name or "://" in name or "/" in name or ":" in name or "@" in name or "*" in name:
        raise ValueError("Enter a domain name only, such as portal.example.gov.in.")
    if _is_ip_address(name):
        raise ValueError("An IP address cannot be used as a domain.")
    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("This domain name is not valid.") from exc
    labels = name.split(".")
    if len(name) > 253 or len(labels) < 2 or not all(_LABEL.match(label) for label in labels) or labels[-1].isdigit():
        raise ValueError("This domain name is not valid.")
    if name == "localhost" or name.endswith(_BLOCKED_SUFFIXES):
        raise ValueError("Local and internal names cannot be used.")
    for reserved in reserved_domains():
        if name == reserved or name.endswith("." + reserved):
            raise ValueError("This domain is reserved by the platform.")
    return name


def related_domains(name: str) -> List[str]:
    """The name and each parent. A tenant must not take a host beneath another tenant's domain."""
    labels = name.split(".")
    return [".".join(labels[i:]) for i in range(len(labels) - 1)]


def validate_route(value: Optional[str]) -> Optional[str]:
    if not value or not value.strip():
        return None
    route = value.strip()
    if not _ROUTE.match(route) or ".." in route or "//" in route:
        raise ValueError("The target route must be a path on this site, such as /login.")
    return route
