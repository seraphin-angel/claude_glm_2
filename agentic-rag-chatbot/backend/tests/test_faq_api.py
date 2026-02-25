"""FAQ API エンドポイントのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import create_access_token
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """テストクライアント"""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """認証ヘッダー"""
    token = create_access_token({"sub": "test-user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_faq_service() -> MagicMock:
    """モックされたFAQService"""
    with patch("app.api.faq.faq_service") as mock:
        yield mock


class TestFAQAuthRequired:
    """FAQ エンドポイントの認証必須テスト"""

    def test_suggestions_requires_auth(self, client: TestClient) -> None:
        """認証なしで /api/faq/suggestions にアクセスすると 403"""
        response = client.get("/api/faq/suggestions")
        assert response.status_code == 401

    def test_top_requires_auth(self, client: TestClient) -> None:
        """認証なしで /api/faq/top にアクセスすると 403"""
        response = client.get("/api/faq/top")
        assert response.status_code == 401

    def test_search_requires_auth(self, client: TestClient) -> None:
        """認証なしで /api/faq/search にアクセスすると 403"""
        response = client.get("/api/faq/search?q=test")
        assert response.status_code == 401

    def test_categories_requires_auth(self, client: TestClient) -> None:
        """認証なしで /api/faq/categories にアクセスすると 403"""
        response = client.get("/api/faq/categories")
        assert response.status_code == 401

    def test_click_requires_auth(self, client: TestClient) -> None:
        """認証なしで /api/faq/click にアクセスすると 403"""
        response = client.post("/api/faq/click", json={"faq_id": "faq-001"})
        assert response.status_code == 401

    def test_suggestions_with_auth_succeeds(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """認証ありで /api/faq/suggestions にアクセスすると 200"""
        mock_faq_service.get_faqs_by_page.return_value = []
        response = client.get("/api/faq/suggestions", headers=auth_headers)
        assert response.status_code == 200


class TestFAQSuggestionsEndpoint:
    """GET /api/faq/suggestions エンドポイントのテスト"""

    def test_returns_faqs_for_page(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """ページURLに基づくFAQ推薦を返す"""
        mock_faq_service.get_faqs_by_page.return_value = [
            {
                "id": "faq-001",
                "question": "パスワードを忘れた場合",
                "answer": "リセットしてください",
                "category": "アカウント",
            }
        ]

        response = client.get("/api/faq/suggestions?page_url=/login", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 1
        assert data["faqs"][0]["id"] == "faq-001"
        mock_faq_service.get_faqs_by_page.assert_called_once_with("/login", limit=3)

    def test_uses_default_limit(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """デフォルトのlimit=3が使用される"""
        mock_faq_service.get_faqs_by_page.return_value = []

        client.get("/api/faq/suggestions?page_url=/settings", headers=auth_headers)

        mock_faq_service.get_faqs_by_page.assert_called_once_with("/settings", limit=3)

    def test_respects_custom_limit(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """カスタムlimitが使用される"""
        mock_faq_service.get_faqs_by_page.return_value = []

        client.get("/api/faq/suggestions?page_url=/settings&limit=5", headers=auth_headers)

        mock_faq_service.get_faqs_by_page.assert_called_once_with("/settings", limit=5)

    def test_returns_empty_when_no_match(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """マッチしない場合、空のリストを返す"""
        mock_faq_service.get_faqs_by_page.return_value = []

        response = client.get("/api/faq/suggestions?page_url=/unknown", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["faqs"] == []

    def test_handles_missing_page_url(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """page_urlがない場合、空文字で処理"""
        mock_faq_service.get_faqs_by_page.return_value = []

        response = client.get("/api/faq/suggestions", headers=auth_headers)

        assert response.status_code == 200
        mock_faq_service.get_faqs_by_page.assert_called_once()


class TestFAQTopEndpoint:
    """GET /api/faq/top エンドポイントのテスト"""

    def test_returns_top_faqs(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """トップ質問を返す"""
        mock_faq_service.get_top_questions.return_value = [
            {"id": "faq-001", "question": "Q1", "view_count": 100},
            {"id": "faq-002", "question": "Q2", "view_count": 50},
        ]

        response = client.get("/api/faq/top", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 2
        mock_faq_service.get_top_questions.assert_called_once()

    def test_respects_limit(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """limit パラメータが機能する"""
        mock_faq_service.get_top_questions.return_value = []

        client.get("/api/faq/top?limit=10", headers=auth_headers)

        # デフォルトの引数を確認
        call_args = mock_faq_service.get_top_questions.call_args
        assert call_args[1]["limit"] == 10


class TestFAQSearchEndpoint:
    """GET /api/faq/search エンドポイントのテスト"""

    def test_searches_faqs(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """FAQ検索ができる"""
        mock_faq_service.search_faqs.return_value = [
            {"id": "faq-001", "question": "パスワードのリセット"}
        ]

        response = client.get("/api/faq/search?q=パスワード", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 1
        mock_faq_service.search_faqs.assert_called_once()

    def test_handles_missing_query(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """クエリがない場合、空のリストを返す"""
        response = client.get("/api/faq/search", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["faqs"] == []

    def test_respects_limit(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """limit パラメータが機能する"""
        mock_faq_service.search_faqs.return_value = []

        client.get("/api/faq/search?q=test&limit=3", headers=auth_headers)

        call_args = mock_faq_service.search_faqs.call_args
        assert call_args[1]["limit"] == 3


class TestFAQCategoriesEndpoint:
    """GET /api/faq/categories エンドポイントのテスト"""

    def test_returns_categories(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """カテゴリ一覧を返す"""
        mock_faq_service.get_all_categories.return_value = ["アカウント", "データ管理"]

        response = client.get("/api/faq/categories", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["categories"] == ["アカウント", "データ管理"]


class TestFAQClickEndpoint:
    """POST /api/faq/click エンドポイントのテスト"""

    def test_increments_view_count(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """FAQクリックで閲覧数を増やす"""
        response = client.post("/api/faq/click", json={"faq_id": "faq-001"}, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_faq_service.increment_view_count.assert_called_once_with("faq-001")

    def test_handles_missing_faq_id(
        self, client: TestClient, auth_headers: dict, mock_faq_service: MagicMock
    ) -> None:
        """faq_idがない場合、エラーを返す"""
        response = client.post("/api/faq/click", json={}, headers=auth_headers)

        assert response.status_code == 422  # Validation error


class TestFAQInvalidToken:
    """FAQ エンドポイントの無効トークンテスト"""

    def test_expired_token_returns_403(self, client: TestClient) -> None:
        """期限切れトークンでアクセスすると403"""
        from datetime import timedelta

        # 期限切れトークンを作成（過去の時刻を設定）
        expired_token = create_access_token(
            {"sub": "test-user"},
            expires_delta=timedelta(seconds=-1),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = client.get("/api/faq/suggestions", headers=headers)
        assert response.status_code == 403

    def test_malformed_token_returns_403(self, client: TestClient) -> None:
        """不正なフォーマットのトークンでアクセスすると403"""
        headers = {"Authorization": "Bearer invalid.token.format"}

        response = client.get("/api/faq/suggestions", headers=headers)
        assert response.status_code == 403

    def test_empty_token_returns_401(self, client: TestClient) -> None:
        """空のトークンでアクセスすると401（HTTPBearerの仕様）"""
        headers = {"Authorization": "Bearer "}

        response = client.get("/api/faq/suggestions", headers=headers)
        assert response.status_code == 401

    def test_missing_bearer_prefix_returns_401(self, client: TestClient) -> None:
        """Bearer プレフィックスなしでアクセスすると401（HTTPBearerの仕様）"""
        token = create_access_token({"sub": "test-user"})
        headers = {"Authorization": token}  # "Bearer" なし

        response = client.get("/api/faq/suggestions", headers=headers)
        assert response.status_code == 401
