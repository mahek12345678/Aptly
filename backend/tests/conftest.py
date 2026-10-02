import os
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["JOB_PROVIDER"] = "mock"
from app.core.config import settings
settings.JOB_PROVIDER = "mock"

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

try:
    from app.core.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
except Exception:
    pass

TEST_DB_FILE = Path(__file__).parent / "test_aptly.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.as_posix()}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def prepare_database(anyio_backend):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass
