"""ガードレールサービス - 入出力の安全性チェックとトピックスコープ管理"""

import logging
from typing import Any

from app.agents.tools.content_safety import check_input_safety, check_output_safety
from app.models.guardrails import RiskLevel, SafetyCheckResult, ViolationType

logger = logging.getLogger(__name__)

# デフォルトの許可トピック
DEFAULT_ALLOWED_TOPICS = [
    "操作方法",
    "障害・トラブル",
    "契約・料金",
    "製品仕様",
    "その他",
]


class GuardrailsService:
    """ガードレールチェックのビジネスロジック"""

    _instance = None

    def __init__(self, allowed_topics: list[str] | None = None):
        """ガードレールサービスを初期化

        Args:
            allowed_topics: 許可するトピックのリスト（None の場合はデフォルト）
        """
        self._allowed_topics = allowed_topics or DEFAULT_ALLOWED_TOPICS

    @classmethod
    def get_instance(cls) -> "GuardrailsService":
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """シングルトンをリセット（テスト用）"""
        cls._instance = None

    def check_input(
        self,
        content: str,
        category: str | None = None,
    ) -> dict[str, Any]:
        """入力コンテンツの安全性をチェック

        Args:
            content: チェックする入力コンテンツ
            category: 分類カテゴリ（トピックスコープ外チェック用）

        Returns:
            SafetyCheckResult を辞書形式で返す
        """
        # ContentSafetyTool で基本チェック
        result = check_input_safety.invoke({"content": content})

        # トピックスコープ外チェック
        if category and category == "out_of_scope":
            violations = list(result.get("violations", []))
            violation_types = list(result.get("violation_types", []))
            
            violations.append("トピックスコープ外の質問です")
            violation_types.append(ViolationType.OUT_OF_SCOPE)

            result = {
                "is_safe": False,
                "risk_level": RiskLevel.MEDIUM.value,
                "violations": violations,
                "violation_types": violation_types,
                "sanitized_content": result.get("sanitized_content"),
                "confidence": result.get("confidence", 0.9),
            }

        return result

    def check_output(self, content: str) -> dict[str, Any]:
        """出力コンテンツの安全性をチェック

        Args:
            content: チェックする出力コンテンツ

        Returns:
            SafetyCheckResult を辞書形式で返す
        """
        return check_output_safety.invoke({"content": content})

    def sanitize_content(self, content: str, violations: list[str]) -> str:
        """コンテンツをサニタイズ

        Args:
            content: サニタイズするコンテンツ
            violations: 検出された違反リスト

        Returns:
            サニタイズ済みコンテンツ
        """
        # 出力チェックを実行してサニタイズ済みコンテンツを取得
        result = check_output_safety.invoke({"content": content})
        
        if result.get("sanitized_content"):
            return result["sanitized_content"]
        
        return content

    def is_topic_allowed(self, category: str) -> bool:
        """トピックが許可されているかチェック

        Args:
            category: カテゴリ

        Returns:
            許可されている場合は True
        """
        return category in self._allowed_topics

    @property
    def allowed_topics(self) -> list[str]:
        """許可トピック一覧を取得"""
        return list(self._allowed_topics)
