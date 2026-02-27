"""HIGH-4: JWT ハンドラーのセキュリティテスト

get_user_id_from_payload が sub クレームのみを使用することを確認するテスト。
"""

import pytest

from app.auth.jwt_handler import create_access_token, get_user_id_from_payload


class TestGetUserIdFromPayload:
    """get_user_id_from_payload のユニットテスト"""

    def test_get_user_id_from_payload_returns_sub(self):
        """sub クレームからユーザーIDを取得できる"""
        payload = {"sub": "user-123"}
        result = get_user_id_from_payload(payload)
        assert result == "user-123"

    def test_get_user_id_from_payload_ignores_user_id_field(self):
        """user_id フィールドは無視される（sub がない場合はNone）"""
        payload = {"user_id": "user-456"}
        result = get_user_id_from_payload(payload)
        assert result is None

    def test_get_user_id_from_payload_ignores_id_field(self):
        """id フィールドは無視される（sub がない場合はNone）"""
        payload = {"id": "user-789"}
        result = get_user_id_from_payload(payload)
        assert result is None

    def test_get_user_id_from_payload_returns_none_when_no_sub(self):
        """sub がない場合は None を返す"""
        payload = {"name": "テストユーザー", "email": "test@example.com"}
        result = get_user_id_from_payload(payload)
        assert result is None

    def test_get_user_id_from_payload_converts_to_string(self):
        """数値の sub も文字列に変換される"""
        payload = {"sub": 12345}
        result = get_user_id_from_payload(payload)
        assert result == "12345"
        assert isinstance(result, str)

    def test_get_user_id_from_payload_empty_payload(self):
        """空のペイロードは None を返す"""
        payload = {}
        result = get_user_id_from_payload(payload)
        assert result is None

    def test_get_user_id_from_payload_sub_takes_priority_over_other_fields(self):
        """sub が存在する場合、他のフィールドより優先される"""
        payload = {
            "sub": "correct-user",
            "user_id": "wrong-user",
            "id": "also-wrong",
        }
        result = get_user_id_from_payload(payload)
        assert result == "correct-user"

    def test_get_user_id_from_payload_ignores_userId_field(self):
        """userId フィールドは無視される（sub がない場合はNone）"""
        payload = {"userId": "user-camel"}
        result = get_user_id_from_payload(payload)
        assert result is None


class TestVerifyTokenAndGetUserId:
    """#14: verify_token_and_get_user_id のエンドポイント統合テスト"""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """環境変数を設定"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")

    @pytest.mark.asyncio
    async def test_valid_jwt_without_sub_returns_401(self):
        """sub クレームなしの有効な JWT は 401 を返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        # sub を持たないトークン（ユーザーIDなし）
        token_without_sub = create_access_token({"role": "user", "name": "test-user"})
        headers = {"Authorization": f"Bearer {token_without_sub}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/users/me", headers=headers)

        assert response.status_code == 401, (
            f"sub なしの JWT は 401 を返すべきだが {response.status_code} を返した"
        )

    @pytest.mark.asyncio
    async def test_valid_jwt_with_sub_returns_user_id(self):
        """sub クレームありの有効な JWT は正常にユーザーIDを返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token
        from app.services.user_service import UserService

        UserService.reset_instance()

        user_id = "test-user-abc123"
        token = create_access_token({"sub": user_id})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/users/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id


# ---------------------------------------------------------------------------
# MEDIUM問題修正テスト（P3-53-security-issues Phase3）
# ---------------------------------------------------------------------------

class TestJWTHandlerMediumFixes:
    """JWT ハンドラーMEDIUM問題修正テスト"""

    # --- #12: verify_token HTTPステータスコード修正 ---

    @pytest.mark.asyncio
    async def test_verify_token_returns_401_not_403(self):
        """無効なトークンで verify_token は401を返す（403ではなく）"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from fastapi.security import HTTPAuthorizationCredentials
        from app.auth.jwt_handler import verify_token
        from fastapi import HTTPException

        invalid_creds = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here",
        )

        try:
            await verify_token(invalid_creds)
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 401, f"Expected 401, got {e.status_code}"

    # --- #13: ExpiredSignatureError を分離 ---

    @pytest.mark.asyncio
    async def test_expired_token_returns_401_with_expired_message(self):
        """期限切れトークンで401を返し、適切なメッセージを含む"""
        import os
        from datetime import timedelta
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from fastapi.security import HTTPAuthorizationCredentials
        from app.auth.jwt_handler import create_access_token, verify_token
        from fastapi import HTTPException

        # 既に期限切れのトークンを作成
        token = create_access_token(
            {"sub": "test-user"},
            expires_delta=timedelta(seconds=-1),
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        try:
            await verify_token(creds)
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 401
            # 期限切れを示すメッセージが含まれる
            assert "期限" in e.detail or "expired" in e.detail.lower() or "有効期限" in e.detail
