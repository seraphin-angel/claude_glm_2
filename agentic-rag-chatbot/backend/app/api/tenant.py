"""P3-48: マルチテナント対応 - テナント管理APIエンドポイント"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt_handler import verify_token
from app.models.tenant import TenantCreateRequest, TenantResponse, TenantUpdateConfigRequest
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


def _to_response(tenant) -> dict:
    """テナントをレスポンス形式に変換する（不変パターン）。"""
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "config": {
            "llm_model": tenant.config.llm_model,
            "max_tokens": tenant.config.max_tokens,
            "system_prompt_override": tenant.config.system_prompt_override,
            "rate_limit_chat": tenant.config.rate_limit_chat,
            "rate_limit_stream": tenant.config.rate_limit_stream,
        },
        "is_active": tenant.is_active,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントを作成する。"""
    service = TenantService.get_instance()
    try:
        tenant = service.create_tenant(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return {
        "success": True,
        "data": _to_response(tenant),
    }


@router.get("")
async def list_tenants(
    include_inactive: bool = False,
    token: dict = Depends(verify_token),
) -> dict:
    """テナント一覧を取得する。"""
    service = TenantService.get_instance()
    tenants = service.list_tenants(include_inactive=include_inactive)
    return {
        "success": True,
        "data": {
            "tenants": [_to_response(t) for t in tenants],
            "total": len(tenants),
        },
    }


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントを取得する。"""
    service = TenantService.get_instance()
    tenant = service.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    return {
        "success": True,
        "data": _to_response(tenant),
    }


@router.put("/{tenant_id}/config")
async def update_tenant_config(
    tenant_id: str,
    request: TenantUpdateConfigRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """テナント設定を更新する。"""
    service = TenantService.get_instance()
    try:
        tenant = service.update_tenant_config(tenant_id, request.config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return {
        "success": True,
        "data": _to_response(tenant),
    }


@router.delete("/{tenant_id}")
async def deactivate_tenant(
    tenant_id: str,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントを無効化する。"""
    service = TenantService.get_instance()
    try:
        tenant = service.deactivate_tenant(tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return {
        "success": True,
        "data": _to_response(tenant),
    }
