"""Parses and validates TLS certificates and protects their private keys."""
import base64
import datetime
import hashlib
from dataclasses import dataclass
from typing import Optional

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization

from app.core.config import settings

MAX_PEM_BYTES = 64 * 1024


def _fernet() -> Fernet:
    key = settings.CERT_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("CERT_ENCRYPTION_KEY must be set before certificates can be uploaded.")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest()))


def encrypt_private_key(pem: str) -> bytes:
    return _fernet().encrypt(pem.encode("utf-8"))


def decrypt_private_key(token: bytes) -> str:
    return _fernet().decrypt(token).decode("utf-8")


def certificate_covers(certificate: x509.Certificate, domain: str) -> bool:
    try:
        names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        return False
    for name in names:
        name = name.lower().rstrip(".")
        if name == domain:
            return True
        # A wildcard covers exactly one label.
        if name.startswith("*.") and domain.split(".", 1)[-1] == name[2:]:
            return True
    return False


@dataclass
class ParsedCertificate:
    expiry: datetime.datetime


def parse_certificate(pem: str) -> ParsedCertificate:
    try:
        certificate = x509.load_pem_x509_certificate(pem.encode("utf-8"))
    except ValueError as exc:
        raise ValueError("The certificate is not a valid PEM file.") from exc
    return ParsedCertificate(expiry=certificate.not_valid_after_utc.replace(tzinfo=None))


def validate_upload(certificate_pem: str, private_key_pem: str, chain_pem: Optional[str], domain: str) -> ParsedCertificate:
    """Errors never include file contents, so key material cannot reach a response or a log."""
    for content in (certificate_pem, private_key_pem, chain_pem or ""):
        if len(content.encode("utf-8")) > MAX_PEM_BYTES:
            raise ValueError("Certificate files must be 64 KB or smaller.")
    try:
        certificate = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
    except ValueError as exc:
        raise ValueError("The certificate is not a valid PEM file.") from None
    try:
        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    except (ValueError, TypeError):
        raise ValueError("The private key is not valid, or it is protected by a passphrase.") from None
    spki = lambda public: public.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if spki(key.public_key()) != spki(certificate.public_key()):
        raise ValueError("The private key does not match the certificate.")
    if chain_pem and chain_pem.strip():
        try:
            x509.load_pem_x509_certificates(chain_pem.encode("utf-8"))
        except ValueError:
            raise ValueError("The certificate chain is not a valid PEM file.") from None
    if not certificate_covers(certificate, domain):
        raise ValueError("This certificate does not cover the selected domain.")
    now = datetime.datetime.now(datetime.timezone.utc)
    if certificate.not_valid_after_utc <= now:
        raise ValueError("This certificate has expired.")
    if certificate.not_valid_before_utc > now:
        raise ValueError("This certificate is not valid yet.")
    return ParsedCertificate(expiry=certificate.not_valid_after_utc.replace(tzinfo=None))


def status_for_expiry(expiry: Optional[datetime.datetime], notice_days: int) -> str:
    if not expiry:
        return "Pending Issuance"
    now = datetime.datetime.utcnow()
    if expiry <= now:
        return "Expired"
    if expiry <= now + datetime.timedelta(days=notice_days):
        return "Expiring Soon"
    return "Active"
