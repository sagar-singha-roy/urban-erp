import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Urban ERP Core Service"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database - Read/Write Replica Splitting (CQRS / Master-Replica)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://urban_admin:urban_password123@localhost:5432/urban_erp"
    )
    WRITE_DATABASE_URL: str = os.getenv("WRITE_DATABASE_URL", "")
    READ_DATABASE_URL: str = os.getenv("READ_DATABASE_URL", "")

    @property
    def write_db_url(self) -> str:
        return self.WRITE_DATABASE_URL or self.DATABASE_URL

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
    DEFAULT_TENANT_ID: str = os.getenv("DEFAULT_TENANT_ID", "GWMC")

    class Config:
        case_sensitive = True

settings = Settings()
