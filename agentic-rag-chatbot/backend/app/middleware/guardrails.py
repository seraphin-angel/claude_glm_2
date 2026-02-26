"""ガードレールミドルウェア - リクエスト/レスポンスの安全性チェック"""

import json
import logging
from contextvars import ContextVar
from typing import Any, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.guardrails import RiskLevel, SafetyCheckResult
from app.services.guardrails_service import GuardrailsService

logger = logging.getLogger(__name__)

# リクエストスコープのガードレール結果管理
_current_guardrails_result: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "current_guardrails_result", default=None
)

# チェック対象のパス（プレフィックスマッチ）
GUARDRAILS_PATHS = ["/api/v1/chat"]

# チェック除外パス
EXCLUDED_PATHS = ["/health", "/metrics", "/docs", "/openapi.json"]


def get_guardrails_result() -> Optional[dict[str, Any]]:
    """現在のリクエストスコープのガードレール結果を取得する"""
    return _current_guardrails_result.get()


def set_guardrails_result(result: dict[str, Any]) -> None:
    """ガードレール結果をコンテキストに設定する"""
    _current_guardrails_result.set(result)


def reset_guardrails_context() -> None:
    """ガードレールコンテキストをリセットする"""
    _current_guardrails_result.set(None)


class GuardrailsMiddleware(BaseHTTPMiddleware):
    """リクエストとレスポンスに対してガードレールチェックを行うミドルウェア。

    - リクエスト: 入力ガードレールチェック（違反時は400エラー）
    - レスポンス: 出力ガードレールチェック（違反時はログ出力＆サニタイズ）
    """

    def __init__(self, app, service: GuardrailsService | None = None):
        super().__init__(app)
        self._service = service or GuardrailsService.get_instance()

    async def dispatch(self, request: Request, call_next):
        # 除外パスのチェック
        if self._should_skip(request.url.path):
            return await call_next(request)

        # チェック対象パスのチェック
        if not self._should_check(request.url.path):
            return await call_next(request)

        # リクエストボディの読み込み
        try:
            body = await request.body()
            content = body.decode("utf-8") if body else ""
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
            return await call_next(request)

        # 入力ガードレールチェック
        input_result = await self._check_input(content)
        
        if not input_result.get("is_safe", True):
            logger.warning(
                f"Input guardrails violation: {input_result.get('violations')}"
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "入力が拒否されました",
                    "violations": input_result.get("violations", []),
                    "risk_level": input_result.get("risk_level"),
                },
            )

        # コンテキストに結果を保存
        set_guardrails_result(input_result)

        try:
            # レスポンス取得
            response = await call_next(request)
            
            # 出力ガードレールチェック（レスポンスボディがある場合）
            response = await self._check_and_sanitize_response(response)
            
        finally:
            reset_guardrails_context()

        return response

    def _should_skip(self, path: str) -> bool:
        """パスがチェック除外かどうか"""
        return any(path.startswith(excluded) for excluded in EXCLUDED_PATHS)

    def _should_check(self, path: str) -> bool:
        """パスがチェック対象かどうか"""
        return any(path.startswith(check_path) for check_path in GUARDRAILS_PATHS)

    async def _check_input(self, content: str) -> dict[str, Any]:
        """入力コンテンツのガードレールチェック"""
        try:
            # JSON パースを試行
            try:
                data = json.loads(content)
                message = data.get("message", content)
            except json.JSONDecodeError:
                message = content

            return self._service.check_input(message)
        except Exception as e:
            logger.error(f"Error during input guardrails check: {e}")
            return {"is_safe": True, "risk_level": RiskLevel.LOW.value}

    async def _check_and_sanitize_response(self, response: Response) -> Response:
        """レスポンスのガードレールチェックとサニタイズ"""
        # レスポンスボディを読み込み
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            content = body.decode("utf-8") if body else ""
            
            if not content:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            # 出力ガードレールチェック
            output_result = self._service.check_output(content)
            
            if not output_result.get("is_safe", True):
                logger.warning(
                    f"Output guardrails violation: {output_result.get('violations')}"
                )
                
                # サニタイズ済みコンテンツを使用
                if output_result.get("sanitized_content"):
                    content = output_result["sanitized_content"]
                    body = content.encode("utf-8")

            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
            
        except Exception as e:
            logger.error(f"Error during output guardrails check: {e}")
            return response
