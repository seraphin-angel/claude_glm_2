from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
