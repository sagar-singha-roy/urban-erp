"""Proves that a tenant controls a domain, with real DNS and HTTP checks."""
import ipaddress
import logging
from dataclasses import dataclass
from typing import List

import dns.asyncresolver
import dns.exception
import dns.resolver
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

VERIFY_RECORD_PREFIX = "_urban-verify"
HTTP_VERIFY_PATH = "/.well-known/urban-verify"
DNS_LOOKUP_SECONDS = 5.0
HTTP_READ_BYTES = 1024


@dataclass
class VerificationResult:
    verified: bool
    message: str
    # DNS outages and timeouts say nothing about ownership, so they never revoke a verified domain.
    conclusive: bool = True


def verification_instructions(method: str, domain: str, token: str) -> str:
    if method == "DNS TXT":
        return f"Add a TXT record at {VERIFY_RECORD_PREFIX}.{domain} with the value {token}"
    if method == "DNS CNAME":
        return f"Add a CNAME record at {domain} pointing to {settings.PLATFORM_CNAME_TARGET or 'the platform CNAME target'}"
    return f"Serve the text {token} at http://{domain}{HTTP_VERIFY_PATH}/{token}"


async def _resolve(name: str, record_type: str) -> List[str]:
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = DNS_LOOKUP_SECONDS
    answer = await resolver.resolve(name, record_type)
    return [str(item) for item in answer]


async def _check_txt(domain: str, token: str) -> VerificationResult:
    try:
        records = await _resolve(f"{VERIFY_RECORD_PREFIX}.{domain}", "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return VerificationResult(False, "The TXT record was not found.")
    except dns.exception.DNSException:
        return VerificationResult(False, "DNS could not be reached. Try again shortly.", conclusive=False)
    if any(record.strip('"') == token for record in records):
        return VerificationResult(True, "TXT record matched.")
    return VerificationResult(False, "A TXT record exists but its value does not match.")


async def _check_cname(domain: str) -> VerificationResult:
    target = settings.PLATFORM_CNAME_TARGET.strip().lower().rstrip(".")
    if not target:
        return VerificationResult(False, "PLATFORM_CNAME_TARGET is not configured on the server.", conclusive=False)
    try:
        records = await _resolve(domain, "CNAME")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return VerificationResult(False, "The CNAME record was not found.")
    except dns.exception.DNSException:
        return VerificationResult(False, "DNS could not be reached. Try again shortly.", conclusive=False)
    if any(record.lower().rstrip(".") == target for record in records):
        return VerificationResult(True, "CNAME record matched.")
    return VerificationResult(False, "The CNAME record points somewhere else.")


def _is_public_address(address: str) -> bool:
    return ipaddress.ip_address(address).is_global


async def _check_http(domain: str, token: str) -> VerificationResult:
    """Tenants choose this hostname, so it must not become a way to reach internal addresses."""
    try:
        addresses: List[str] = []
        for record_type in ("A", "AAAA"):
            try:
                addresses += await _resolve(domain, record_type)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
    except dns.exception.DNSException:
        return VerificationResult(False, "DNS could not be reached. Try again shortly.", conclusive=False)
    if not addresses:
        return VerificationResult(False, "The domain has no address records.")
    if not all(_is_public_address(address) for address in addresses):
        return VerificationResult(False, "The domain points to a private address.")
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False, trust_env=False) as client:
            response = await client.get(f"http://{domain}{HTTP_VERIFY_PATH}/{token}")
    except httpx.HTTPError:
        return VerificationResult(False, "The site could not be reached.", conclusive=False)
    if response.status_code == 200 and response.content[:HTTP_READ_BYTES].decode("utf-8", "ignore").strip() == token:
        return VerificationResult(True, "Verification file matched.")
    return VerificationResult(False, "The verification file was not found or does not match.")


async def verify_domain(domain: str, method: str, token: str) -> VerificationResult:
    if method == "DNS TXT":
        return await _check_txt(domain, token)
    if method == "DNS CNAME":
        return await _check_cname(domain)
    if method == "HTTP File":
        return await _check_http(domain, token)
    return VerificationResult(False, "Unknown verification method.")
