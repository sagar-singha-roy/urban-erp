import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Urban ERP Core Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Database - Read/Write Replica Splitting (CQRS / Master-Replica)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://urban_app:urban_app_password123@localhost:5432/urban_erp"
    )
    # Owner role for startup schema work and backups. Requests never use it, so RLS always applies to them.
    DB_ADMIN_URL: str = os.getenv(
        "DB_ADMIN_URL",
        "postgresql+asyncpg://urban_admin:urban_password123@localhost:5432/urban_erp"
    )
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "backups")
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
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
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
