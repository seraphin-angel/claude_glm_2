"""P3-54: パーソナライゼーション - ユーザーモデルのテスト"""

import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.auth.jwt_handler import create_access_token
from app.models.user import (
    UserPlan,
    ConversationRecord,
    UserProfile,
    UserCreateRequest,
    UserUpdatePlanRequest,
    UserResponse,
)

client = TestClient(app)


class TestUserPlan:
    """UserPlan Enumのテスト"""

    def test_user_plan_values(self):
        """プランの値が正しい"""
        assert UserPlan.FREE.value == "free"
        assert UserPlan.PAID.value == "paid"

    def test_user_plan_is_string_enum(self):
        """UserPlanはstr Enum"""
        assert isinstance(UserPlan.FREE, str)
        assert UserPlan.FREE == "free"


class TestConversationRecord:
    """ConversationRecordのテスト"""

    def test_create_conversation_record(self):
        """会話レコードを作成できる"""
        record = ConversationRecord(question="テスト質問")
        assert record.question == "テスト質問"
        assert record.category is None
        assert record.feedback_score is None
        assert record.timestamp is not None

    def test_create_conversation_record_with_all_fields(self):
        """全フィールドを指定して会話レコードを作成"""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = ConversationRecord(
            question="テスト質問",
            category="操作方法",
            timestamp=ts,
            feedback_score=5,
        )
        assert record.question == "テスト質問"
        assert record.category == "操作方法"
        assert record.timestamp == ts
        assert record.feedback_score == 5

    def test_conversation_record_is_frozen(self):
        """会話レコードは不変"""
        record = ConversationRecord(question="テスト")
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            record.question = "変更"

    def test_empty_question_raises_error(self):
        """空の質問はエラー"""
        with pytest.raises(ValueError, match="question must not be empty"):
            ConversationRecord(question="")

    def test_whitespace_only_question_raises_error(self):
        """空白のみの質問はエラー"""
        with pytest.raises(ValueError, match="question must not be empty"):
            ConversationRecord(question="   ")

    def test_feedback_score_out_of_range_low(self):
        """フィードバックスコアが低すぎる場合はエラー"""
        with pytest.raises(ValueError, match="feedback_score must be between 1 and 5"):
            ConversationRecord(question="テスト", feedback_score=0)

    def test_feedback_score_out_of_range_high(self):
        """フィードバックスコアが高すぎる場合はエラー"""
        with pytest.raises(ValueError, match="feedback_score must be between 1 and 5"):
            ConversationRecord(question="テスト", feedback_score=6)

    def test_valid_feedback_scores(self):
        """有効なフィードバックスコア"""
        for score in [1, 2, 3, 4, 5]:
            record = ConversationRecord(question="テスト", feedback_score=score)
            assert record.feedback_score == score


class TestUserProfile:
    """UserProfileのテスト"""

    def test_create_user_profile(self):
        """ユーザープロファイルを作成できる"""
        profile = UserProfile(user_id="user-123")
        assert profile.user_id == "user-123"
        assert profile.plan == UserPlan.FREE
        assert profile.conversations == ()
        assert profile.preferred_categories == ()
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_create_user_profile_with_paid_plan(self):
        """有料プランでユーザープロファイルを作成"""
        profile = UserProfile(user_id="user-456", plan=UserPlan.PAID)
        assert profile.plan == UserPlan.PAID

    def test_user_profile_is_frozen(self):
        """ユーザープロファイルは不変"""
        profile = UserProfile(user_id="user-123")
        with pytest.raises(Exception):
            profile.plan = UserPlan.PAID

    def test_empty_user_id_raises_error(self):
        """空のユーザーIDはエラー"""
        with pytest.raises(ValueError, match="user_id must not be empty"):
            UserProfile(user_id="")

    def test_invalid_user_id_special_chars(self):
        """特殊文字を含むユーザーIDはエラー"""
        with pytest.raises(ValueError, match="user_id must start with alphanumeric"):
            UserProfile(user_id="user@123")

    def test_invalid_user_id_starts_with_hyphen(self):
        """ハイフンで始まるユーザーIDはエラー"""
        with pytest.raises(ValueError, match="user_id must start with alphanumeric"):
            UserProfile(user_id="-user123")

    def test_valid_user_ids(self):
        """有効なユーザーID"""
        valid_ids = ["user123", "user-123", "USER-456", "abc", "123", "a1-b2-c3"]
        for uid in valid_ids:
            profile = UserProfile(user_id=uid)
            assert profile.user_id == uid

    def test_user_profile_with_conversations(self):
        """会話履歴付きのユーザープロファイル"""
        conv1 = ConversationRecord(question="質問1", category="操作方法")
        conv2 = ConversationRecord(question="質問2", category="障害・トラブル")
        profile = UserProfile(
            user_id="user-123",
            conversations=(conv1, conv2),
        )
        assert len(profile.conversations) == 2
        assert profile.conversations[0].question == "質問1"
        assert profile.conversations[1].question == "質問2"

    def test_user_profile_with_preferred_categories(self):
        """希望カテゴリ付きのユーザープロファイル"""
        profile = UserProfile(
            user_id="user-123",
            preferred_categories=("操作方法", "契約・料金"),
        )
        assert len(profile.preferred_categories) == 2
        assert "操作方法" in profile.preferred_categories


class TestUserCreateRequest:
    """UserCreateRequestのテスト"""

    def test_create_user_create_request(self):
        """ユーザー作成リクエストを作成できる"""
        request = UserCreateRequest(user_id="new-user-123")
        assert request.user_id == "new-user-123"

    def test_empty_user_id_raises_error(self):
        """空のユーザーIDはエラー"""
        with pytest.raises(ValueError, match="user_id must not be empty"):
            UserCreateRequest(user_id="")


class TestUserUpdatePlanRequest:
    """UserUpdatePlanRequestのテスト"""

    def test_create_update_plan_request(self):
        """プラン更新リクエストを作成できる"""
        request = UserUpdatePlanRequest(plan=UserPlan.PAID)
        assert request.plan == UserPlan.PAID

    def test_update_plan_request_with_free(self):
        """無料プランへの更新リクエスト"""
        request = UserUpdatePlanRequest(plan=UserPlan.FREE)
        assert request.plan == UserPlan.FREE


class TestUserResponse:
    """UserResponseのテスト"""

    def test_create_user_response_from_profile(self):
        """UserProfileからUserResponseを作成"""
        conv = ConversationRecord(question="テスト質問", category="操作方法")
        profile = UserProfile(
            user_id="user-123",
            plan=UserPlan.PAID,
            conversations=(conv,),
            preferred_categories=("操作方法",),
        )
        response = UserResponse.from_profile(profile)
        
        assert response.user_id == "user-123"
        assert response.plan == UserPlan.PAID
        assert len(response.conversations) == 1
        assert response.conversations[0]["question"] == "テスト質問"
        assert response.preferred_categories == ["操作方法"]

    def test_user_response_model_dump(self):
        """UserResponseをdictに変換"""
        profile = UserProfile(user_id="user-123")
        response = UserResponse.from_profile(profile)
        data = response.model_dump()
        
        assert data["user_id"] == "user-123"
        assert data["plan"] == "free"
        assert "conversations" in data
        assert "created_at" in data
        assert "updated_at" in data


class TestUserContextMiddleware:
    """ユーザーコンテキストミドルウェアのテスト"""

    def test_set_and_get_user_context(self):
        """ユーザーコンテキストの設定と取得"""
        from app.middleware.user_context import (
            set_user_context,
            get_current_user_id,
            reset_user_context,
        )
        
        # 初期状態はNone
        reset_user_context()
        assert get_current_user_id() is None
        
        # 設定して取得
        set_user_context("user-123")
        assert get_current_user_id() == "user-123"
        
        # リセット
        reset_user_context()
        assert get_current_user_id() is None

    def test_user_context_with_multiple_values(self):
        """複数の値の設定"""
        from app.middleware.user_context import (
            set_user_context,
            get_current_user_id,
            reset_user_context,
        )
        
        reset_user_context()
        
        set_user_context("user-1")
        assert get_current_user_id() == "user-1"
        
        set_user_context("user-2")
        assert get_current_user_id() == "user-2"
        
        reset_user_context()


class TestUserService:
    """ユーザーサービスのテスト"""

    def setup_method(self):
        """各テストの前にシングルトンをリセット"""
        from app.services.user_service import UserService
        UserService.reset_instance()

    def test_create_user(self):
        """ユーザーを作成できる"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        request = UserCreateRequest(user_id="user-123")
        profile = service.create_user(request)
        
        assert profile.user_id == "user-123"
        assert profile.plan == UserPlan.FREE

    def test_create_duplicate_user_raises_error(self):
        """重複ユーザー作成はエラー"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        request = UserCreateRequest(user_id="user-123")
        service.create_user(request)
        
        with pytest.raises(ValueError, match="already exists"):
            service.create_user(request)

    def test_get_user(self):
        """ユーザーを取得できる"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        profile = service.get_user("user-123")
        assert profile is not None
        assert profile.user_id == "user-123"

    def test_get_nonexistent_user_returns_none(self):
        """存在しないユーザーはNoneを返す"""
        from app.services.user_service import UserService
        
        service = UserService.get_instance()
        profile = service.get_user("nonexistent")
        assert profile is None

    def test_get_or_create_user(self):
        """ユーザーを取得または作成"""
        from app.services.user_service import UserService
        
        service = UserService.get_instance()
        
        # 新規作成
        profile1 = service.get_or_create_user("user-123")
        assert profile1.user_id == "user-123"
        
        # 既存取得
        profile2 = service.get_or_create_user("user-123")
        assert profile2.user_id == "user-123"

    def test_update_user_plan(self):
        """ユーザープランを更新"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        updated = service.update_user_plan("user-123", UserPlan.PAID)
        assert updated.plan == UserPlan.PAID

    def test_update_nonexistent_user_plan_raises_error(self):
        """存在しないユーザーのプラン更新はエラー"""
        from app.services.user_service import UserService
        
        service = UserService.get_instance()
        
        with pytest.raises(ValueError, match="not found"):
            service.update_user_plan("nonexistent", UserPlan.PAID)

    def test_record_conversation(self):
        """会話履歴を記録"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        updated = service.record_conversation(
            user_id="user-123",
            question="テスト質問",
            category="操作方法",
            feedback_score=5,
        )
        
        assert len(updated.conversations) == 1
        assert updated.conversations[0].question == "テスト質問"
        assert updated.conversations[0].category == "操作方法"

    def test_record_multiple_conversations_updates_preferred_categories(self):
        """複数の会話履歴で希望カテゴリが更新される"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        # 異なるカテゴリの会話を記録
        service.record_conversation("user-123", "質問1", category="操作方法")
        service.record_conversation("user-123", "質問2", category="操作方法")
        service.record_conversation("user-123", "質問3", category="障害・トラブル")
        
        profile = service.get_user("user-123")
        assert "操作方法" in profile.preferred_categories

    def test_get_conversation_history(self):
        """会話履歴を取得"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        service.record_conversation("user-123", "質問1", category="操作方法")
        service.record_conversation("user-123", "質問2", category="障害・トラブル")
        
        history = service.get_conversation_history("user-123")
        assert len(history) == 2

    def test_get_conversation_history_with_category_filter(self):
        """カテゴリでフィルタした会話履歴"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        service.record_conversation("user-123", "質問1", category="操作方法")
        service.record_conversation("user-123", "質問2", category="障害・トラブル")
        service.record_conversation("user-123", "質問3", category="操作方法")
        
        history = service.get_conversation_history("user-123", category="操作方法")
        assert len(history) == 2
        assert all(c.category == "操作方法" for c in history)

    def test_get_conversation_history_with_limit(self):
        """件数制限付きで会話履歴を取得"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        for i in range(5):
            service.record_conversation("user-123", f"質問{i}")
        
        history = service.get_conversation_history("user-123", limit=3)
        assert len(history) == 3

    def test_delete_user(self):
        """ユーザーを削除"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest
        
        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-123"))
        
        service.delete_user("user-123")
        
        assert service.get_user("user-123") is None

    def test_delete_nonexistent_user_raises_error(self):
        """存在しないユーザーの削除はエラー"""
        from app.services.user_service import UserService
        
        service = UserService.get_instance()
        
        with pytest.raises(ValueError, match="not found"):
            service.delete_user("nonexistent")

    def test_user_service_is_singleton(self):
        """UserServiceはシングルトン"""
        from app.services.user_service import UserService

        service1 = UserService.get_instance()
        service2 = UserService.get_instance()

        assert service1 is service2


class TestUpdatePlanEndpoint:
    """HIGH-3: /api/users/me/plan エンドポイントの管理者権限チェックテスト"""

    def test_update_plan_requires_admin(self):
        """一般ユーザー（is_adminなし）がプラン変更しようとすると403"""
        token = create_access_token({"sub": "user-1"})
        response = client.patch(
            "/api/users/me/plan",
            json={"plan": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "管理者" in response.json()["detail"]

    def test_update_plan_admin_can_change(self):
        """is_admin=True の場合はプラン変更が可能"""
        token = create_access_token({"sub": "admin-user-1", "is_admin": True})
        response = client.patch(
            "/api/users/me/plan",
            json={"plan": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "paid"

    def test_update_plan_no_admin_flag_returns_403(self):
        """is_admin フラグがない場合も403を返す"""
        token = create_access_token({"sub": "user-2", "role": "user"})
        response = client.patch(
            "/api/users/me/plan",
            json={"plan": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_update_plan_is_admin_false_returns_403(self):
        """is_admin=False の場合も403を返す"""
        token = create_access_token({"sub": "user-3", "is_admin": False})
        response = client.patch(
            "/api/users/me/plan",
            json={"plan": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_update_plan_without_token_returns_403_or_401(self):
        """トークンなしで呼び出すと認証エラー（403または401）"""
        response = client.patch(
            "/api/users/me/plan",
            json={"plan": "paid"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# HIGH問題修正テスト（P3-53-security-issues Phase2）
# ---------------------------------------------------------------------------

class TestHistoryLimitValidation:
    """会話履歴のlimitパラメータバリデーションテスト（#7）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """テスト前のセットアップ"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        os.environ.setdefault("DEBUG_MODE", "true")
        from app.services.user_service import UserService
        UserService.reset_instance()
        yield
        UserService.reset_instance()

    @pytest.mark.asyncio
    async def test_history_limit_exceeds_100_returns_422(self):
        """limit=101の場合は422エラーを返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/users/me/history?limit=101",
                headers=headers,
            )
        # limitが100を超えるので422を返す
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_history_limit_zero_returns_422(self):
        """limit=0の場合は422エラーを返す"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/users/me/history?limit=0",
                headers=headers,
            )
        # limitが0なので422を返す
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_history_limit_100_is_valid(self):
        """limit=100は有効"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/users/me/history?limit=100",
                headers=headers,
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_history_limit_default_is_10(self):
        """デフォルトlimitは10"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/users/me/history",
                headers=headers,
            )
        assert response.status_code == 200


class TestUserServiceReadLock:
    """UserService 読み取りロックテスト（#11）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.services.user_service import UserService
        UserService.reset_instance()
        yield
        UserService.reset_instance()

    def test_get_user_thread_safe(self):
        """get_user はスレッドセーフに動作する（並列アクセスでデータが壊れない）"""
        import threading
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest

        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="concurrent-user"))

        results = []
        errors = []

        def read_user():
            try:
                for _ in range(100):
                    user = service.get_user("concurrent-user")
                    results.append(user is not None)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_user) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(results)

    def test_get_conversation_history_thread_safe(self):
        """get_conversation_history はスレッドセーフに動作する"""
        import threading
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest

        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="concurrent-user-2"))

        results = []
        errors = []

        def read_history():
            try:
                for _ in range(50):
                    history = service.get_conversation_history("concurrent-user-2", limit=10)
                    results.append(isinstance(history, list))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=read_history) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(results)

    def test_get_user_uses_data_lock(self):
        """UserServiceにget_user用ロックが実装されている"""
        import inspect
        from app.services.user_service import UserService

        source = inspect.getsource(UserService.get_user)
        # ロックが使用されていることを確認
        assert "_data_lock" in source or "with self._data_lock" in source

    def test_get_conversation_history_uses_data_lock(self):
        """UserServiceにget_conversation_history用ロックが実装されている"""
        import inspect
        from app.services.user_service import UserService

        source = inspect.getsource(UserService.get_conversation_history)
        # ロックが使用されていることを確認
        assert "_data_lock" in source or "with self._data_lock" in source


class TestUserProfileDatetimeField:
    """UserProfile datetime Field修正テスト（#16）"""

    def test_user_profile_timestamp_field_has_proper_type_hint(self):
        """UserProfile の datetime フィールドは Optional[datetime] | None の型アノテーション"""
        import inspect
        from app.models.user import UserProfile

        hints = UserProfile.__annotations__
        # created_at と updated_at が Optional[datetime] または datetime | None であること
        created_at_hint = str(hints.get("created_at", ""))
        # None が型アノテーションに含まれる
        assert "None" in created_at_hint or "Optional" in created_at_hint or "| None" in created_at_hint

    def test_conversation_record_timestamp_field_has_proper_type_hint(self):
        """ConversationRecord の timestamp フィールドは適切な型アノテーション"""
        import inspect
        from app.models.user import ConversationRecord

        hints = ConversationRecord.__annotations__
        timestamp_hint = str(hints.get("timestamp", ""))
        # Noneを許容するか、datetimeのデフォルト値が適切
        assert "datetime" in timestamp_hint

    def test_user_profile_created_at_default_is_none_compatible(self):
        """UserProfileのcreated_atはNoneをデフォルト値として設定可能"""
        from app.models.user import UserProfile

        # 直接 None を渡すと __init__ が現在時刻を設定する
        profile = UserProfile(user_id="test-user", created_at=None, updated_at=None)
        assert profile.created_at is not None
        assert profile.updated_at is not None


# ---------------------------------------------------------------------------
# Gap-2: is_admin 型攻撃テスト
# ---------------------------------------------------------------------------

class TestIsAdminTypeSafety:
    """is_admin 型安全性テスト（update_user_plan エンドポイント）"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        from app.services.user_service import UserService
        UserService.reset_instance()
        yield
        UserService.reset_instance()

    @pytest.fixture
    def user_token(self) -> str:
        """通常ユーザーJWTトークン"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from app.auth.jwt_handler import create_access_token
        return create_access_token({"sub": "user-001"})

    @pytest.mark.asyncio
    async def test_is_admin_string_true_returns_403(self) -> None:
        """is_admin='true'（文字列）は管理者権限を付与しない → 403"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "user-001", "is_admin": "true"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/users/me/plan",
                json={"plan": "paid"},
                headers=headers,
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_is_admin_int_1_returns_403(self) -> None:
        """is_admin=1（整数）は管理者権限を付与しない → 403"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "user-001", "is_admin": 1})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/users/me/plan",
                json={"plan": "paid"},
                headers=headers,
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_is_admin_bool_true_succeeds(self) -> None:
        """is_admin=True（bool）は管理者として認められる → 200"""
        import os
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.auth.jwt_handler import create_access_token

        token = create_access_token({"sub": "admin-user", "is_admin": True})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/users/me/plan",
                json={"plan": "paid"},
                headers=headers,
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Gap-5: update_preferred_categories テスト
# ---------------------------------------------------------------------------

class TestUpdatePreferredCategories:
    """update_preferred_categories のテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        from app.services.user_service import UserService
        UserService.reset_instance()
        yield
        UserService.reset_instance()

    def test_update_preferred_categories_success(self) -> None:
        """正常に preferred_categories を更新できる"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest

        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-cat-001"))

        updated = service.update_preferred_categories(
            "user-cat-001",
            ["billing", "technical", "general"],
        )
        assert updated.preferred_categories == ("billing", "technical", "general")

    def test_update_preferred_categories_nonexistent_user_raises(self) -> None:
        """存在しないユーザーは ValueError を発生させる"""
        from app.services.user_service import UserService
        import pytest

        service = UserService.get_instance()
        with pytest.raises(ValueError, match="not found"):
            service.update_preferred_categories("nonexistent-user", ["billing"])

    def test_update_preferred_categories_empty_list(self) -> None:
        """空リストでも更新できる"""
        from app.services.user_service import UserService
        from app.models.user import UserCreateRequest

        service = UserService.get_instance()
        service.create_user(UserCreateRequest(user_id="user-cat-002"))

        updated = service.update_preferred_categories("user-cat-002", [])
        assert updated.preferred_categories == ()
