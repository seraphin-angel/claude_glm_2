"""
GuardrailsMiddlewareのエッジケースのテスト

テスト方針:
- 巨大バイナリリクエストの処理
- multipart/form-dataリクエストの処理
- デコード不能なリクエストボディの処理
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.middleware.guardrails import (
    GuardrailsMiddleware,
    reset_guardrails_context,
)
from app.models.guardrails import RiskLevel
from app.services.guardrails_service import GuardrailsService


class TestGuardrailsBinaryAndMultipart:
    """バイナリ・マルチパートデータのエッジケーステスト"""

    def setup_method(self):
        """各テスト前にシングルトンをリセット"""
        GuardrailsService.reset_instance()
        reset_guardrails_context()

    def _create_test_app(self, mock_service=None):
        """テスト用FastAPIアプリを作成"""
        app = FastAPI()

        @app.post("/api/v1/chat")
        async def chat_endpoint():
            return {"response": "test response"}

        app.add_middleware(GuardrailsMiddleware, service=mock_service)
        return app

    def test_large_binary_request_does_not_timeout(self):
        """巨大なバイナリリクエストでもガードレールチェックがタイムアウトしないこと"""
        mock_service = MagicMock()
        mock_service.check_input.return_value = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW.value,
            "violations": [],
            "violation_types": [],
            "confidence": 0.95,
        }

        app = self._create_test_app(mock_service)
        client = TestClient(app)

        # 10MBのバイナリデータを作成
        large_binary = b"\x00" * (10 * 1024 * 1024)

        # デコード不能なため、警告ログが出るがリクエストは通過する
        response = client.post(
            "/api/v1/chat",
            content=large_binary,
            headers={"Content-Type": "application/octet-stream"},
        )

        # バイナリはデコード不能だが、フェイルセーフでリクエストは通過
        assert response.status_code == 200

    def test_non_utf8_request_body(self):
        """UTF-8以外のエンコーディングのリクエストボディ"""
        mock_service = MagicMock()
        mock_service.check_input.return_value = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW.value,
            "violations": [],
            "violation_types": [],
            "confidence": 0.95,
        }

        app = self._create_test_app(mock_service)
        client = TestClient(app)

        # Shift-JISエンコードされたテキスト
        shift_jis_text = "テスト".encode("shift-jis")

        response = client.post(
            "/api/v1/chat",
            content=shift_jis_text,
            headers={"Content-Type": "text/plain; charset=shift-jis"},
        )

        # デコードに失敗してもフェイルセーフで通過
        assert response.status_code == 200

    def test_binary_with_null_bytes(self):
        """NULLバイトを含むバイナリデータの処理"""
        mock_service = MagicMock()
        mock_service.check_input.return_value = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW.value,
            "violations": [],
            "violation_types": [],
            "confidence": 0.95,
        }

        app = self._create_test_app(mock_service)
        client = TestClient(app)

        # NULLバイトを含むデータ
        binary_with_nulls = b"test\x00\x01\x02content"

        response = client.post(
            "/api/v1/chat",
            content=binary_with_nulls,
            headers={"Content-Type": "application/octet-stream"},
        )

        assert response.status_code == 200

    def test_empty_binary_request(self):
        """空のバイナリリクエスト"""
        mock_service = MagicMock()
        mock_service.check_input.return_value = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW.value,
            "violations": [],
            "violation_types": [],
            "confidence": 0.95,
        }

        app = self._create_test_app(mock_service)
        client = TestClient(app)

        # 空ボディ
        response = client.post(
            "/api/v1/chat",
            content=b"",
            headers={"Content-Type": "application/octet-stream"},
        )

        # 空ボディでもエラーにならず通過
        assert response.status_code == 200

    def test_multipart_form_data_skipped_gracefully(self):
        """multipart/form-dataリクエストはデコード失敗でもフェイルセーフで通過"""
        mock_service = MagicMock()
        mock_service.check_input.return_value = {
            "is_safe": True,
            "risk_level": RiskLevel.LOW.value,
            "violations": [],
            "violation_types": [],
            "confidence": 0.95,
        }

        app = self._create_test_app(mock_service)
        client = TestClient(app)

        # multipart/form-dataの境界データ
        multipart_data = b"------WebKitFormBoundary\r\nContent-Disposition: form-data; name=\"field\"\r\n\r\nvalue\r\n------WebKitFormBoundary--\r\n"

        response = client.post(
            "/api/v1/chat",
            content=multipart_data,
            headers={"Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary"},
        )

        # multipartはUTF-8デコードできないが、フェイルセーフで通過
        assert response.status_code == 200
