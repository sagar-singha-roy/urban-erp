import os
from pydantic_settings import BaseSettings


def _local_default(value: str) -> str:
    """Development credentials never apply to production."""
    return "" if os.getenv("ENVIRONMENT", "production") == "production" else value


class ServiceSettings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DATABASE_URL: str = _local_default("postgresql+asyncpg://urban_app:urban_app_password123@localhost:5432/urban_erp")
    VALKEY_URL: str = "valkey://localhost:6379/0"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    # core_service owns identity and the permission matrix, so module services ask it.
    CORE_SERVICE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:4200"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    class Config:
        case_sensitive = True


settings = ServiceSettings()
