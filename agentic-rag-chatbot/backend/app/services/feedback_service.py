import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

VALID_RATINGS = ("positive", "negative")


class FeedbackService:
    """フィードバックの記録と集計（インメモリ + ファイル永続化）"""

    _instance = None
    _lock = Lock()

    def __init__(self, persist_path: str = "data/feedback.json"):
        self._feedbacks: list[dict] = []
        self._persist_path = Path(persist_path)
        self._load()

    @classmethod
    def get_instance(cls) -> "FeedbackService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def record_feedback(
        self,
        message_id: str,
        thread_id: str,
        rating: str,
        timestamp: str | None = None,
    ) -> dict:
        """フィードバックを記録する。既存のmessage_idがあれば上書き。"""
        if rating not in VALID_RATINGS:
            raise ValueError(f"rating must be one of {VALID_RATINGS}")

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        entry = {
            "message_id": message_id,
            "thread_id": thread_id,
            "rating": rating,
            "timestamp": ts,
        }
        # 同じ message_id のフィードバックは上書き（immutable: filter + append）
        filtered = [f for f in self._feedbacks if f["message_id"] != message_id]
        self._feedbacks = filtered + [entry]
        self._save()
        return entry

    def get_feedback_summary(self) -> dict:
        """positive / negative の件数を返す。"""
        positive = sum(1 for f in self._feedbacks if f["rating"] == "positive")
        negative = sum(1 for f in self._feedbacks if f["rating"] == "negative")
        return {
            "total": len(self._feedbacks),
            "positive": positive,
            "negative": negative,
        }

    def _load(self):
        try:
            if self._persist_path.exists():
                self._feedbacks = json.loads(
                    self._persist_path.read_text(encoding="utf-8")
                )
        except Exception as e:
            logger.error(
                "Failed to load feedback file",
                exc_info=True,
            )
            self._feedbacks = []

    def _save(self):
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._feedbacks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(
                "Failed to save feedback file",
                exc_info=True,
            )
