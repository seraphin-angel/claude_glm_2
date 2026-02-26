"""P3-48: マルチテナント対応のテスト (TDD - RED phase)"""

import pytest
from unittest.mock import patch, MagicMock
from contextvars import ContextVar


# ---------------------------------------------------------------------------
# TenantModel tests
# ---------------------------------------------------------------------------
class TestTenantModel:
    """テナントモデルのテスト"""

    def test_tenant_create_valid(self):
        """有効なテナント作成"""
        from app.models.tenant import Tenant, TenantConfig
        config = TenantConfig(llm_model="gpt-4o-mini", max_tokens=2000)
        tenant = Tenant(
            tenant_id="acme-corp",
            name="Acme Corporation",
            config=config,
        )
        assert tenant.tenant_id == "acme-corp"
        assert tenant.name == "Acme Corporation"
        assert tenant.config.llm_model == "gpt-4o-mini"
        assert tenant.is_active is True

    def test_tenant_id_validation_invalid_chars(self):
        """テナントIDに無効な文字が含まれる場合はエラー"""
        from app.models.tenant import Tenant, TenantConfig
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            Tenant(
                tenant_id="invalid tenant id!",
                name="Invalid",
                config=TenantConfig(),
            )

    def test_tenant_id_validation_empty(self):
        """テナントIDが空の場合はエラー"""
        from app.models.tenant import Tenant, TenantConfig
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            Tenant(
                tenant_id="",
                name="Empty ID",
                config=TenantConfig(),
            )

    def test_tenant_config_defaults(self):
        """テナント設定のデフォルト値"""
        from app.models.tenant import TenantConfig
        config = TenantConfig()
        assert config.llm_model is None or isinstance(config.llm_model, str)
        assert config.max_tokens is None or isinstance(config.max_tokens, int)

    def test_tenant_create_request_model(self):
        """テナント作成リクエストモデル"""
        from app.models.tenant import TenantCreateRequest
        req = TenantCreateRequest(
            tenant_id="new-tenant",
            name="New Tenant",
        )
        assert req.tenant_id == "new-tenant"
        assert req.name == "New Tenant"

    def test_tenant_immutability(self):
        """テナントモデルは不変"""
        from app.models.tenant import Tenant, TenantConfig
        tenant = Tenant(
            tenant_id="test-tenant",
            name="Test",
            config=TenantConfig(),
        )
        # Pydantic v2のモデルはfrozen=Trueで不変にする
        with pytest.raises((TypeError, Exception)):
            tenant.name = "Changed"


# ---------------------------------------------------------------------------
# TenantContext tests
# ---------------------------------------------------------------------------
class TestTenantContext:
    """テナントコンテキスト（ContextVar）のテスト"""

    def test_get_current_tenant_id_not_set(self):
        """テナントIDが未設定の場合はNoneを返す"""
        from app.middleware.tenant import get_current_tenant_id, reset_tenant_context
        reset_tenant_context()
        result = get_current_tenant_id()
        assert result is None

    def test_set_and_get_current_tenant_id(self):
        """テナントIDを設定・取得できる"""
        from app.middleware.tenant import set_tenant_context, get_current_tenant_id, reset_tenant_context
        reset_tenant_context()
        set_tenant_context("acme-corp")
        assert get_current_tenant_id() == "acme-corp"
        reset_tenant_context()

    def test_reset_tenant_context(self):
        """テナントコンテキストのリセット"""
        from app.middleware.tenant import set_tenant_context, get_current_tenant_id, reset_tenant_context
        set_tenant_context("some-tenant")
        reset_tenant_context()
        assert get_current_tenant_id() is None

    def test_get_collection_name_with_tenant(self):
        """テナントIDを含むコレクション名を生成"""
        from app.middleware.tenant import get_tenant_collection_name
        name = get_tenant_collection_name("acme-corp", "product_support_v2")
        assert name == "acme-corp_product_support_v2"

    def test_get_collection_name_no_tenant(self):
        """テナントIDなしの場合はデフォルトのコレクション名を使用"""
        from app.middleware.tenant import get_tenant_collection_name
        name = get_tenant_collection_name(None, "product_support_v2")
        assert name == "product_support_v2"


# ---------------------------------------------------------------------------
# TenantMiddleware tests
# ---------------------------------------------------------------------------
class TestTenantMiddleware:
    """テナントミドルウェアのテスト"""

    @pytest.mark.asyncio
    async def test_middleware_extracts_tenant_from_header(self):
        """X-Tenant-IDヘッダーからテナントIDを抽出"""
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
                "/api/health",
                headers={"X-Tenant-ID": "acme-corp"},
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_works_without_tenant_header(self):
        """X-Tenant-IDヘッダーなしでもリクエストが通る"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TenantService tests
# ---------------------------------------------------------------------------
class TestTenantService:
    """テナントサービスのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.tenant_service import TenantService
        TenantService.reset_instance()
        yield
        TenantService.reset_instance()

    def test_create_tenant(self):
        """テナントを作成できる"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        req = TenantCreateRequest(tenant_id="test-co", name="Test Co")
        tenant = service.create_tenant(req)
        assert tenant.tenant_id == "test-co"
        assert tenant.name == "Test Co"
        assert tenant.is_active is True

    def test_create_duplicate_tenant_raises(self):
        """重複するテナントIDは作成不可"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        req = TenantCreateRequest(tenant_id="dup-tenant", name="Dup")
        service.create_tenant(req)
        with pytest.raises(ValueError, match="already exists"):
            service.create_tenant(req)

    def test_get_tenant_exists(self):
        """存在するテナントを取得できる"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="get-test", name="Get Test"))
        tenant = service.get_tenant("get-test")
        assert tenant is not None
        assert tenant.tenant_id == "get-test"

    def test_get_tenant_not_exists(self):
        """存在しないテナントはNoneを返す"""
        from app.services.tenant_service import TenantService
        service = TenantService.get_instance()
        tenant = service.get_tenant("nonexistent")
        assert tenant is None

    def test_list_tenants(self):
        """テナント一覧を取得できる"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="t1", name="Tenant 1"))
        service.create_tenant(TenantCreateRequest(tenant_id="t2", name="Tenant 2"))
        tenants = service.list_tenants()
        assert len(tenants) == 2

    def test_deactivate_tenant(self):
        """テナントを無効化できる"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="deact-test", name="Deactivate Test"))
        result = service.deactivate_tenant("deact-test")
        assert result.is_active is False

    def test_deactivate_nonexistent_tenant_raises(self):
        """存在しないテナントの無効化はエラー"""
        from app.services.tenant_service import TenantService
        service = TenantService.get_instance()
        with pytest.raises(ValueError, match="not found"):
            service.deactivate_tenant("nonexistent")

    def test_validate_tenant_active(self):
        """アクティブなテナントのバリデーション"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="valid-tenant", name="Valid"))
        assert service.validate_tenant("valid-tenant") is True

    def test_validate_tenant_inactive(self):
        """非アクティブなテナントのバリデーション"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="inactive-t", name="Inactive"))
        service.deactivate_tenant("inactive-t")
        assert service.validate_tenant("inactive-t") is False

    def test_validate_tenant_not_exists(self):
        """存在しないテナントのバリデーション"""
        from app.services.tenant_service import TenantService
        service = TenantService.get_instance()
        assert service.validate_tenant("ghost-tenant") is False

    def test_update_tenant_config(self):
        """テナント設定を更新できる"""
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest, TenantConfig
        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="config-test", name="Config Test"))
        new_config = TenantConfig(llm_model="gpt-4o", max_tokens=4000)
        updated = service.update_tenant_config("config-test", new_config)
        assert updated.config.llm_model == "gpt-4o"
        assert updated.config.max_tokens == 4000


# ---------------------------------------------------------------------------
# Tenant API tests
# ---------------------------------------------------------------------------
class TestTenantAPI:
    """テナントAPIのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.tenant_service import TenantService
        TenantService.reset_instance()
        yield
        TenantService.reset_instance()

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
    async def test_create_tenant_api(self, admin_headers):
        """テナント作成API"""
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
                "/api/tenants",
                json={"tenant_id": "api-test-tenant", "name": "API Test Tenant"},
                headers=admin_headers,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["tenant_id"] == "api-test-tenant"

    @pytest.mark.asyncio
    async def test_list_tenants_api(self, admin_headers):
        """テナント一覧API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/tenants", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tenants" in data["data"]

    @pytest.mark.asyncio
    async def test_get_tenant_api(self, admin_headers):
        """テナント取得API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest

        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="get-api-test", name="Get API Test"))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/tenants/get-api-test", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tenant_id"] == "get-api-test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_tenant_api(self, admin_headers):
        """存在しないテナント取得API - 404"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/tenants/nonexistent-xyz", headers=admin_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_tenant_api(self, admin_headers):
        """テナント無効化API"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.tenant_service import TenantService
        from app.models.tenant import TenantCreateRequest

        service = TenantService.get_instance()
        service.create_tenant(TenantCreateRequest(tenant_id="deact-api", name="Deactivate API"))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/tenants/deact-api", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_create_tenant_requires_auth(self):
        """テナント作成には認証が必要"""
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
                "/api/tenants",
                json={"tenant_id": "unauth-tenant", "name": "Unauth"},
            )
        assert response.status_code in (401, 403)
