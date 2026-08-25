"""API v1 router."""

from app.api.v1.endpoints import (
    auth,
    categories,
    lots,
    residents,
    tasks,
    user_types,
    users,
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


