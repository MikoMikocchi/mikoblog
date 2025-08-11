from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter

from core.config import settings
from db.database import check_db_connection

router = APIRouter(tags=["System"])


@router.get("/health", tags=["Health"])
async def health() -> dict[str, Any]:
    ok = await check_db_connection()
    return {
        "success": ok,
        "status": "ok" if ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    return {
        "success": True,
        "message": f"Welcome to {settings.api_title}",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat(),
    }
