"""P3-49: データ保持ポリシー（GDPR）のテスト (TDD - RED phase)"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# RetentionPolicy Model tests
# ---------------------------------------------------------------------------
class TestRetentionPolicyModel:
    """データ保持ポリシーモデルのテスト"""

    def test_retention_policy_create_valid(self):
        """有効なポリシー作成"""
        from app.models.retention import RetentionPolicy
        policy = RetentionPolicy(
            tenant_id="acme-corp",
            data_type="chat_history",
            retention_days=90,
        )
        assert policy.tenant_id == "acme-corp"
        assert policy.data_type == "chat_history"
        assert policy.retention_days == 90
        assert policy.is_active is True

    def test_retention_policy_negative_days_raises(self):
        """負の保持期間はエラー"""
        from app.models.retention import RetentionPolicy
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            RetentionPolicy(
                tenant_id="acme-corp",
                data_type="chat_history",
                retention_days=-1,
            )

    def test_retention_policy_zero_days_raises(self):
        """0日の保持期間はエラー"""
        from app.models.retention import RetentionPolicy
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            RetentionPolicy(
                tenant_id="acme-corp",
                data_type="chat_history",
                retention_days=0,
            )

    def test_data_deletion_request_model(self):
        """データ削除リクエストモデル"""
        from app.models.retention import DataDeletionRequest
        req = DataDeletionRequest(
            tenant_id="acme-corp",
            user_id="user-123",
            reason="GDPR Article 17 - Right to erasure",
        )
        assert req.tenant_id == "acme-corp"
        assert req.user_id == "user-123"

    def test_audit_log_entry_model(self):
        """監査ログエントリモデル"""
        from app.models.retention import AuditLogEntry
        entry = AuditLogEntry(
            operation="delete",
            tenant_id="acme-corp",
            data_type="chat_history",
            record_count=5,
            performed_by="system",
        )
        assert entry.operation == "delete"
        assert entry.record_count == 5
        assert entry.timestamp is not None

    def test_retention_policy_immutability(self):
        """RetentionPolicyは不変"""
        from app.models.retention import RetentionPolicy
        policy = RetentionPolicy(
            tenant_id="test",
            data_type="chat_history",
            retention_days=30,
        )
        with pytest.raises((TypeError, Exception)):
            policy.retention_days = 60


# ---------------------------------------------------------------------------
# RetentionService tests
# ---------------------------------------------------------------------------
class TestRetentionService:
    """データ保持サービスのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.retention_service import RetentionService
        RetentionService.reset_instance()
        yield
        RetentionService.reset_instance()

    def test_create_policy(self):
        """ポリシーを作成できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import RetentionPolicy
        service = RetentionService.get_instance()
        policy = RetentionPolicy(
            tenant_id="acme-corp",
            data_type="chat_history",
            retention_days=90,
        )
        created = service.create_policy(policy)
        assert created.tenant_id == "acme-corp"
        assert created.retention_days == 90

    def test_get_policy(self):
        """ポリシーを取得できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import RetentionPolicy
        service = RetentionService.get_instance()
        policy = RetentionPolicy(
            tenant_id="acme-corp",
            data_type="chat_history",
            retention_days=90,
        )
        service.create_policy(policy)
        result = service.get_policy("acme-corp", "chat_history")
        assert result is not None
        assert result.retention_days == 90

    def test_get_policy_not_found(self):
        """存在しないポリシーはNoneを返す"""
        from app.services.retention_service import RetentionService
        service = RetentionService.get_instance()
        result = service.get_policy("nonexistent", "chat_history")
        assert result is None

    def test_list_policies_by_tenant(self):
        """テナント別ポリシー一覧を取得できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import RetentionPolicy
        service = RetentionService.get_instance()
        service.create_policy(RetentionPolicy(tenant_id="t1", data_type="chat_history", retention_days=30))
        service.create_policy(RetentionPolicy(tenant_id="t1", data_type="documents", retention_days=365))
        service.create_policy(RetentionPolicy(tenant_id="t2", data_type="chat_history", retention_days=60))

        t1_policies = service.list_policies("t1")
        assert len(t1_policies) == 2

    def test_delete_user_data(self):
        """ユーザーデータを削除できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import DataDeletionRequest
        service = RetentionService.get_instance()
        req = DataDeletionRequest(
            tenant_id="acme-corp",
            user_id="user-123",
            reason="GDPR Article 17",
        )
        result = service.delete_user_data(req)
        assert result["success"] is True
        assert "deletion_id" in result
        assert result["user_id"] == "user-123"

    def test_get_audit_logs(self):
        """監査ログを取得できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import DataDeletionRequest
        service = RetentionService.get_instance()
        # 削除操作を実行
        req = DataDeletionRequest(
            tenant_id="audit-test",
            user_id="user-audit",
            reason="Test",
        )
        service.delete_user_data(req)
        logs = service.get_audit_logs("audit-test")
        assert len(logs) >= 1
        assert logs[0]["tenant_id"] == "audit-test"
        assert logs[0]["operation"] == "delete_user_data"

    def test_find_expired_data(self):
        """期限切れデータを特定できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import RetentionPolicy
        service = RetentionService.get_instance()
        # 1日の保持ポリシーを作成
        policy = RetentionPolicy(
            tenant_id="expire-test",
            data_type="chat_history",
            retention_days=1,
        )
        service.create_policy(policy)
        expired = service.find_expired_data("expire-test")
        # データがない場合は空リストを返す
        assert isinstance(expired, list)

    def test_run_cleanup_job(self):
        """クリーンアップジョブを実行できる"""
        from app.services.retention_service import RetentionService
        service = RetentionService.get_instance()
        result = service.run_cleanup_job()
        assert "cleaned_records" in result
        assert "errors" in result
        assert isinstance(result["cleaned_records"], int)

    def test_update_policy(self):
        """ポリシーを更新できる"""
        from app.services.retention_service import RetentionService
        from app.models.retention import RetentionPolicy
        service = RetentionService.get_instance()
        policy = RetentionPolicy(
            tenant_id="update-test",
            data_type="chat_history",
            retention_days=30,
        )
        service.create_policy(policy)
        updated = service.update_policy("update-test", "chat_history", retention_days=60)
        assert updated.retention_days == 60

    def test_update_nonexistent_policy_raises(self):
        """存在しないポリシーの更新はエラー"""
        from app.services.retention_service import RetentionService
        service = RetentionService.get_instance()
        with pytest.raises(ValueError, match="not found"):
            service.update_policy("ghost", "chat_history", retention_days=60)


# ---------------------------------------------------------------------------
# GDPR API tests
# ---------------------------------------------------------------------------
class TestGdprAPI:
    """GDPR APIのテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """各テスト前にサービスをリセット"""
        from app.services.retention_service import RetentionService
        RetentionService.reset_instance()
        yield
        RetentionService.reset_instance()

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
    async def test_create_retention_policy_api(self, admin_headers):
        """保持ポリシー作成API"""
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
                "/api/gdpr/policies",
                json={
                    "tenant_id": "api-gdpr-test",
                    "data_type": "chat_history",
                    "retention_days": 90,
                },
                headers=admin_headers,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["retention_days"] == 90

    @pytest.mark.asyncio
    async def test_list_retention_policies_api(self, admin_headers):
        """保持ポリシー一覧API"""
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
                "/api/gdpr/policies?tenant_id=list-test",
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "policies" in data["data"]

    @pytest.mark.asyncio
    async def test_delete_user_data_api(self, admin_headers):
        """ユーザーデータ削除API（GDPR Article 17）"""
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
                "/api/gdpr/delete-user-data",
                json={
                    "tenant_id": "acme-corp",
                    "user_id": "user-to-delete",
                    "reason": "GDPR Article 17 - Right to erasure",
                },
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "user-to-delete"

    @pytest.mark.asyncio
    async def test_get_audit_logs_api(self, admin_headers):
        """監査ログ取得API"""
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
                "/api/gdpr/audit-logs?tenant_id=audit-corp",
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "logs" in data["data"]

    @pytest.mark.asyncio
    async def test_run_cleanup_api(self, admin_headers):
        """クリーンアップジョブ実行API"""
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
                "/api/gdpr/cleanup",
                headers=admin_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleaned_records" in data["data"]

    @pytest.mark.asyncio
    async def test_gdpr_endpoints_require_auth(self):
        """GDPR エンドポイントには認証が必要"""
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
                "/api/gdpr/delete-user-data",
                json={
                    "tenant_id": "acme",
                    "user_id": "user-123",
                    "reason": "test",
                },
            )
        assert response.status_code in (401, 403)
