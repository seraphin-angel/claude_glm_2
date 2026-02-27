"""エスカレーションAPIのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_handler import create_access_token
from app.main import app
from app.services.escalation_service import EscalationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_escalation_service():
    """各テスト後にシングルトンをリセット"""
    EscalationService.reset_instance()
    yield
    EscalationService.reset_instance()


@pytest.fixture
def auth_headers() -> dict:
    """認証ヘッダー"""
    token = create_access_token({"sub": "admin-user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_escalation_service():
    """EscalationServiceモック"""
    with patch(
        "app.api.admin.EscalationService.get_instance"
    ) as mock_get_instance:
        mock_service = MagicMock()
        mock_get_instance.return_value = mock_service
        yield mock_service


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetEscalations:
    """GET /api/admin/escalations のテスト"""

    async def test_get_escalations_success(
        self, auth_headers, mock_escalation_service
    ):
        """エスカレーション一覧取得成功"""
        mock_escalation_service.get_tickets.return_value = [
            {
                "id": "ESC-12345678",
                "reason": "テスト理由",
                "urgency": "high",
                "summary": "テストサマリー",
                "status": "open",
            }
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["tickets"]) == 1
        assert data["data"]["tickets"][0]["id"] == "ESC-12345678"

    async def test_get_escalations_empty(
        self, auth_headers, mock_escalation_service
    ):
        """エスカレーションがない場合"""
        mock_escalation_service.get_tickets.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["tickets"] == []
        assert data["data"]["total"] == 0

    async def test_get_escalations_with_limit(
        self, auth_headers, mock_escalation_service
    ):
        """limit パラメータのテスト"""
        mock_escalation_service.get_tickets.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations?limit=10",
                headers=auth_headers,
            )

        assert response.status_code == 200
        mock_escalation_service.get_tickets.assert_called_once_with(limit=10)

    async def test_get_escalations_unauthenticated(self):
        """認証なしでのアクセス"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/escalations")

        assert response.status_code == 401

    async def test_get_escalations_invalid_token(self):
        """無効なトークンで 403 が返る"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetEscalation:
    """GET /api/admin/escalations/{ticket_id} のテスト"""

    async def test_get_escalation_found(
        self, auth_headers, mock_escalation_service
    ):
        """チケットが見つかる場合"""
        mock_escalation_service.get_ticket.return_value = {
            "id": "ESC-ABCD1234",
            "reason": "テスト理由",
            "urgency": "medium",
            "summary": "テストサマリー",
            "status": "open",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations/ESC-ABCD1234",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "ESC-ABCD1234"

    async def test_get_escalation_not_found(
        self, auth_headers, mock_escalation_service
    ):
        """チケットが見つからない場合"""
        mock_escalation_service.get_ticket.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/admin/escalations/ESC-999",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"]

    async def test_get_escalation_unauthenticated(self):
        """認証なしでのアクセス"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/escalations/ESC-123")

        assert response.status_code == 401
