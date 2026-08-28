"""API v1 router."""

from app.api.v1.endpoints import (
    access_control,
    access_logs,
    announcements,
    auth,
    authorizations,
    categories,
    documents,
    feedback,
    finance,
    lots,
    occurrences,
    packages,
    projects,
    residents,
    tasks,
    uploads,
    user_types,
    users,
    visitors,
)
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(user_types.router, prefix="/user-types", tags=["user-types"])
api_router.include_router(lots.router, prefix="/lots", tags=["lots"])
api_router.include_router(residents.router, tags=["residents"])
api_router.include_router(visitors.router, prefix="/visitors", tags=["visitors"])
api_router.include_router(authorizations.router, tags=["authorizations"])
api_router.include_router(access_logs.router, prefix="/access-logs", tags=["access-logs"])
api_router.include_router(occurrences.router, prefix="/occurrences", tags=["occurrences"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(uploads.router)
api_router.include_router(access_control.router, prefix="/access-control", tags=["access-control"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(packages.router, prefix="/packages", tags=["packages"])





