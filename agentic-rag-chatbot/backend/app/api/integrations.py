"""P3-50: CRM/チケットシステム連携 - APIエンドポイント"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.integrations.base import TicketData, TicketPriority
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class RegisterAdapterRequest(BaseModel):
    """アダプター登録リクエスト"""

    tenant_id: str
    adapter_type: str  # "mock", "zendesk", etc.
    config: dict[str, Any] = {}


class CreateTicketRequest(BaseModel):
    """チケット作成リクエスト"""

    tenant_id: str
    title: str
    description: str
    priority: str = "medium"
    user_id: str
    metadata: Optional[dict[str, Any]] = None
    tags: list[str] = []


def _priority_from_str(priority_str: str) -> TicketPriority:
    """文字列からTicketPriorityに変換する。"""
    mapping = {
        "low": TicketPriority.LOW,
        "medium": TicketPriority.MEDIUM,
        "high": TicketPriority.HIGH,
        "urgent": TicketPriority.URGENT,
    }
    return mapping.get(priority_str.lower(), TicketPriority.MEDIUM)


@router.post("/register")
async def register_adapter(
    request: RegisterAdapterRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントにCRMアダプターを登録する。"""
    service = IntegrationService.get_instance()

    if request.adapter_type == "mock":
        from app.integrations.mock_adapter import MockTicketAdapter
        adapter = MockTicketAdapter()
    elif request.adapter_type == "zendesk":
        from app.integrations.zendesk import ZendeskAdapter
        try:
            adapter = ZendeskAdapter(
                subdomain=request.config["subdomain"],
                email=request.config["email"],
                api_token=request.config["api_token"],
            )
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required config field: {e}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown adapter type: {request.adapter_type}",
        )

    service.register_adapter(request.tenant_id, adapter)

    return {
        "success": True,
        "data": {
            "tenant_id": request.tenant_id,
            "adapter_type": request.adapter_type,
        },
    }


@router.get("")
async def list_integrations(
    token: dict = Depends(verify_token),
) -> dict:
    """登録済み連携一覧を取得する。"""
    service = IntegrationService.get_instance()
    tenants = service.list_registered_tenants()
    return {
        "success": True,
        "data": {
            "tenants": tenants,
            "total": len(tenants),
        },
    }


@router.delete("/{tenant_id}")
async def unregister_adapter(
    tenant_id: str,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントのCRMアダプター登録を解除する。"""
    service = IntegrationService.get_instance()
    success = service.unregister_adapter(tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No integration registered for tenant '{tenant_id}'",
        )
    return {
        "success": True,
        "data": {"tenant_id": tenant_id},
    }


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: CreateTicketRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """CRMチケットを作成する。"""
    service = IntegrationService.get_instance()

    ticket_data = TicketData(
        title=request.title,
        description=request.description,
        priority=_priority_from_str(request.priority),
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        metadata=request.metadata,
        tags=request.tags,
    )

    try:
        result = await service.create_ticket(request.tenant_id, ticket_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return {
        "success": True,
        "data": result,
    }


@router.get("/tickets/{tenant_id}/{ticket_id}")
async def get_ticket(
    tenant_id: str,
    ticket_id: str,
    token: dict = Depends(verify_token),
) -> dict:
    """CRMチケットを取得する。"""
    service = IntegrationService.get_instance()

    try:
        ticket = await service.get_ticket(tenant_id, ticket_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found",
        )

    return {
        "success": True,
        "data": ticket,
    }
