import os
from pydantic_settings import BaseSettings

PLATFORM_ULB_TYPE = "Platform"


def _local_default(value: str) -> str:
    """Development credentials never apply to production."""
    return "" if os.getenv("ENVIRONMENT", "production") == "production" else value


class Settings(BaseSettings):
    PROJECT_NAME: str = "Urban ERP Core Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Database - Read/Write Replica Splitting (CQRS / Master-Replica)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        _local_default("postgresql+asyncpg://urban_app:urban_app_password123@localhost:5432/urban_erp")
    )
    # Owner role for startup schema work and backups. Requests never use it, so RLS always applies to them.
    DB_ADMIN_URL: str = os.getenv(
        "DB_ADMIN_URL",
        _local_default("postgresql+asyncpg://urban_admin:urban_password123@localhost:5432/urban_erp")
    )
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "backups")
    GIS_CUSTOM_BASEMAP_URL: str = os.getenv("GIS_CUSTOM_BASEMAP_URL", "")
    BACKUP_ENCRYPTION_KEY: str = os.getenv("BACKUP_ENCRYPTION_KEY", "")
    # ADM-T04: encrypts uploaded certificate private keys. Uploads are refused without it.
    CERT_ENCRYPTION_KEY: str = os.getenv("CERT_ENCRYPTION_KEY", "")
    # Comma-separated domains tenants may never claim, such as the platform's own.
    PLATFORM_RESERVED_DOMAINS: str = os.getenv("PLATFORM_RESERVED_DOMAINS", "")
    # Hostname that tenants point CNAME records at.
    PLATFORM_CNAME_TARGET: str = os.getenv("PLATFORM_CNAME_TARGET", "")
    GATEWAY_GENERATED_DIR: str = os.getenv("GATEWAY_GENERATED_DIR", "../../../gateway/generated")
    LETSENCRYPT_DIR: str = os.getenv("LETSENCRYPT_DIR", "/etc/letsencrypt")
    ACME_WEBROOT: str = os.getenv("ACME_WEBROOT", "/var/www/acme")
    # ADM-S04: signs SMS delivery reports. Reports are refused until it is set.
    SMS_WEBHOOK_SECRET: str = os.getenv("SMS_WEBHOOK_SECRET", "")
    # Alert email. The Email channel cannot be selected until a host is set.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    WRITE_DATABASE_URL: str = os.getenv("WRITE_DATABASE_URL", "")
    READ_DATABASE_URL: str = os.getenv("READ_DATABASE_URL", "")

    @property
    def write_db_url(self) -> str:
        return self.WRITE_DATABASE_URL or self.DATABASE_URL

    @property
    def admin_db_url(self) -> str:
        return self.DB_ADMIN_URL

    @property
    def read_db_url(self) -> str:
        return self.READ_DATABASE_URL or self.DATABASE_URL
    
    # Valkey
    VALKEY_URL: str = os.getenv("VALKEY_URL", "valkey://localhost:6379/0")
    
    # Keycloak
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "urban")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "urban-web")
    
    # Tenant
    DEFAULT_TENANT_ID: str = os.getenv("DEFAULT_TENANT_ID", "GWMC" if os.getenv("ENVIRONMENT") == "development" else "")

    # Comma-separated browser origins allowed to call this API
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:4200")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    class Config:
        case_sensitive = True

settings = Settings()

if settings.ENVIRONMENT == "production" and not (settings.DATABASE_URL and settings.DB_ADMIN_URL):
    raise RuntimeError("DATABASE_URL and DB_ADMIN_URL must be set in production.")
