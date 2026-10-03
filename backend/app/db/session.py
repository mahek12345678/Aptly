"""Async database engine, session factory, and dependency injection."""
from collections.abc import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _create_engine():
    db_url = settings.async_database_url
    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            echo=(settings.ENVIRONMENT == "development"),
            future=True,
        )

    connect_args: dict[str, Any] = {}
    if db_url.startswith("postgresql+asyncpg://"):
        # Neon pooler and remote PostgreSQL require SSL
        is_local = "localhost" in db_url or "127.0.0.1" in db_url
        if not is_local or settings.ENVIRONMENT == "production":
            connect_args["ssl"] = "require"

    return create_async_engine(
        db_url,
        connect_args=connect_args,
        echo=(settings.ENVIRONMENT == "development"),
        future=True,
        pool_pre_ping=True,
    )


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def _sync_sqlite_columns(sync_conn):
    if sync_conn.dialect.name != "sqlite":
        return
    try:
        from sqlalchemy import text
        res = sync_conn.execute(text("PRAGMA table_info(job_listings)"))
        cols = [r[1] for r in res.fetchall()]
        if cols:
            if "is_active" not in cols:
                sync_conn.execute(text("ALTER TABLE job_listings ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            if "last_seen_at" not in cols:
                sync_conn.execute(text("ALTER TABLE job_listings ADD COLUMN last_seen_at DATETIME"))
            if "fetched_at" not in cols:
                sync_conn.execute(text("ALTER TABLE job_listings ADD COLUMN fetched_at DATETIME"))
        res_resumes = sync_conn.execute(text("PRAGMA table_info(resumes)"))
        resume_cols = [r[1] for r in res_resumes.fetchall()]
        if resume_cols and "file_size_bytes" not in resume_cols:
            sync_conn.execute(text("ALTER TABLE resumes ADD COLUMN file_size_bytes INTEGER"))
    except Exception:
        pass


async def init_db() -> None:
    """Initialize database tables, with automatic SQLite fallback only for development."""
    from app.db.base import Base
    import app.models  # noqa: F401
    global engine, AsyncSessionLocal

    is_production = (settings.ENVIRONMENT == "production")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if conn.dialect.name == "sqlite":
                await conn.run_sync(_sync_sqlite_columns)

        if "postgresql" in engine.dialect.name or "asyncpg" in str(engine.url):
            logger.info("Connected to PostgreSQL database")
        else:
            logger.info("Connected to database (%s)", engine.dialect.name)

    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        if is_production:
            logger.error("PostgreSQL connection failed: %s", err_msg)
            raise
        else:
            logger.warning(
                "Database connection failed (%s). Falling back to local SQLite database (aptly.db) for development.",
                err_msg,
            )
            engine = create_async_engine("sqlite+aiosqlite:///./aptly.db", future=True)
            AsyncSessionLocal.configure(bind=engine)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(_sync_sqlite_columns)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
