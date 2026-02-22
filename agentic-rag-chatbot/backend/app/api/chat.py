import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.auth.jwt_handler import verify_token
from app.config.settings import get_settings
from app.models.chat import ChatRequest, ChatStartResponse
from app.models.hitl import ResumeRequest
from app.models.messages import StreamEventType
from app.rate_limit import limiter
from app.services.chat_service import get_chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=dict)
@limiter.limit(get_settings().rate_limit_chat)
async def start_chat(request: Request, body: ChatRequest, token: dict = Depends(verify_token)):
    """新規チャット開始 or 既存スレッドへのメッセージ送信"""
    service = get_chat_service()
    thread_id = await service.start_chat(
        message=body.message,
        thread_id=str(body.thread_id) if body.thread_id else None,
    )
    return {
        "success": True,
        "data": ChatStartResponse(thread_id=thread_id, status="streaming").model_dump(),
    }


@router.get("/stream/{thread_id}")
@limiter.limit(get_settings().rate_limit_stream)
async def stream_chat(request: Request, thread_id: UUID, token: dict = Depends(verify_token)):
    """SSE ストリーム"""
    service = get_chat_service()
    tid = str(thread_id)
    queue = service.get_or_create_queue(tid)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120.0)
                    yield f"data: {event.model_dump_json()}\n\n"

                    if event.type in (StreamEventType.DONE, StreamEventType.ERROR):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            service.cleanup(tid)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/resume/{thread_id}")
@limiter.limit(get_settings().rate_limit_chat)
async def resume_chat(
    request: Request,
    thread_id: UUID,
    body: ResumeRequest,
    token: dict = Depends(verify_token),
):
    """HITL 中断から再開"""
    service = get_chat_service()
    tid = str(thread_id)

    if tid not in service._queues:
        service.get_or_create_queue(tid)

    await service.resume_chat(
        thread_id=tid,
        response=body.response,
    )

    return {
        "success": True,
        "data": {"thread_id": tid, "status": "streaming"},
    }
