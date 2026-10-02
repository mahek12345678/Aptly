from fastapi import APIRouter
from app.api.v1.endpoints import (
    applications,
    assistant,
    auth,
    dashboard,
    health,
    jd_analyzer,
    jobs,
    onboarding,
    resumes,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(resumes.router)
api_router.include_router(dashboard.router)
api_router.include_router(applications.router)
api_router.include_router(jd_analyzer.router)
api_router.include_router(jobs.router)
api_router.include_router(assistant.router)


