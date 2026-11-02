"""Builds the gateway's host configuration from active mappings.

Only writes a candidate folder. gateway/apply_generated.sh tests it with nginx -t and keeps
the last working configuration when the test fails, so a bad render cannot take down the gateway.
"""
import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings

_HOST = re.compile(r"^[a-z0-9.-]{1,253}$")
_ROUTE = re.compile(r"^/[A-Za-z0-9/_.-]{0,254}$")
CERT_DIR = "generated/live/certs"


@dataclass
class Site:
    host: str
    certificate_id: Optional[str] = None
    fullchain: Optional[str] = None
    private_key: Optional[str] = None
    force_https: bool = True
    root_redirect: Optional[str] = None


def _acme_location() -> str:
    return f"    location /.well-known/acme-challenge/ {{\n        root {settings.ACME_WEBROOT};\n    }}\n"


def _redirect(site: Site) -> str:
    return f"    location = / {{\n        return 302 {site.root_redirect};\n    }}\n" if site.root_redirect else ""


def render_site(site: Site) -> str:
    # Values come from validated columns; this second check stops anything else reaching the config.
    if not _HOST.match(site.host) or (site.root_redirect and not _ROUTE.match(site.root_redirect)):
        raise ValueError(f"Refusing to render an unsafe gateway value for {site.host!r}")
    has_tls = bool(site.fullchain and site.private_key)
    http_body = _acme_location()
    if has_tls and site.force_https:
        http_body += "    location / {\n        return 301 https://$host$request_uri;\n    }\n"
    elif has_tls or not site.force_https:
        http_body += _redirect(site) + "    include server_common.conf;\n"
    else:
        # Waiting for a certificate: answer the ACME challenge and nothing else.
        http_body += "    location / {\n        return 404;\n    }\n"
    output = f"server {{\n    listen 8088;\n    server_name {site.host};\n{http_body}}}\n"
    if has_tls:
        output += (
            f"server {{\n    listen 8443 ssl;\n    http2 on;\n    server_name {site.host};\n"
            f"    ssl_certificate {CERT_DIR}/{site.certificate_id}.crt;\n"
            f"    ssl_certificate_key {CERT_DIR}/{site.certificate_id}.key;\n"
            "    ssl_protocols TLSv1.2 TLSv1.3;\n"
            "    add_header Strict-Transport-Security \"max-age=31536000\" always;\n"
            f"{_redirect(site)}    include server_common.conf;\n}}\n"
        )
    return output


def render_files(sites: List[Site], acme_domains: List[str]) -> Dict[str, str]:
    files = {
        "sites.conf": "".join(render_site(site) for site in sorted(sites, key=lambda s: s.host)),
        "acme-domains.txt": "".join(f"{domain}\n" for domain in sorted(acme_domains)),
    }
    for site in sites:
        if site.fullchain and site.private_key:
            files[f"certs/{site.certificate_id}.crt"] = site.fullchain
            files[f"certs/{site.certificate_id}.key"] = site.private_key
    return files


def version_of(files: Dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode())
        digest.update(files[name].encode())
    return digest.hexdigest()


def generated_dir() -> Path:
    return Path(settings.GATEWAY_GENERATED_DIR)


def write_candidate(files: Dict[str, str], root: Optional[Path] = None) -> bool:
    """Returns True when there was something new for the gateway to apply."""
    root = root or generated_dir()
    version = version_of(files)
    for marker in (root / "live" / "version", root / "candidate" / "version", root / "rejected_version"):
        if marker.exists() and marker.read_text().strip() == version:
            return False
    temporary = root / "candidate.tmp"
    shutil.rmtree(temporary, ignore_errors=True)
    (temporary / "certs").mkdir(parents=True)
    for name, content in files.items():
        path = temporary / name
        # Created private from the start, not tightened afterwards.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600 if name.endswith(".key") else 0o644)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
    (temporary / "version").write_text(version)
    shutil.rmtree(root / "candidate", ignore_errors=True)
    temporary.rename(root / "candidate")
    return True


def routing_status(root: Optional[Path] = None) -> Dict[str, Optional[str]]:
    root = root or generated_dir()
    read = lambda path: path.read_text().strip() if path.exists() else None
    return {
        "appliedVersion": read(root / "live" / "version"),
        "pendingVersion": read(root / "candidate" / "version"),
        "lastError": read(root / "last_error"),
    }
