from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.services.escalation_service import EscalationService
from app.services.gap_service import KnowledgeGapService
from app.services.cost_service import CostService
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/api/admin", tags=["admin"])


class PromptUpdateRequest(BaseModel):
    """プロンプト更新リクエスト"""
    content: str


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


@router.get("/escalations")
async def get_escalations(
    limit: int = 50,
    token: dict = Depends(verify_token),
):
    """エスカレーション一覧を取得する"""
    service = EscalationService.get_instance()
    tickets = service.get_tickets(limit=limit)
    return {
        "success": True,
        "data": {
            "tickets": tickets,
            "total": len(tickets),
        },
    }


@router.get("/escalations/{ticket_id}")
async def get_escalation(
    ticket_id: str,
    token: dict = Depends(verify_token),
):
    """個別のエスカレーションチケットを取得する"""
    service = EscalationService.get_instance()
    ticket = service.get_ticket(ticket_id)

    if ticket is None:
        return {
            "success": False,
            "error": f"Ticket {ticket_id} not found",
        }

    return {
        "success": True,
        "data": ticket,
    }


@router.get("/costs")
async def get_costs(
    session_id: str | None = Query(None, description="Filter by session ID"),
    since: str | None = Query(None, description="Filter by ISO datetime"),
    token: dict = Depends(verify_token),
):
    """LLMコスト情報を取得する

    Args:
        session_id: セッションIDでフィルタリング（オプション）
        since: ISO形式の日時でフィルタリング（オプション）

    Returns:
        コスト情報のサマリー
    """
    from dataclasses import asdict

    service = CostService.get_instance()

    # Parse since parameter
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            return {
                "success": False,
                "error": "Invalid datetime format for 'since'. Use ISO format.",
            }

    # Get session-specific or total costs
    if session_id:
        session_usages = service.get_costs_by_session(session_id)
        total_cost = sum(u.cost_usd for u in session_usages)
        total_input = sum(u.input_tokens for u in session_usages)
        total_output = sum(u.output_tokens for u in session_usages)

        # Aggregate by model for this session
        by_model: dict[str, dict] = {}
        for usage in session_usages:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "call_count": 0,
                }
            by_model[usage.model]["input_tokens"] += usage.input_tokens
            by_model[usage.model]["output_tokens"] += usage.output_tokens
            by_model[usage.model]["cost_usd"] += usage.cost_usd
            by_model[usage.model]["call_count"] += 1

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "total_cost_usd": total_cost,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "call_count": len(session_usages),
                "by_model": by_model,
                "usages": [asdict(u) for u in session_usages],
            },
        }

    # Get total costs
    total = service.get_total_costs(since=since_dt)
    return {
        "success": True,
        "data": total,
    }


@router.get("/costs/check-limit")
async def check_cost_limit(
    session_id: str = Query(..., description="Session ID to check"),
    limit_usd: float = Query(..., description="Cost limit in USD"),
    token: dict = Depends(verify_token),
):
    """セッションのコスト上限をチェックする

    Args:
        session_id: チェックするセッションID
        limit_usd: コスト上限（USD）

    Returns:
        上限を超えているかどうかの結果
    """
    service = CostService.get_instance()
    is_over = service.check_cost_limit(session_id, limit_usd)

    # Get current cost for the session
    session_usages = service.get_costs_by_session(session_id)
    current_cost = sum(u.cost_usd for u in session_usages)

    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "limit_usd": limit_usd,
            "current_cost_usd": current_cost,
            "is_over_limit": is_over,
            "remaining_usd": max(0, limit_usd - current_cost),
        },
    }


# ============== プロンプト管理 API ==============


@router.get("/prompts")
async def get_prompts(
    token: dict = Depends(verify_token),
):
    """全プロンプト一覧を取得する"""
    service = PromptService.get_instance()
    prompts = service.get_all_prompts()
    return {
        "success": True,
        "data": {
            "prompts": [
                {
                    "id": p.id,
                    "name": p.name,
                    "version": p.version,
                    "updated_at": p.updated_at,
                }
                for p in prompts
            ],
            "total": len(prompts),
        },
    }


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    token: dict = Depends(verify_token),
):
    """個別プロンプトを取得する"""
    service = PromptService.get_instance()
    prompt = service.get_prompt(prompt_id)

    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

    return {
        "success": True,
        "data": {
            "id": prompt.id,
            "name": prompt.name,
            "content": prompt.content,
            "version": prompt.version,
            "updated_at": prompt.updated_at,
            "history": [
                {
                    "version": h.version,
                    "content": h.content,
                    "updated_at": h.updated_at,
                }
                for h in prompt.history
            ],
        },
    }


@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: PromptUpdateRequest,
    token: dict = Depends(verify_token),
):
    """プロンプトを更新する"""
    service = PromptService.get_instance()

    # プロンプトが存在するか確認
    existing = service.get_prompt(prompt_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

    try:
        updated = service.update_prompt(prompt_id, request.content)
        return {
            "success": True,
            "data": {
                "id": updated.id,
                "name": updated.name,
                "content": updated.content,
                "version": updated.version,
                "updated_at": updated.updated_at,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/prompts/{prompt_id}/rollback/{version}")
async def rollback_prompt(
    prompt_id: str,
    version: int,
    token: dict = Depends(verify_token),
):
    """プロンプトを指定バージョンにロールバックする"""
    service = PromptService.get_instance()

    # プロンプトが存在するか確認
    existing = service.get_prompt(prompt_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

    try:
        rolled_back = service.rollback_prompt(prompt_id, version)
        return {
            "success": True,
            "data": {
                "id": rolled_back.id,
                "name": rolled_back.name,
                "content": rolled_back.content,
                "version": rolled_back.version,
                "updated_at": rolled_back.updated_at,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/prompts/{prompt_id}/history")
async def get_prompt_history(
    prompt_id: str,
    token: dict = Depends(verify_token),
):
    """プロンプトの履歴を取得する"""
    service = PromptService.get_instance()

    # プロンプトが存在するか確認
    existing = service.get_prompt(prompt_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")

    history = service.get_prompt_history(prompt_id)
    return {
        "success": True,
        "data": {
            "prompt_id": prompt_id,
            "history": [
                {
                    "version": h.version,
                    "content": h.content,
                    "updated_at": h.updated_at,
                }
                for h in history
            ],
        },
    }
