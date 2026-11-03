from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base

from urban_common.settings import settings
from urban_common.tenant_context import SET_RLS_CONTEXT_SQL, rls_params

engine = create_async_engine(settings.DATABASE_URL or "postgresql+asyncpg://unset", pool_size=5, max_overflow=10, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
Base = declarative_base()


@event.listens_for(Session, "after_begin")
def _apply_rls_context(session, transaction, connection):
    """set_config(..., true) lasts only for this transaction, so pooled connections cannot leak scope."""
    connection.execute(text(SET_RLS_CONTEXT_SQL), rls_params())


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
