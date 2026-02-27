"""セキュリティヘッダーミドルウェアのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestSecurityHeaders:
    async def test_health_has_x_content_type_options(self, client: AsyncClient):
        """GET /api/health に X-Content-Type-Options: nosniff が付与されること"""
        response = await client.get("/api/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_health_has_x_frame_options(self, client: AsyncClient):
        """GET /api/health に X-Frame-Options: DENY が付与されること"""
        response = await client.get("/api/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_health_has_referrer_policy(self, client: AsyncClient):
        """GET /api/health に Referrer-Policy が付与されること"""
        response = await client.get("/api/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_health_has_all_security_headers(self, client: AsyncClient):
        """GET /api/health に3つのセキュリティヘッダーがすべて存在すること"""
        response = await client.get("/api/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_chat_post_has_security_headers(self, client: AsyncClient, auth_headers: dict):
        """POST /api/chat にもセキュリティヘッダーが付与されること"""
        mock_service = MagicMock()
        mock_service.start_chat = AsyncMock(return_value="test-thread-id")

        with patch("app.api.chat.get_chat_service", return_value=mock_service):
            response = await client.post(
                "/api/chat",
                json={"message": "テスト"},
                headers=auth_headers,
            )

        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_health_has_content_security_policy(self, client: AsyncClient):
        """GET /api/health に Content-Security-Policy が付与されること（#17）"""
        response = await client.get("/api/health")
        assert "content-security-policy" in response.headers

    async def test_health_has_strict_transport_security(self, client: AsyncClient):
        """GET /api/health に Strict-Transport-Security が付与されること（#17）"""
        response = await client.get("/api/health")
        assert "strict-transport-security" in response.headers
