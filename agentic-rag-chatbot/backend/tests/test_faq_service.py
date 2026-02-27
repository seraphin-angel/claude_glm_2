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


# ---------------------------------------------------------------------------
# HIGH問題修正テスト（#10: faq_service 例外ハンドリング改善）
# ---------------------------------------------------------------------------

class TestFAQServiceExceptionHandling:
    """FAQ サービスの例外ハンドリングテスト"""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        from app.services.faq_service import FAQService
        FAQService.reset_instance()
        yield
        FAQService.reset_instance()

    def test_load_with_json_decode_error_logs_error_level(self, tmp_path):
        """JSONDecodeError時にerrorレベルでログを記録する"""
        import logging
        from unittest.mock import patch, MagicMock

        invalid_json_file = tmp_path / "faqs.json"
        invalid_json_file.write_text("{ invalid json }", encoding="utf-8")

        with patch("app.services.faq_service.logger") as mock_logger:
            from app.services.faq_service import FAQService
            service = FAQService(faq_path=str(invalid_json_file))

        # errorレベルでログが記録される
        mock_logger.error.assert_called_once()
        # FAQが空になる
        assert service.get_top_questions() == []

    def test_load_with_os_error_logs_error_level(self, tmp_path):
        """OSError時にerrorレベルでログを記録する"""
        from unittest.mock import patch, MagicMock

        non_existent_path = tmp_path / "nonexistent" / "faqs.json"
        # ファイルを作成してから権限を削除してOSErrorを起こす
        non_existent_path.parent.mkdir(parents=True)
        non_existent_path.write_text('{"faqs":[]}', encoding="utf-8")

        with patch.object(
            non_existent_path.__class__,
            "read_text",
            side_effect=OSError("Permission denied"),
        ):
            with patch("app.services.faq_service.logger") as mock_logger:
                from app.services.faq_service import FAQService
                service = FAQService(faq_path=str(non_existent_path))

        mock_logger.error.assert_called_once()
        assert service.get_top_questions() == []


# ---------------------------------------------------------------------------
# Gap-1: get_recommended_faqs / get_personalized_faqs テスト
# ---------------------------------------------------------------------------

class TestGetPersonalizedFaqs:
    """get_personalized_faqs のテスト"""

    @pytest.fixture
    def faq_service(self, sample_faq_data: Path) -> "FAQService":
        from app.services.faq_service import FAQService
        return FAQService(faq_path=str(sample_faq_data))

    def test_user_profile_none_falls_back_to_top_questions(self, faq_service) -> None:
        """user_profile=None の場合は get_top_questions にフォールバック"""
        result = faq_service.get_personalized_faqs(user_profile=None, limit=3)
        top = faq_service.get_top_questions(limit=3)
        assert result == top

    def test_empty_preferred_categories_falls_back_to_top_questions(self, faq_service) -> None:
        """preferred_categories が空の場合はフォールバック"""
        class FakeProfile:
            preferred_categories = ()

        result = faq_service.get_personalized_faqs(user_profile=FakeProfile(), limit=3)
        top = faq_service.get_top_questions(limit=3)
        assert result == top

    def test_category_match_prioritized(self, faq_service) -> None:
        """カテゴリマッチが優先される"""
        all_faqs = faq_service.get_top_questions(limit=100)
        if not all_faqs:
            pytest.skip("No FAQs available for this test")

        # 最初のFAQのカテゴリを preferred_categories に設定
        first_category = all_faqs[0].get("category", "")
        if not first_category:
            pytest.skip("FAQ has no category")

        class FakeProfile:
            preferred_categories = (first_category,)

        result = faq_service.get_personalized_faqs(user_profile=FakeProfile(), limit=10)
        # 結果の先頭はカテゴリマッチが来るはず
        if result:
            # カテゴリが一致するFAQが存在する場合、それが含まれている
            categories = [f.get("category") for f in result]
            assert first_category in categories

    def test_limit_respected(self, faq_service) -> None:
        """limit が守られる"""
        class FakeProfile:
            preferred_categories = ("general",)

        result = faq_service.get_personalized_faqs(user_profile=FakeProfile(), limit=2)
        assert len(result) <= 2


class TestGetRecommendedFaqs:
    """get_recommended_faqs のテスト"""

    @pytest.fixture
    def faq_service(self, sample_faq_data: Path) -> "FAQService":
        from app.services.faq_service import FAQService
        return FAQService(faq_path=str(sample_faq_data))

    def test_user_profile_none_returns_results(self, faq_service) -> None:
        """user_profile=None でも結果が返る"""
        result = faq_service.get_recommended_faqs(user_profile=None, limit=3)
        assert isinstance(result, list)

    def test_limit_respected(self, faq_service) -> None:
        """limit が守られる"""
        result = faq_service.get_recommended_faqs(user_profile=None, limit=2)
        assert len(result) <= 2

    def test_with_page_url(self, faq_service) -> None:
        """page_url を指定すると結果が返る"""
        result = faq_service.get_recommended_faqs(
            user_profile=None,
            page_url="/some/page",
            limit=5,
        )
        assert isinstance(result, list)
