import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FastAPI‑Limiter for rate limiting
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on startup
    await init_db()

    # Initialize FastAPI-Limiter with Redis when configured and reachable
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await redis_client.ping()
            await FastAPILimiter.init(redis_client)
            logger.info("FastAPI-Limiter initialized with Redis successfully.")
        except Exception as exc:
            logger.warning(
                "Redis is unavailable (%s). Running with safe development fallback (unthrottled).",
                exc,
            )
            FastAPILimiter.redis = None

    yield

    # Cleanup rate limiter connection on shutdown
    if FastAPILimiter.redis:
        try:
            await FastAPILimiter.close()
        except Exception:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type", "Cache-Control", "Pragma", "Expires"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)
if settings.API_V1_STR != "/api/v1":
    app.include_router(api_router, prefix="/api/v1")
