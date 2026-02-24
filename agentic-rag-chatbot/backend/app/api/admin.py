from fastapi import APIRouter, Depends

from app.auth.jwt_handler import verify_token
from app.services.gap_service import KnowledgeGapService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/knowledge-gaps")
async def get_knowledge_gaps(
    limit: int = 50,
    token: dict = Depends(verify_token),
):
    service = KnowledgeGapService.get_instance()
    return {
        "success": True,
        "data": {
            "gaps": service.get_gaps(limit=limit),
            "summary": service.get_summary(),
        },
    }
