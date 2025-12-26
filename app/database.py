import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

logger = logging.getLogger(__name__)

settings = get_settings()

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
    echo=settings.debug,
)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db() -> Session:
    """Get sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db():
    """Create all database tables."""
    if not settings.db_auto_create:
        logger.info("DB_AUTO_CREATE disabled; skipping metadata.create_all()")
        return

    logger.warning(
        "Creating database tables via SQLAlchemy metadata (DB_AUTO_CREATE=true). "
        "For production, prefer Alembic migrations and set DB_AUTO_CREATE=false."
    )
    Base.metadata.create_all(bind=sync_engine)
