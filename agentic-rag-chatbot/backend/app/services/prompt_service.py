"""プロンプト管理サービス

システムプロンプトのデータベース管理、バージョン管理、ロールバック機能を提供。
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    """プロンプトのバージョン履歴エントリ"""

    version: int
    content: str
    updated_at: str


@dataclass
class PromptSummary:
    """プロンプト一覧用のサマリー"""

    id: str
    name: str
    version: int
    updated_at: str


@dataclass
class Prompt:
    """プロンプトデータ"""

    id: str
    name: str
    content: str
    version: int
    updated_at: str
    history: list[PromptVersion] = field(default_factory=list)


class PromptService:
    """プロンプト管理サービス（シングルトン + JSON ファイル永続化）"""

    _instance: Optional["PromptService"] = None
    _lock: Lock = Lock()

    def __init__(self, persist_path: Optional[str] = None):
        self._persist_path = Path(
            persist_path or self._get_default_data_path()
        )
        self._data: dict = {"prompts": {}}
        self._load()

    @classmethod
    def get_instance(cls) -> "PromptService":
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

    def _get_default_data_path(self) -> Path:
        """デフォルトのデータファイルパスを取得"""
        return Path(__file__).parent.parent.parent / "data" / "prompts.json"

    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """指定IDのプロンプトを取得

        Args:
            prompt_id: プロンプトID

        Returns:
            プロンプト（存在しない場合はNone）
        """
        prompt_data = self._data.get("prompts", {}).get(prompt_id)
        if prompt_data is None:
            return None

        history = [
            PromptVersion(
                version=h.get("version", 0),
                content=h.get("content", ""),
                updated_at=h.get("updated_at", ""),
            )
            for h in prompt_data.get("history", [])
        ]

        return Prompt(
            id=prompt_data.get("id", prompt_id),
            name=prompt_data.get("name", ""),
            content=prompt_data.get("content", ""),
            version=prompt_data.get("version", 1),
            updated_at=prompt_data.get("updated_at", ""),
            history=history,
        )

    def get_all_prompts(self) -> list[PromptSummary]:
        """全プロンプトの一覧を取得

        Returns:
            プロンプトサマリーのリスト
        """
        prompts = []
        for prompt_id, prompt_data in self._data.get("prompts", {}).items():
            prompts.append(
                PromptSummary(
                    id=prompt_id,
                    name=prompt_data.get("name", ""),
                    version=prompt_data.get("version", 1),
                    updated_at=prompt_data.get("updated_at", ""),
                )
            )
        return prompts

    def update_prompt(self, prompt_id: str, content: str) -> Prompt:
        """プロンプトを更新

        Args:
            prompt_id: プロンプトID
            content: 新しいコンテンツ

        Returns:
            更新後のプロンプト

        Raises:
            ValueError: プロンプトが存在しない場合
            IOError: 保存に失敗した場合
        """
        prompts = self._data.get("prompts", {})
        prompt_data = prompts.get(prompt_id)

        if prompt_data is None:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # 履歴に現在の状態を保存（不変性を保つため新しいリストを作成）
        current_history = list(prompt_data.get("history", []))
        new_history_entry = {
            "version": prompt_data.get("version", 1),
            "content": prompt_data.get("content", ""),
            "updated_at": prompt_data.get("updated_at", ""),
        }
        updated_history = current_history + [new_history_entry]

        # 新しいプロンプトデータを作成（不変性）
        now = datetime.now(timezone.utc).isoformat()
        new_prompt_data = {
            **prompt_data,
            "content": content,
            "version": prompt_data.get("version", 1) + 1,
            "updated_at": now,
            "history": updated_history,
        }

        # データを更新（不変性を保つため新しい辞書を作成）
        self._data = {
            "prompts": {
                **prompts,
                prompt_id: new_prompt_data,
            }
        }

        self._save()

        return self.get_prompt(prompt_id)  # type: ignore

    def rollback_prompt(self, prompt_id: str, version: int) -> Prompt:
        """プロンプトを指定バージョンにロールバック

        Args:
            prompt_id: プロンプトID
            version: ロールバック先のバージョン

        Returns:
            ロールバック後のプロンプト

        Raises:
            ValueError: プロンプトまたはバージョンが存在しない場合
            IOError: 保存に失敗した場合
        """
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # 指定バージョンを履歴から探す
        target_entry = None
        for h in prompt.history:
            if h.version == version:
                target_entry = h
                break

        if target_entry is None:
            raise ValueError(f"Version {version} not found in history")

        # 現在の状態を履歴に追加して、指定バージョンの内容に戻す
        prompts = self._data.get("prompts", {})
        prompt_data = prompts.get(prompt_id, {})

        current_history = list(prompt_data.get("history", []))
        current_entry = {
            "version": prompt_data.get("version", 1),
            "content": prompt_data.get("content", ""),
            "updated_at": prompt_data.get("updated_at", ""),
        }

        now = datetime.now(timezone.utc).isoformat()
        new_prompt_data = {
            **prompt_data,
            "content": target_entry.content,
            "version": prompt_data.get("version", 1) + 1,
            "updated_at": now,
            "history": current_history + [current_entry],
        }

        self._data = {
            "prompts": {
                **prompts,
                prompt_id: new_prompt_data,
            }
        }

        self._save()

        return self.get_prompt(prompt_id)  # type: ignore

    def get_prompt_history(self, prompt_id: str) -> list[PromptVersion]:
        """プロンプトの履歴を取得

        Args:
            prompt_id: プロンプトID

        Returns:
            バージョン履歴のリスト
        """
        prompt = self.get_prompt(prompt_id)
        if prompt is None:
            return []
        return prompt.history

    def _load(self) -> None:
        """データをファイルから読み込み"""
        try:
            if self._persist_path.exists():
                self._data = json.loads(
                    self._persist_path.read_text(encoding="utf-8")
                )
            else:
                logger.warning(
                    f"Prompts file not found: {self._persist_path}. "
                    "Using empty data."
                )
                self._data = {"prompts": {}}
        except Exception as e:
            logger.error(
                "Failed to load prompts file",
                exc_info=True,
            )
            self._data = {"prompts": {}}

    def _save(self) -> None:
        """データをファイルに保存

        Raises:
            IOError: 保存に失敗した場合。呼び出し元で適切にハンドリングすること。
        """
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(
                f"Failed to save prompts file - DATA LOSS RISK: "
                f"path={self._persist_path}, error={e}",
                exc_info=True,
            )
            raise IOError(f"Failed to save prompt data: {e}") from e
