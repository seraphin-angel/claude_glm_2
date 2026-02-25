"""エスカレーションサービス - 有人サポートへのチケット作成と管理"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

VALID_URGENCIES = ("low", "medium", "high")


class EscalationService:
    """エスカレーションチケットの管理（インメモリ + ファイル永続化）"""

    _instance = None
    _lock = Lock()

    def __init__(self, persist_path: str = "data/escalations.json"):
        self._tickets: list[dict[str, Any]] = []
        self._persist_path = Path(persist_path)
        self._load()

    @classmethod
    def get_instance(cls) -> "EscalationService":
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """シングルトンをリセット（テスト用）"""
        cls._instance = None

    def create_ticket(
        self,
        reason: str,
        urgency: str,
        summary: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """エスカレーションチケットを作成する。

        Args:
            reason: エスカレーションの理由
            urgency: 緊急度 (low, medium, high)
            summary: 会話の要約（空の場合、conversation_historyから自動生成）
            conversation_history: 会話履歴

        Returns:
            作成されたチケット情報

        Raises:
            ValueError: urgencyが無効な場合
        """
        if urgency not in VALID_URGENCIES:
            raise ValueError(f"urgency must be one of {VALID_URGENCIES}")

        # サマリーが空で会話履歴がある場合は自動生成
        if not summary and conversation_history:
            summary = self._generate_summary(conversation_history)
        elif not summary:
            summary = "（詳細なし）"

        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        ticket = {
            "id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "summary": summary,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 新しいチケットを先頭に追加（不変パターン）
        self._tickets = [ticket] + self._tickets
        self._save()

        logger.info(f"Created escalation ticket: {ticket_id}")
        return ticket

    def get_tickets(self, limit: int = 50) -> list[dict[str, Any]]:
        """チケット一覧を取得する。

        Args:
            limit: 取得する最大件数

        Returns:
            チケットのリスト（新しい順）
        """
        return self._tickets[:limit]

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """個別のチケットを取得する。

        Args:
            ticket_id: チケットID

        Returns:
            チケット情報（見つからない場合はNone）
        """
        for ticket in self._tickets:
            if ticket["id"] == ticket_id:
                return ticket
        return None

    def _generate_summary(self, conversation_history: list[dict[str, str]]) -> str:
        """LLMを使用して会話サマリーを生成する。

        Args:
            conversation_history: 会話履歴

        Returns:
            生成されたサマリー
        """
        if not conversation_history:
            return "（会話履歴なし）"

        try:
            from app.agents.llm_factory import get_llm

            # 会話履歴をテキスト形式に変換
            conversation_text = "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in conversation_history
            )

            prompt = f"""以下の会話履歴を要約してください。日本語で簡潔に（2〜3文で）回答してください。

会話履歴:
{conversation_text}

要約:"""

            llm = get_llm(temperature=0.3)
            response = llm.invoke(prompt)
            return response.content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")
            return "（サマリー生成エラー）"

    def _load(self):
        """ファイルからチケットを読み込む"""
        try:
            if self._persist_path.exists():
                self._tickets = json.loads(
                    self._persist_path.read_text(encoding="utf-8")
                )
        except Exception as e:
            logger.warning(f"Failed to load escalations file: {e}")
            self._tickets = []

    def _save(self):
        """チケットをファイルに保存する"""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._tickets, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save escalations file: {e}")
