import hashlib
import hmac
import logging
import os
import secrets
import datetime
from typing import Dict, Any, Optional
from jose import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)


def _load_secret_key() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if secret:
        return secret
    if settings.is_development:
        logger.warning("JWT_SECRET_KEY is not set; using a random key, so sessions end when the server restarts.")
        return secrets.token_urlsafe(48)
    raise RuntimeError("JWT_SECRET_KEY must be set when ENVIRONMENT is not 'development'.")


SECRET_KEY = _load_secret_key()


def _load_audit_signing_key() -> bytes:
    key = os.getenv("AUDIT_SIGNING_KEY", "").strip()
    if key:
        return key.encode("utf-8")
    if settings.is_development:
        return b"development-only-audit-signing-key"
    raise RuntimeError("AUDIT_SIGNING_KEY must be set when ENVIRONMENT is not 'development'.")


AUDIT_SIGNING_KEY = _load_audit_signing_key()
AUDIT_SIGNATURE_PREFIX = "HMAC-SHA256:"


def sign_audit_hash(event_hash: str) -> str:
    digest = hmac.new(AUDIT_SIGNING_KEY, event_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{AUDIT_SIGNATURE_PREFIX}{digest}"


def audit_signature_is_valid(event_hash: str, signature: Optional[str]) -> bool:
    return hmac.compare_digest(sign_audit_hash(event_hash), signature or "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split(':')
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        key = bytes.fromhex(parts[1])
        new_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
