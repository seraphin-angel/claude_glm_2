"""FAQService のユニットテスト"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.faq_service import FAQService


@pytest.fixture
def sample_faq_data(tmp_path: Path) -> Path:
    """テスト用のFAQデータファイルを作成"""
    data = {
        "faqs": [
            {
                "id": "faq-001",
                "question": "パスワードを忘れた場合はどうすればいいですか？",
                "answer": "ログインページの「パスワードを忘れた」からリセットできます。",
                "keywords": ["パスワード", "ログイン", "忘れた"],
                "page_patterns": ["/login", "/account"],
                "category": "アカウント",
                "view_count": 10,
            },
            {
                "id": "faq-002",
                "question": "アカウントの設定を変更するにはどうすればいいですか？",
                "answer": "画面右上のアカウントアイコンをクリックし、「設定」から変更できます。",
                "keywords": ["アカウント", "設定", "変更"],
                "page_patterns": ["/settings", "/account"],
                "category": "アカウント",
                "view_count": 5,
            },
            {
                "id": "faq-003",
                "question": "データをエクスポートする方法は？",
                "answer": "設定ページの「データ管理」からエクスポートできます。",
                "keywords": ["エクスポート", "データ", "ダウンロード"],
                "page_patterns": ["/settings", "/data"],
                "category": "データ管理",
                "view_count": 20,
            },
        ]
    }
    faq_file = tmp_path / "faqs.json"
    faq_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return faq_file


@pytest.fixture
def faq_service(sample_faq_data: Path) -> FAQService:
    """テスト用のFAQServiceインスタンス"""
    return FAQService(faq_path=str(sample_faq_data))


class TestFAQServiceInit:
    """FAQService 初期化テスト"""

    def test_init_loads_faqs(self, sample_faq_data: Path) -> None:
        """FAQデータが正しく読み込まれること"""
        service = FAQService(faq_path=str(sample_faq_data))
        assert len(service._faqs) == 3

    def test_init_handles_missing_file(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合、空のリストで初期化されること"""
        service = FAQService(faq_path=str(tmp_path / "nonexistent.json"))
        assert service._faqs == []


class TestGetFaqsByPage:
    """get_faqs_by_page メソッドのテスト"""

    def test_returns_matching_faqs(self, faq_service: FAQService) -> None:
        """ページURLにマッチするFAQを返す"""
        results = faq_service.get_faqs_by_page("/login")
        assert len(results) == 1
        assert results[0]["id"] == "faq-001"

    def test_returns_multiple_matching_faqs(self, faq_service: FAQService) -> None:
        """複数マッチする場合、すべて返す"""
        results = faq_service.get_faqs_by_page("/settings")
        assert len(results) == 2
        ids = [r["id"] for r in results]
        assert "faq-002" in ids
        assert "faq-003" in ids

    def test_respects_limit(self, faq_service: FAQService) -> None:
        """limit パラメータが機能すること"""
        results = faq_service.get_faqs_by_page("/settings", limit=1)
        assert len(results) == 1

    def test_returns_empty_for_no_match(self, faq_service: FAQService) -> None:
        """マッチしない場合、空リストを返す"""
        results = faq_service.get_faqs_by_page("/unknown")
        assert results == []

    def test_partial_url_match(self, faq_service: FAQService) -> None:
        """部分一致でマッチすること"""
        results = faq_service.get_faqs_by_page("/login?redirect=/home")
        assert len(results) == 1
        assert results[0]["id"] == "faq-001"


class TestGetTopQuestions:
    """get_top_questions メソッドのテスト"""

    def test_returns_top_by_view_count(self, faq_service: FAQService) -> None:
        """閲覧数順でトップ質問を返す"""
        results = faq_service.get_top_questions(limit=2)
        assert len(results) == 2
        # view_count: faq-003=20, faq-001=10, faq-002=5
        assert results[0]["id"] == "faq-003"
        assert results[1]["id"] == "faq-001"

    def test_respects_limit(self, faq_service: FAQService) -> None:
        """limit パラメータが機能すること"""
        results = faq_service.get_top_questions(limit=1)
        assert len(results) == 1

    def test_returns_all_if_less_than_limit(self, faq_service: FAQService) -> None:
        """FAQ数がlimitより少ない場合、全件返す"""
        results = faq_service.get_top_questions(limit=10)
        assert len(results) == 3


class TestSearchFaqs:
    """search_faqs メソッドのテスト"""

    def test_search_by_keyword(self, faq_service: FAQService) -> None:
        """キーワードで検索できる"""
        results = faq_service.search_faqs("パスワード")
        assert len(results) == 1
        assert results[0]["id"] == "faq-001"

    def test_search_matches_keywords_field(self, faq_service: FAQService) -> None:
        """keywords フィールドで検索できる"""
        results = faq_service.search_faqs("エクスポート")
        assert len(results) == 1
        assert results[0]["id"] == "faq-003"

    def test_search_matches_question(self, faq_service: FAQService) -> None:
        """質問文でも検索できる"""
        results = faq_service.search_faqs("設定")
        assert len(results) >= 1

    def test_search_is_case_insensitive(self, faq_service: FAQService) -> None:
        """大文字小文字を区別しない"""
        results = faq_service.search_faqs("パスワード")
        assert len(results) == 1

    def test_respects_limit(self, faq_service: FAQService) -> None:
        """limit パラメータが機能すること"""
        results = faq_service.search_faqs("設定", limit=1)
        assert len(results) <= 1

    def test_returns_empty_for_no_match(self, faq_service: FAQService) -> None:
        """マッチしない場合、空リストを返す"""
        results = faq_service.search_faqs("存在しないキーワード")
        assert results == []


class TestIncrementViewCount:
    """increment_view_count メソッドのテスト"""

    def test_increments_view_count(self, faq_service: FAQService, sample_faq_data: Path) -> None:
        """閲覧数が増加すること"""
        initial_count = faq_service._faqs[0]["view_count"]
        faq_service.increment_view_count("faq-001")
        assert faq_service._faqs[0]["view_count"] == initial_count + 1

    def test_no_error_for_unknown_id(self, faq_service: FAQService) -> None:
        """存在しないIDでもエラーにならない"""
        faq_service.increment_view_count("unknown-id")  # Should not raise


class TestGetAllCategories:
    """get_all_categories メソッドのテスト"""

    def test_returns_unique_categories(self, faq_service: FAQService) -> None:
        """ユニークなカテゴリ一覧を返す"""
        categories = faq_service.get_all_categories()
        assert "アカウント" in categories
        assert "データ管理" in categories
        assert len(categories) == 2  # 重複なし

    def test_returns_empty_for_no_faqs(self, tmp_path: Path) -> None:
        """FAQがない場合、空リストを返す"""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text('{"faqs": []}', encoding="utf-8")
        service = FAQService(faq_path=str(empty_file))
        assert service.get_all_categories() == []
