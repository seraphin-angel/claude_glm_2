"""FAQ API エンドポイントのテスト"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """テストクライアント"""
    return TestClient(app)


@pytest.fixture
def mock_faq_service() -> MagicMock:
    """モックされたFAQService"""
    with patch("app.api.faq.faq_service") as mock:
        yield mock


class TestFAQSuggestionsEndpoint:
    """GET /api/faq/suggestions エンドポイントのテスト"""

    def test_returns_faqs_for_page(
        self, client: TestClient, mock_faq_service: MagicMock
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

        response = client.get("/api/faq/suggestions?page_url=/login")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 1
        assert data["faqs"][0]["id"] == "faq-001"
        mock_faq_service.get_faqs_by_page.assert_called_once_with("/login", limit=3)

    def test_uses_default_limit(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """デフォルトのlimit=3が使用される"""
        mock_faq_service.get_faqs_by_page.return_value = []

        client.get("/api/faq/suggestions?page_url=/settings")

        mock_faq_service.get_faqs_by_page.assert_called_once_with("/settings", limit=3)

    def test_respects_custom_limit(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """カスタムlimitが使用される"""
        mock_faq_service.get_faqs_by_page.return_value = []

        client.get("/api/faq/suggestions?page_url=/settings&limit=5")

        mock_faq_service.get_faqs_by_page.assert_called_once_with("/settings", limit=5)

    def test_returns_empty_when_no_match(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """マッチしない場合、空のリストを返す"""
        mock_faq_service.get_faqs_by_page.return_value = []

        response = client.get("/api/faq/suggestions?page_url=/unknown")

        assert response.status_code == 200
        data = response.json()
        assert data["faqs"] == []

    def test_handles_missing_page_url(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """page_urlがない場合、空文字で処理"""
        mock_faq_service.get_faqs_by_page.return_value = []

        response = client.get("/api/faq/suggestions")

        assert response.status_code == 200
        mock_faq_service.get_faqs_by_page.assert_called_once()


class TestFAQTopEndpoint:
    """GET /api/faq/top エンドポイントのテスト"""

    def test_returns_top_faqs(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """トップ質問を返す"""
        mock_faq_service.get_top_questions.return_value = [
            {"id": "faq-001", "question": "Q1", "view_count": 100},
            {"id": "faq-002", "question": "Q2", "view_count": 50},
        ]

        response = client.get("/api/faq/top")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 2
        mock_faq_service.get_top_questions.assert_called_once()

    def test_respects_limit(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """limit パラメータが機能する"""
        mock_faq_service.get_top_questions.return_value = []

        client.get("/api/faq/top?limit=10")

        # デフォルトの引数を確認
        call_args = mock_faq_service.get_top_questions.call_args
        assert call_args[1]["limit"] == 10


class TestFAQSearchEndpoint:
    """GET /api/faq/search エンドポイントのテスト"""

    def test_searches_faqs(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """FAQ検索ができる"""
        mock_faq_service.search_faqs.return_value = [
            {"id": "faq-001", "question": "パスワードのリセット"}
        ]

        response = client.get("/api/faq/search?q=パスワード")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["faqs"]) == 1
        mock_faq_service.search_faqs.assert_called_once()

    def test_handles_missing_query(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """クエリがない場合、空のリストを返す"""
        response = client.get("/api/faq/search")

        assert response.status_code == 200
        data = response.json()
        assert data["faqs"] == []

    def test_respects_limit(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """limit パラメータが機能する"""
        mock_faq_service.search_faqs.return_value = []

        client.get("/api/faq/search?q=test&limit=3")

        call_args = mock_faq_service.search_faqs.call_args
        assert call_args[1]["limit"] == 3


class TestFAQCategoriesEndpoint:
    """GET /api/faq/categories エンドポイントのテスト"""

    def test_returns_categories(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """カテゴリ一覧を返す"""
        mock_faq_service.get_all_categories.return_value = ["アカウント", "データ管理"]

        response = client.get("/api/faq/categories")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["categories"] == ["アカウント", "データ管理"]


class TestFAQClickEndpoint:
    """POST /api/faq/click エンドポイントのテスト"""

    def test_increments_view_count(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """FAQクリックで閲覧数を増やす"""
        response = client.post("/api/faq/click", json={"faq_id": "faq-001"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_faq_service.increment_view_count.assert_called_once_with("faq-001")

    def test_handles_missing_faq_id(
        self, client: TestClient, mock_faq_service: MagicMock
    ) -> None:
        """faq_idがない場合、エラーを返す"""
        response = client.post("/api/faq/click", json={})

        assert response.status_code == 422  # Validation error
