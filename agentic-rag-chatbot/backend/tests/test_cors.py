"""CORS設定のテスト"""

import pytest
from httpx import AsyncClient

from app.config.settings import Settings


class TestCorsSettings:
    """Settings の CORS設定値に関するユニットテスト"""

    def test_cors_allowed_methods_default(self):
        """cors_allowed_methods のデフォルト値が GET, POST, OPTIONS であること"""
        settings = Settings()
        assert settings.cors_allowed_methods == ["GET", "POST", "OPTIONS"]

    def test_cors_allowed_headers_default(self):
        """cors_allowed_headers のデフォルト値が Authorization, Content-Type であること"""
        settings = Settings()
        assert settings.cors_allowed_headers == ["Authorization", "Content-Type"]

    def test_cors_allowed_methods_excludes_wildcard(self):
        """cors_allowed_methods に '*' が含まれないこと"""
        settings = Settings()
        assert "*" not in settings.cors_allowed_methods

    def test_cors_allowed_headers_excludes_wildcard(self):
        """cors_allowed_headers に '*' が含まれないこと"""
        settings = Settings()
        assert "*" not in settings.cors_allowed_headers


class TestCorsPreflightRequest:
    """OPTIONSプリフライトリクエストの統合テスト"""

    async def test_options_preflight_returns_ok(self, client: AsyncClient):
        """OPTIONS プリフライトリクエストが正常に動作すること"""
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code in (200, 204)

    async def test_options_preflight_allows_get(self, client: AsyncClient):
        """Access-Control-Allow-Methods に GET が含まれること"""
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods

    async def test_options_preflight_allows_post(self, client: AsyncClient):
        """Access-Control-Allow-Methods に POST が含まれること"""
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods

    async def test_cors_allows_configured_origin(self, client: AsyncClient):
        """設定済みオリジン (localhost:5173) へのリクエストが CORS ヘッダーを返すこと"""
        response = await client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
