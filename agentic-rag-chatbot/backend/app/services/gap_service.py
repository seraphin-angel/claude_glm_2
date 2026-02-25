import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class KnowledgeGapService:
    """ナレッジギャップの記録と集計（インメモリ + ファイル永続化）"""

    _instance = None
    _lock = Lock()

    def __init__(self, persist_path: str = "data/knowledge_gaps.json"):
        self._gaps: list[dict] = []
        self._persist_path = Path(persist_path)
        self._load()

    @classmethod
    def get_instance(cls) -> "KnowledgeGapService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def record_gap(self, query: str, category: str = "", reason: str = ""):
        """ナレッジギャップを記録"""
        gap = {
            "query": query,
            "category": category,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._gaps = self._gaps + [gap]
        self._save()

    def get_gaps(self, limit: int = 50) -> list[dict]:
        """ギャップ一覧を取得（新しい順）"""
        sorted_gaps = sorted(self._gaps, key=lambda g: g["timestamp"], reverse=True)
        return sorted_gaps[:limit]

    def get_summary(self) -> dict:
        """ギャップの集計サマリー"""
        total = len(self._gaps)
        by_category: dict[str, int] = {}
        for gap in self._gaps:
            cat = gap.get("category", "不明")
            by_category[cat] = by_category.get(cat, 0) + 1
        return {"total": total, "by_category": by_category}

    def _load(self):
        try:
            if self._persist_path.exists():
                self._gaps = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(
                "Failed to load knowledge gaps file",
                exc_info=True,
            )
            self._gaps = []

    def _save(self):
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._gaps, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(
                "Failed to save knowledge gaps file",
                exc_info=True,
            )
