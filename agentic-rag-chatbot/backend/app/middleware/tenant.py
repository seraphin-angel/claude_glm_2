"""P3-48: マルチテナント対応 - テナントミドルウェアとコンテキスト管理"""

from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# リクエストスコープのテナントID管理
_current_tenant_id: ContextVar[Optional[str]] = ContextVar(
    "current_tenant_id", default=None
)

TENANT_HEADER = "X-Tenant-ID"


def get_current_tenant_id() -> Optional[str]:
    """現在のリクエストスコープのテナントIDを取得する。"""
    return _current_tenant_id.get()


def set_tenant_context(tenant_id: str) -> None:
    """テナントIDをコンテキストに設定する。"""
    _current_tenant_id.set(tenant_id)


def reset_tenant_context() -> None:
    """テナントコンテキストをリセットする。"""
    _current_tenant_id.set(None)


def get_tenant_collection_name(
    tenant_id: Optional[str],
    base_collection_name: str,
) -> str:
    """テナントIDを含むChromaDBコレクション名を生成する。

    Args:
        tenant_id: テナントID（Noneの場合はbase_collection_nameをそのまま返す）
        base_collection_name: ベースのコレクション名

    Returns:
        テナント固有のコレクション名
    """
    if tenant_id is None:
        return base_collection_name
    return f"{tenant_id}_{base_collection_name}"


class TenantMiddleware(BaseHTTPMiddleware):
    """X-Tenant-IDヘッダーからテナントIDを抽出してコンテキストに設定するミドルウェア。"""

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get(TENANT_HEADER)

        if tenant_id:
            set_tenant_context(tenant_id)
        else:
            reset_tenant_context()

        try:
            response = await call_next(request)
        finally:
            reset_tenant_context()

        return response
