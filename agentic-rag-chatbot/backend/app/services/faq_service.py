"""FAQ サービス - FAQ データの管理と推薦"""

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# 直近の会話からキーワードを抽出する件数
RECENT_CONVERSATION_COUNT = 10


class FAQService:
    """FAQ データの管理と推薦を行うサービス"""

    _instance = None
    _lock = Lock()

    def __init__(self, faq_path: str = "data/faqs.json"):
        self._faqs: list[dict[str, Any]] = []
        self._faq_path = Path(faq_path)
        self._load()

    @classmethod
    def get_instance(cls) -> "FAQService":
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンインスタンスをリセット（テスト用）"""
        cls._instance = None

    def _load(self) -> None:
        """FAQ データをファイルから読み込む"""
        try:
            if self._faq_path.exists():
                data = json.loads(self._faq_path.read_text(encoding="utf-8"))
                self._faqs = data.get("faqs", [])
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to load FAQ file (JSON parse error): %s path=%s",
                str(e),
                str(self._faq_path),
            )
            self._faqs = []
        except OSError as e:
            logger.error(
                "Failed to load FAQ file (OS error): %s path=%s",
                str(e),
                str(self._faq_path),
            )
            self._faqs = []
        except Exception as e:
            logger.error(
                "Failed to load FAQ file (unexpected error): %s path=%s",
                str(e),
                str(self._faq_path),
            )
            self._faqs = []

    def _save(self) -> None:
        """FAQ データをファイルに保存"""
        try:
            self._faq_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"faqs": self._faqs}
            self._faq_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save FAQ file: {e}")

    def get_faqs_by_page(self, page_url: str, limit: int = 3) -> list[dict[str, Any]]:
        """
        ページURLに基づいて関連FAQを取得

        Args:
            page_url: 現在のページURL
            limit: 返すFAQの最大数

        Returns:
            関連FAQのリスト
        """
        matching_faqs = []
        for faq in self._faqs:
            patterns = faq.get("page_patterns", [])
            for pattern in patterns:
                # 部分一致でチェック（クエリパラメータを含むURLにも対応）
                if pattern in page_url:
                    matching_faqs.append(faq)
                    break

        return matching_faqs[:limit]

    def get_top_questions(
        self, since_days: int = 7, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        よくある質問を取得（閲覧数順）

        Args:
            since_days: 集計期間（日数）※現在は未使用、将来拡張用
            limit: 返すFAQの最大数

        Returns:
            閲覧数順のFAQリスト
        """
        # 閲覧数でソート（降順）
        sorted_faqs = sorted(
            self._faqs,
            key=lambda f: f.get("view_count", 0),
            reverse=True,
        )
        return sorted_faqs[:limit]

    def search_faqs(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        キーワードでFAQを検索

        Args:
            query: 検索クエリ
            limit: 返すFAQの最大数

        Returns:
            マッチしたFAQのリスト
        """
        query_lower = query.lower()
        matching_faqs = []

        for faq in self._faqs:
            # 質問文、キーワード、回答で検索
            question = faq.get("question", "").lower()
            keywords = [k.lower() for k in faq.get("keywords", [])]
            answer = faq.get("answer", "").lower()

            if (
                query_lower in question
                or query_lower in answer
                or any(query_lower in kw for kw in keywords)
            ):
                matching_faqs.append(faq)

        return matching_faqs[:limit]

    def increment_view_count(self, faq_id: str) -> None:
        """
        FAQ の閲覧数を増やす

        Args:
            faq_id: FAQ ID
        """
        for faq in self._faqs:
            if faq.get("id") == faq_id:
                faq["view_count"] = faq.get("view_count", 0) + 1
                self._save()
                break

    def get_all_categories(self) -> list[str]:
        """
        すべてのカテゴリを取得

        Returns:
            カテゴリのリスト（重複なし）
        """
        categories = set()
        for faq in self._faqs:
            if category := faq.get("category"):
                categories.add(category)
        return sorted(list(categories))

    def get_faq_by_id(self, faq_id: str) -> dict[str, Any] | None:
        """
        ID で FAQ を取得

        Args:
            faq_id: FAQ ID

        Returns:
            FAQ データ、見つからない場合は None
        """
        for faq in self._faqs:
            if faq.get("id") == faq_id:
                return faq
        return None

    def get_personalized_faqs(
        self,
        user_profile,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        ユーザープロファイルに基づいてパーソナライズされたFAQを取得

        Args:
            user_profile: UserProfile オブジェクト
            limit: 返すFAQの最大数

        Returns:
            パーソナライズされたFAQのリスト
        """
        if user_profile is None:
            return self.get_top_questions(limit=limit)

        # ユーザーの関心カテゴリを取得
        preferred_categories = getattr(user_profile, "preferred_categories", [])
        if not preferred_categories:
            return self.get_top_questions(limit=limit)

        # 関心カテゴリにマッチするFAQを優先
        matching_faqs = []
        other_faqs = []

        for faq in self._faqs:
            faq_category = faq.get("category", "")
            if faq_category in preferred_categories:
                matching_faqs.append(faq)
            else:
                other_faqs.append(faq)

        # 閲覧数でソート
        matching_faqs.sort(key=lambda f: f.get("view_count", 0), reverse=True)
        other_faqs.sort(key=lambda f: f.get("view_count", 0), reverse=True)

        # マッチしたFAQを優先して返す
        result = matching_faqs[:limit]
        if len(result) < limit:
            remaining = limit - len(result)
            result.extend(other_faqs[:remaining])

        return result

    def get_recommended_faqs(
        self,
        user_profile,
        page_url: str = "",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        ユーザーの過去の質問パターンと現在のページに基づいてFAQを推薦

        Args:
            user_profile: UserProfile オブジェクト
            page_url: 現在のページURL
            limit: 返すFAQの最大数

        Returns:
            推薦FAQのリスト
        """
        recommendations = []
        seen_ids = set()

        self._add_page_based_faqs(page_url, limit, recommendations, seen_ids)
        self._add_user_interest_faqs(user_profile, recommendations, seen_ids)
        self._fill_with_top_faqs(limit, recommendations, seen_ids)

        return recommendations[:limit]

    def _add_page_based_faqs(
        self,
        page_url: str,
        limit: int,
        recommendations: list[dict[str, Any]],
        seen_ids: set,
    ) -> None:
        """ページURLに基づいてFAQを追加"""
        if not page_url:
            return
        page_faqs = self.get_faqs_by_page(page_url, limit=limit)
        for faq in page_faqs:
            faq_id = faq.get("id")
            if faq_id not in seen_ids:
                faq_copy = {**faq, "_recommendation_reason": "このページに関連する質問"}
                recommendations.append(faq_copy)
                seen_ids.add(faq_id)

    def _add_user_interest_faqs(
        self,
        user_profile,
        recommendations: list[dict[str, Any]],
        seen_ids: set,
    ) -> None:
        """ユーザーの関心カテゴリと過去の質問に基づいてFAQを追加"""
        if not user_profile:
            return

        preferred_categories = getattr(user_profile, "preferred_categories", [])
        conversations = getattr(user_profile, "conversations", [])

        # 過去の質問から頻出キーワードを抽出
        question_keywords = set()
        for conv in conversations[-RECENT_CONVERSATION_COUNT:]:
            question = getattr(conv, "question", "")
            # 簡易的なキーワード抽出（スペース区切り）
            words = question.split()
            for word in words:
                if len(word) >= 2:  # 2文字以上
                    question_keywords.add(word.lower())

        # 関心カテゴリとキーワードに基づくFAQ
        for faq in self._faqs:
            faq_id = faq.get("id")
            if faq_id in seen_ids:
                continue

            faq_category = faq.get("category", "")
            faq_keywords = [k.lower() for k in faq.get("keywords", [])]
            faq_question = faq.get("question", "").lower()

            # カテゴリマッチ
            if faq_category in preferred_categories:
                faq_copy = {**faq, "_recommendation_reason": "あなたの関心分野に関連する質問"}
                recommendations.append(faq_copy)
                seen_ids.add(faq_id)
                continue

            # キーワードマッチ
            for keyword in question_keywords:
                if keyword in faq_question or keyword in faq_keywords:
                    faq_copy = {**faq, "_recommendation_reason": "過去の質問に関連する質問"}
                    recommendations.append(faq_copy)
                    seen_ids.add(faq_id)
                    break

    def _fill_with_top_faqs(
        self,
        limit: int,
        recommendations: list[dict[str, Any]],
        seen_ids: set,
    ) -> None:
        """人気FAQで補完"""
        if len(recommendations) >= limit:
            return
        top_faqs = self.get_top_questions(limit=limit * 2)
        for faq in top_faqs:
            faq_id = faq.get("id")
            if faq_id not in seen_ids:
                faq_copy = {**faq, "_recommendation_reason": "よくある質問"}
                recommendations.append(faq_copy)
                seen_ids.add(faq_id)
                if len(recommendations) >= limit:
                    break
