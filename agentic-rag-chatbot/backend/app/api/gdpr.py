"""P3-49: データ保持ポリシー（GDPR）- GDPRコンプライアンスAPIエンドポイント"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt_handler import verify_token
from app.models.retention import DataDeletionRequest, RetentionPolicyCreateRequest
from app.services.retention_service import RetentionService

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


def _policy_to_dict(policy) -> dict:
    """保持ポリシーをレスポンス形式に変換する（不変パターン）。"""
    return {
        "tenant_id": policy.tenant_id,
        "data_type": policy.data_type,
        "retention_days": policy.retention_days,
        "is_active": policy.is_active,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.post("/policies", status_code=status.HTTP_201_CREATED)
async def create_retention_policy(
    request: RetentionPolicyCreateRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """データ保持ポリシーを作成する。"""
    from app.models.retention import RetentionPolicy
    service = RetentionService.get_instance()
    policy = RetentionPolicy(
        tenant_id=request.tenant_id,
        data_type=request.data_type,
        retention_days=request.retention_days,
    )
    created = service.create_policy(policy)
    return {
        "success": True,
        "data": _policy_to_dict(created),
    }


@router.get("/policies")
async def list_retention_policies(
    tenant_id: str,
    include_inactive: bool = False,
    token: dict = Depends(verify_token),
) -> dict:
    """テナントのデータ保持ポリシー一覧を取得する。"""
    service = RetentionService.get_instance()
    policies = service.list_policies(tenant_id, include_inactive=include_inactive)
    return {
        "success": True,
        "data": {
            "policies": [_policy_to_dict(p) for p in policies],
            "total": len(policies),
        },
    }


@router.get("/policies/{tenant_id}/{data_type}")
async def get_retention_policy(
    tenant_id: str,
    data_type: str,
    token: dict = Depends(verify_token),
) -> dict:
    """特定のデータ保持ポリシーを取得する。"""
    service = RetentionService.get_instance()
    policy = service.get_policy(tenant_id, data_type)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Retention policy for tenant '{tenant_id}' and data_type '{data_type}' not found",
        )
    return {
        "success": True,
        "data": _policy_to_dict(policy),
    }


@router.post("/delete-user-data")
async def delete_user_data(
    request: DataDeletionRequest,
    token: dict = Depends(verify_token),
) -> dict:
    """ユーザーデータを削除する（GDPR Article 17 - Right to erasure）。"""
    service = RetentionService.get_instance()
    result = service.delete_user_data(request)
    return {
        "success": True,
        "data": result,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    tenant_id: str,
    limit: int = 100,
    token: dict = Depends(verify_token),
) -> dict:
    """監査ログを取得する。"""
    service = RetentionService.get_instance()
    logs = service.get_audit_logs(tenant_id, limit=limit)
    return {
        "success": True,
        "data": {
            "logs": logs,
            "total": len(logs),
            "tenant_id": tenant_id,
        },
    }


@router.post("/cleanup")
async def run_cleanup(
    token: dict = Depends(verify_token),
) -> dict:
    """期限切れデータのクリーンアップジョブを実行する。"""
    service = RetentionService.get_instance()
    result = service.run_cleanup_job()
    return {
        "success": True,
        "data": result,
    }
