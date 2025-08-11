from __future__ import annotations

from fastapi import APIRouter

from api.routes.v1.auth import router as auth_router
from api.routes.v1.posts import router as posts_router
from api.routes.v1.users import router as users_router

# Aggregate all domain routers under a single versioned router
router = APIRouter(prefix="/api/v1")
router.include_router(users_router)
router.include_router(posts_router)
router.include_router(auth_router)
