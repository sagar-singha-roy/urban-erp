from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 1. Primary / Writer DB Engine (Mutations: INSERT, UPDATE, DELETE)
write_engine = create_async_engine(
    settings.write_db_url,
    echo=False,
    future=True,
    pool_size=15,
    max_overflow=25,
    pool_pre_ping=True
)

# 2. Read Replica DB Engine (Queries: SELECT, Aggregates, Geospatial layers)
read_engine = create_async_engine(
    settings.read_db_url,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Async Session Factories
AsyncWriteSessionLocal = async_sessionmaker(
    bind=write_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

AsyncReadSessionLocal = async_sessionmaker(
    bind=read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Backward-compatibility alias
engine = write_engine
AsyncSessionLocal = AsyncWriteSessionLocal
Base = declarative_base()


async def get_write_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for state-mutating requests (POST, PUT, PATCH, DELETE)."""
    async with AsyncWriteSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for read-heavy requests (GET, GIS search, analytics)."""
    async with AsyncReadSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Default dependency aliases to get_write_db for compatibility
get_db = get_write_db
