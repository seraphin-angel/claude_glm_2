import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt_handler import create_access_token
from app.main import app
from app.services.feedback_service import FeedbackService


@pytest.fixture(autouse=True)
def reset_feedback_service(tmp_path):
    """各テスト前後にシングルトンをリセットしてクリーンな状態を保つ"""
    FeedbackService.reset_instance()
    instance = FeedbackService(persist_path=str(tmp_path / "test_feedback.json"))
    FeedbackService._instance = instance
    yield
    FeedbackService.reset_instance()


class TestFeedbackService:
    def test_record_feedback_positive(self):
        """positive フィードバックが正しく記録される"""
        service = FeedbackService.get_instance()
        entry = service.record_feedback(
            message_id="msg-1", thread_id="thread-1", rating="positive"
        )

        assert entry["message_id"] == "msg-1"
        assert entry["thread_id"] == "thread-1"
        assert entry["rating"] == "positive"
        assert "timestamp" in entry

    def test_record_feedback_negative(self):
        """negative フィードバックが正しく記録される"""
        service = FeedbackService.get_instance()
        entry = service.record_feedback(
            message_id="msg-2", thread_id="thread-2", rating="negative"
        )

        assert entry["rating"] == "negative"

    def test_record_feedback_invalid_rating(self):
        """不正な rating は ValueError を発生させる"""
        service = FeedbackService.get_instance()
        with pytest.raises(ValueError, match="rating must be one of"):
            service.record_feedback(
                message_id="msg-3", thread_id="thread-3", rating="invalid"
            )

    def test_record_feedback_overwrite_same_message_id(self):
        """同じ message_id のフィードバックは上書きされる"""
        service = FeedbackService.get_instance()
        service.record_feedback(message_id="msg-4", thread_id="t", rating="positive")
        service.record_feedback(message_id="msg-4", thread_id="t", rating="negative")

        summary = service.get_feedback_summary()
        # 上書きされるので合計は1件
        assert summary["total"] == 1
        assert summary["negative"] == 1
        assert summary["positive"] == 0

    def test_get_feedback_summary_empty(self):
        """フィードバックなしの場合サマリーが正しく返る"""
        service = FeedbackService.get_instance()
        summary = service.get_feedback_summary()

        assert summary["total"] == 0
        assert summary["positive"] == 0
        assert summary["negative"] == 0

    def test_get_feedback_summary_counts(self):
        """positive/negative の件数が正しく集計される"""
        service = FeedbackService.get_instance()
        service.record_feedback(message_id="m1", thread_id="t", rating="positive")
        service.record_feedback(message_id="m2", thread_id="t", rating="positive")
        service.record_feedback(message_id="m3", thread_id="t", rating="negative")

        summary = service.get_feedback_summary()
        assert summary["total"] == 3
        assert summary["positive"] == 2
        assert summary["negative"] == 1

    def test_persistence(self, tmp_path):
        """ファイルへの永続化が正しく機能する"""
        persist_file = tmp_path / "persist_feedback.json"
        service1 = FeedbackService(persist_path=str(persist_file))
        service1.record_feedback(message_id="persist-msg", thread_id="t", rating="positive")

        service2 = FeedbackService(persist_path=str(persist_file))
        summary = service2.get_feedback_summary()
        assert summary["total"] == 1
        assert summary["positive"] == 1

    def test_singleton_pattern(self):
        """シングルトンパターンが正しく機能する"""
        service1 = FeedbackService.get_instance()
        service2 = FeedbackService.get_instance()
        assert service1 is service2

    def test_immutability_of_feedbacks_list(self):
        """record_feedback が元のリストを変更しない（イミュータブルパターン）"""
        service = FeedbackService.get_instance()
        original_feedbacks = service._feedbacks
        service.record_feedback(message_id="imm-msg", thread_id="t", rating="positive")
        assert service._feedbacks is not original_feedbacks

    def test_custom_timestamp(self):
        """カスタムタイムスタンプが正しく保存される"""
        service = FeedbackService.get_instance()
        ts = "2024-01-01T00:00:00+00:00"
        entry = service.record_feedback(
            message_id="ts-msg", thread_id="t", rating="positive", timestamp=ts
        )
        assert entry["timestamp"] == ts


@pytest.mark.asyncio
class TestFeedbackApiEndpoints:
    async def test_submit_feedback_authenticated(self):
        """認証付きで POST /api/feedback が正常に動作する"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-api-1", "thread_id": "thread-1", "rating": "positive"},
                headers=headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    async def test_submit_feedback_negative(self):
        """negative フィードバックが受け付けられる"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-api-2", "thread_id": "t", "rating": "negative"},
                headers=headers,
            )

        assert response.status_code == 201

    async def test_submit_feedback_unauthenticated(self):
        """認証なしで POST /api/feedback が 403 を返す"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-no-auth", "thread_id": "t", "rating": "positive"},
            )

        assert response.status_code in (401, 403)

    async def test_submit_feedback_invalid_token(self):
        """無効なトークンで 403 が返る"""
        headers = {"Authorization": "Bearer invalid.token.here"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-bad-token", "thread_id": "t", "rating": "positive"},
                headers=headers,
            )

        assert response.status_code == 403

    async def test_submit_feedback_invalid_rating(self):
        """不正な rating で 422 が返る"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-bad-rating", "thread_id": "t", "rating": "unknown"},
                headers=headers,
            )

        assert response.status_code == 422

    async def test_submit_feedback_empty_message_id(self):
        """空の message_id で 422 が返る"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "   ", "thread_id": "t", "rating": "positive"},
                headers=headers,
            )

        assert response.status_code == 422

    async def test_submit_feedback_missing_fields(self):
        """必須フィールド欠如で 422 が返る"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/feedback",
                json={"message_id": "msg-missing"},
                headers=headers,
            )

        assert response.status_code == 422
