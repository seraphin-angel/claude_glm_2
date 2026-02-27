"""P3-54: パーソナライゼーション - ユーザーコンテキストミドルウェア

セキュリティ修正: X-User-ID ヘッダーを信頼せず、
Authorization ヘッダーの JWT からユーザーIDを抽出する。
"""

from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from jose import ExpiredSignatureError, JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

import logging

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# リクエストスコープのユーザーID管理
_current_user_id: ContextVar[Optional[str]] = ContextVar(
    "current_user_id", default=None
)


def get_current_user_id() -> Optional[str]:
    """現在のリクエストスコープのユーザーIDを取得する。"""
    return _current_user_id.get()


def set_user_context(user_id: str) -> None:
    """ユーザーIDをコンテキストに設定する。"""
    _current_user_id.set(user_id)


def reset_user_context() -> None:
    """ユーザーコンテキストをリセットする。"""
    _current_user_id.set(None)


def _extract_user_id_from_authorization(authorization: Optional[str]) -> Optional[str]:
    """Authorization ヘッダーの Bearer JWT からユーザーIDを抽出する。

    Args:
        authorization: Authorization ヘッダーの値（例: "Bearer <token>"）

    Returns:
        JWTの sub クレームから取得したユーザーID。
        トークンが未提供・無効・sub クレームなしの場合は None。
    """
    if not authorization:
        return None

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return str(user_id)
    except ExpiredSignatureError:
        logger.debug("token expired")
        return None
    except JWTError as e:
        logger.warning("JWT validation failed: %s", type(e).__name__)
        return None


class UserContextMiddleware(BaseHTTPMiddleware):
    """Authorization ヘッダーの JWT からユーザーIDを抽出してコンテキストに設定するミドルウェア。

    X-User-ID ヘッダーは偽装可能なため信頼しない。
    エンドポイントレベルの認証（Depends(verify_token)）に委ねる設計のため、
    JWT が無効でもリクエストを拒否しない。
    """

    async def dispatch(self, request: Request, call_next):
        authorization = request.headers.get("Authorization")
        user_id = _extract_user_id_from_authorization(authorization)

        if user_id:
            set_user_context(user_id)
        else:
            reset_user_context()

        try:
            response = await call_next(request)
        finally:
            reset_user_context()

        return response
