from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.auth.jwt_handler import verify_token
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    thread_id: str = ""
    rating: Literal["positive", "negative"]

    @field_validator("message_id")
    @classmethod
    def message_id_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message_id must not be empty")
        return v


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackRequest,
    token: dict = Depends(verify_token),
):
    """アシスタントの回答に対するフィードバックを記録する。"""
    try:
        service = FeedbackService.get_instance()
        service.record_feedback(
            message_id=body.message_id,
            thread_id=body.thread_id,
            rating=body.rating,
        )
        return {"success": True, "data": None}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="フィードバックの保存に失敗しました",
        ) from exc
