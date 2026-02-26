"""P3-50: CRM/チケットシステム連携のテスト (TDD - RED phase)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Base Adapter Interface tests
# ---------------------------------------------------------------------------
class TestBaseAdapter:
    """アダプターインターフェースのテスト"""

    def test_base_adapter_cannot_be_instantiated(self):
        """抽象基底クラスは直接インスタンス化できない"""
        from app.integrations.base import BaseTicketAdapter
        import inspect
        assert inspect.isabstract(BaseTicketAdapter)

    def test_adapter_has_required_methods(self):
        """アダプターに必要なメソッドが定義されている"""
        from app.integrations.base import BaseTicketAdapter
        required_methods = ["create_ticket", "get_ticket", "update_ticket", "close_ticket"]
        for method in required_methods:
            assert hasattr(BaseTicketAdapter, method), f"Missing method: {method}"

    def test_ticket_model_creation(self):
        """チケットモデルの作成"""
        from app.integrations.base import TicketData, TicketPriority, TicketStatus
        ticket = TicketData(
            title="ログインできません",
            description="パスワードをリセットしても解決しない",
            priority=TicketPriority.HIGH,
            tenant_id="acme-corp",
            user_id="user-123",
            metadata={"source": "chatbot"},
        )
        assert ticket.title == "ログインできません"
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.status == TicketStatus.OPEN

    def test_ticket_model_immutability(self):
        """TicketDataは不変"""
        from app.integrations.base import TicketData, TicketPriority
        ticket = TicketData(
            title="Test",
            description="Test desc",
            priority=TicketPriority.MEDIUM,
            tenant_id="test",
            user_id="user-1",
        )
        with pytest.raises((TypeError, Exception)):
            ticket.title = "Changed"

    def test_ticket_priority_enum(self):
        """チケット優先度の列挙型"""
        from app.integrations.base import TicketPriority
        assert TicketPriority.LOW.value == "low"
        assert TicketPriority.MEDIUM.value == "medium"
        assert TicketPriority.HIGH.value == "high"
        assert TicketPriority.URGENT.value == "urgent"

    def test_ticket_status_enum(self):
        """チケット状態の列挙型"""
        from app.integrations.base import TicketStatus
        assert TicketStatus.OPEN.value == "open"
        assert TicketStatus.IN_PROGRESS.value == "in_progress"
        assert TicketStatus.RESOLVED.value == "resolved"
        assert TicketStatus.CLOSED.value == "closed"


# ---------------------------------------------------------------------------
# MockAdapter tests (for testing)
# ---------------------------------------------------------------------------
class TestMockAdapter:
    """モックアダプターのテスト（テスト用実装）"""

    @pytest.fixture
    def mock_adapter(self):
        """モックアダプターインスタンス"""
        from app.integrations.mock_adapter import MockTicketAdapter
        return MockTicketAdapter()

    @pytest.mark.asyncio
    async def test_create_ticket(self, mock_adapter):
        """チケットを作成できる"""
        from app.integrations.base import TicketData, TicketPriority
        ticket_data = TicketData(
            title="テスト問題",
            description="詳細説明",
            priority=TicketPriority.HIGH,
            tenant_id="test-tenant",
            user_id="user-001",
        )
        result = await mock_adapter.create_ticket(ticket_data)
        assert result["success"] is True
        assert "ticket_id" in result
        assert result["ticket_id"].startswith("MOCK-")

    @pytest.mark.asyncio
    async def test_get_ticket(self, mock_adapter):
        """チケットを取得できる"""
        from app.integrations.base import TicketData, TicketPriority
        # まず作成
        ticket_data = TicketData(
            title="Get Test",
            description="Test",
            priority=TicketPriority.LOW,
            tenant_id="test-tenant",
            user_id="user-002",
        )
        create_result = await mock_adapter.create_ticket(ticket_data)
        ticket_id = create_result["ticket_id"]

        # 取得
        get_result = await mock_adapter.get_ticket(ticket_id)
        assert get_result is not None
        assert get_result["ticket_id"] == ticket_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_ticket(self, mock_adapter):
        """存在しないチケットはNoneを返す"""
        result = await mock_adapter.get_ticket("NONEXISTENT-999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_ticket(self, mock_adapter):
        """チケットを更新できる"""
        from app.integrations.base import TicketData, TicketPriority
        ticket_data = TicketData(
            title="Update Test",
            description="Test",
            priority=TicketPriority.LOW,
            tenant_id="test-tenant",
            user_id="user-003",
        )
        create_result = await mock_adapter.create_ticket(ticket_data)
        ticket_id = create_result["ticket_id"]

        update_result = await mock_adapter.update_ticket(
            ticket_id,
            {"status": "in_progress", "comment": "担当者がアサインされました"},
        )
        assert update_result["success"] is True

    @pytest.mark.asyncio
    async def test_close_ticket(self, mock_adapter):
        """チケットをクローズできる"""
        from app.integrations.base import TicketData, TicketPriority
        ticket_data = TicketData(
            title="Close Test",
            description="Test",
            priority=TicketPriority.LOW,
            tenant_id="test-tenant",
            user_id="user-004",
        )
        create_result = await mock_adapter.create_ticket(ticket_data)
        ticket_id = create_result["ticket_id"]

        close_result = await mock_adapter.close_ticket(ticket_id, resolution="解決済み")
        assert close_result["success"] is True


# ---------------------------------------------------------------------------
# ZendeskAdapter tests
# ---------------------------------------------------------------------------
class TestZendeskAdapter:
    """Zendeskアダプターのテスト"""

    @pytest.fixture
    def zendesk_adapter(self):
        """Zendeskアダプターインスタンス（モック設定）"""
        from app.integrations.zendesk import ZendeskAdapter
        return ZendeskAdapter(
            subdomain="test-company",
            email="admin@test.com",
            api_token="test-token-xyz",
        )

    def test_adapter_initialization(self, zendesk_adapter):
        """アダプターが正しく初期化される"""
        from app.integrations.zendesk import ZendeskAdapter
        assert zendesk_adapter is not None

    @pytest.mark.asyncio
    async def test_create_ticket_with_mock(self, zendesk_adapter):
        """モックHTTPでチケットを作成できる"""
        from app.integrations.base import TicketData, TicketPriority
        import httpx

        ticket_data = TicketData(
            title="Zendesk Test",
            description="テスト説明",
            priority=TicketPriority.HIGH,
            tenant_id="test-tenant",
            user_id="user-zen",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "ticket": {
                "id": 12345,
                "status": "new",
                "subject": "Zendesk Test",
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await zendesk_adapter.create_ticket(ticket_data)

        assert result["success"] is True
        assert result["ticket_id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_ticket_with_mock(self, zendesk_adapter):
        """モックHTTPでチケットを取得できる"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ticket": {
                "id": 99,
                "status": "open",
                "subject": "Test",
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await zendesk_adapter.get_ticket("99")

        assert result is not None
        assert result["ticket_id"] == "99"

    def test_priority_mapping(self, zendesk_adapter):
        """優先度マッピングが正しい"""
        from app.integrations.base import TicketPriority
        from app.integrations.zendesk import ZendeskAdapter
        assert zendesk_adapter._map_priority(TicketPriority.LOW) == "low"
        assert zendesk_adapter._map_priority(TicketPriority.MEDIUM) == "normal"
        assert zendesk_adapter._map_priority(TicketPriority.HIGH) == "high"
        assert zendesk_adapter._map_priority(TicketPriority.URGENT) == "urgent"


# ---------------------------------------------------------------------------
# IntegrationService tests
# ---------------------------------------------------------------------------
class TestIntegrationService:
    """CRM連携サービスのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.integration_service import IntegrationService
        IntegrationService.reset_instance()
        yield
        IntegrationService.reset_instance()

    def test_register_adapter(self):
        """アダプターを登録できる"""
        from app.services.integration_service import IntegrationService
        from app.integrations.mock_adapter import MockTicketAdapter
        service = IntegrationService.get_instance()
        adapter = MockTicketAdapter()
        service.register_adapter("acme-corp", adapter)
        assert service.get_adapter("acme-corp") is not None

    def test_get_adapter_not_registered(self):
        """未登録テナントのアダプターはNoneを返す"""
        from app.services.integration_service import IntegrationService
        service = IntegrationService.get_instance()
        result = service.get_adapter("nonexistent-tenant")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_ticket_via_service(self):
        """サービス経由でチケットを作成できる"""
        from app.services.integration_service import IntegrationService
        from app.integrations.mock_adapter import MockTicketAdapter
        from app.integrations.base import TicketData, TicketPriority
        service = IntegrationService.get_instance()
        service.register_adapter("test-tenant", MockTicketAdapter())

        ticket_data = TicketData(
            title="サービステスト",
            description="詳細",
            priority=TicketPriority.MEDIUM,
            tenant_id="test-tenant",
            user_id="user-svc",
        )
        result = await service.create_ticket("test-tenant", ticket_data)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_ticket_no_adapter(self):
        """アダプター未登録でチケット作成するとエラー"""
        from app.services.integration_service import IntegrationService
        from app.integrations.base import TicketData, TicketPriority
        service = IntegrationService.get_instance()

        ticket_data = TicketData(
            title="Test",
            description="Test",
            priority=TicketPriority.LOW,
            tenant_id="no-adapter",
            user_id="user-x",
        )
        with pytest.raises(ValueError, match="No adapter"):
            await service.create_ticket("no-adapter", ticket_data)

    @pytest.mark.asyncio
    async def test_escalation_hook(self):
        """エスカレーションフックがCRMチケットを自動作成する"""
        from app.services.integration_service import IntegrationService
        from app.integrations.mock_adapter import MockTicketAdapter
        service = IntegrationService.get_instance()
        service.register_adapter("hook-tenant", MockTicketAdapter())

        result = await service.on_escalation(
            tenant_id="hook-tenant",
            user_id="user-escalated",
            reason="解決不可",
            urgency="high",
            summary="ユーザーが困っています",
        )
        assert result["success"] is True
        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_escalation_hook_no_adapter_returns_none(self):
        """アダプター未登録テナントのエスカレーションはNoneを返す"""
        from app.services.integration_service import IntegrationService
        service = IntegrationService.get_instance()

        result = await service.on_escalation(
            tenant_id="no-crm-tenant",
            user_id="user-x",
            reason="test",
            urgency="low",
            summary="test",
        )
        assert result is None

    def test_list_registered_tenants(self):
        """登録済みテナント一覧を取得できる"""
        from app.services.integration_service import IntegrationService
        from app.integrations.mock_adapter import MockTicketAdapter
        service = IntegrationService.get_instance()
        service.register_adapter("t1", MockTicketAdapter())
        service.register_adapter("t2", MockTicketAdapter())
        tenants = service.list_registered_tenants()
        assert "t1" in tenants
        assert "t2" in tenants


# ---------------------------------------------------------------------------
# CRM Integration API tests
# ---------------------------------------------------------------------------
class TestIntegrationAPI:
    """CRM連携APIのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.integration_service import IntegrationService
        IntegrationService.reset_instance()
        yield
        IntegrationService.reset_instance()

    @pytest.fixture
    def admin_headers(self) -> dict:
        """管理者JWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.auth.jwt_handler import create_access_token
        token = create_access_token({"sub": "admin-user", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_register_mock_adapter_api(self, admin_headers):
        """モックアダプター登録API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/integrations/register",
                json={
                    "tenant_id": "api-crm-test",
                    "adapter_type": "mock",
                    "config": {},
                },
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_integrations_api(self, admin_headers):
        """連携一覧API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/integrations",
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tenants" in data["data"]

    @pytest.mark.asyncio
    async def test_create_ticket_api(self, admin_headers):
        """チケット作成API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.integration_service import IntegrationService
        from app.integrations.mock_adapter import MockTicketAdapter

        # アダプターを事前登録
        service = IntegrationService.get_instance()
        service.register_adapter("ticket-api-test", MockTicketAdapter())

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/integrations/tickets",
                json={
                    "tenant_id": "ticket-api-test",
                    "title": "APIテストチケット",
                    "description": "詳細説明",
                    "priority": "high",
                    "user_id": "user-api",
                },
                headers=admin_headers,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "ticket_id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_ticket_no_adapter_returns_404(self, admin_headers):
        """アダプター未登録テナントでのチケット作成は404"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/integrations/tickets",
                json={
                    "tenant_id": "no-adapter-tenant",
                    "title": "Test",
                    "description": "Test",
                    "priority": "low",
                    "user_id": "user-x",
                },
                headers=admin_headers,
            )
        assert response.status_code in (404, 422, 400)

    @pytest.mark.asyncio
    async def test_integration_endpoints_require_auth(self):
        """連携エンドポイントには認証が必要"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/integrations")
        assert response.status_code in (401, 403)
