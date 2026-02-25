"""PromptService のユニットテスト"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.services.prompt_service import PromptService, Prompt, PromptSummary, PromptVersion


@pytest.fixture
def sample_prompts_data():
    """テスト用のサンプルプロンプトデータ"""
    return {
        "prompts": {
            "system": {
                "id": "system",
                "name": "システムプロンプト",
                "content": "あなたは製品サポートAIアシスタントです。",
                "version": 1,
                "updated_at": "2026-02-25T10:00:00Z",
                "history": []
            },
            "category_troubleshooting": {
                "id": "category_troubleshooting",
                "name": "障害・トラブル対応プロンプト",
                "content": "トラブルシューティング用のプロンプトです。",
                "version": 2,
                "updated_at": "2026-02-25T11:00:00Z",
                "history": [
                    {
                        "version": 1,
                        "content": "初期版のトラブルシューティングプロンプト",
                        "updated_at": "2026-02-24T10:00:00Z"
                    }
                ]
            }
        }
    }


@pytest.fixture
def temp_prompts_file(tmp_path, sample_prompts_data):
    """一時的なプロンプトファイルを作成"""
    data_file = tmp_path / "prompts.json"
    data_file.write_text(json.dumps(sample_prompts_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_file


@pytest.fixture
def prompt_service(temp_prompts_file):
    """テスト用のPromptServiceインスタンス"""
    PromptService.reset_instance()
    with patch.object(PromptService, "_get_default_data_path", return_value=temp_prompts_file):
        service = PromptService.get_instance()
        yield service
    PromptService.reset_instance()


class TestPromptServiceGetPrompt:
    """get_prompt メソッドのテスト"""

    def test_get_prompt_existing(self, prompt_service):
        """存在するプロンプトを取得できる"""
        prompt = prompt_service.get_prompt("system")

        assert isinstance(prompt, Prompt)
        assert prompt.id == "system"
        assert prompt.name == "システムプロンプト"
        assert prompt.content == "あなたは製品サポートAIアシスタントです。"
        assert prompt.version == 1

    def test_get_prompt_not_found(self, prompt_service):
        """存在しないプロンプトはNoneを返す"""
        prompt = prompt_service.get_prompt("nonexistent")

        assert prompt is None

    def test_get_prompt_with_history(self, prompt_service):
        """履歴があるプロンプトも正しく取得できる"""
        prompt = prompt_service.get_prompt("category_troubleshooting")

        assert prompt.version == 2
        assert len(prompt.history) == 1
        assert prompt.history[0].version == 1


class TestPromptServiceGetAllPrompts:
    """get_all_prompts メソッドのテスト"""

    def test_get_all_prompts(self, prompt_service):
        """全プロンプトの一覧を取得できる"""
        prompts = prompt_service.get_all_prompts()

        assert len(prompts) == 2
        assert all(isinstance(p, PromptSummary) for p in prompts)
        ids = [p.id for p in prompts]
        assert "system" in ids
        assert "category_troubleshooting" in ids

    def test_get_all_prompts_summary_fields(self, prompt_service):
        """一覧には必要なフィールドが含まれる"""
        prompts = prompt_service.get_all_prompts()
        system_prompt = next(p for p in prompts if p.id == "system")

        assert system_prompt.name == "システムプロンプト"
        assert system_prompt.version == 1
        assert hasattr(system_prompt, "updated_at")


class TestPromptServiceUpdatePrompt:
    """update_prompt メソッドのテスト"""

    def test_update_prompt_increments_version(self, prompt_service):
        """プロンプト更新時にバージョンがインクリメントされる"""
        original = prompt_service.get_prompt("system")
        assert original.version == 1

        updated = prompt_service.update_prompt("system", "新しいコンテンツ")

        assert updated.version == 2
        assert updated.content == "新しいコンテンツ"

    def test_update_prompt_saves_history(self, prompt_service):
        """プロンプト更新時に履歴が保存される"""
        original = prompt_service.get_prompt("system")
        original_content = original.content

        prompt_service.update_prompt("system", "新しいコンテンツ")

        updated = prompt_service.get_prompt("system")
        assert len(updated.history) == 1
        assert updated.history[0].version == 1
        assert updated.history[0].content == original_content

    def test_update_prompt_updates_timestamp(self, prompt_service):
        """プロンプト更新時にタイムスタンプが更新される"""
        with patch("app.services.prompt_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.timezone = timezone

            updated = prompt_service.update_prompt("system", "新しいコンテンツ")

            assert "2026-02-26" in updated.updated_at

    def test_update_nonexistent_prompt_raises_error(self, prompt_service):
        """存在しないプロンプトの更新はエラーになる"""
        with pytest.raises(ValueError, match="not found"):
            prompt_service.update_prompt("nonexistent", "コンテンツ")


class TestPromptServiceRollback:
    """rollback_prompt メソッドのテスト"""

    def test_rollback_prompt(self, prompt_service):
        """指定バージョンにロールバックできる"""
        # まず更新して履歴を作る
        prompt_service.update_prompt("system", "バージョン2のコンテンツ")

        # バージョン1にロールバック
        rolled_back = prompt_service.rollback_prompt("system", 1)

        assert rolled_back.content == "あなたは製品サポートAIアシスタントです。"
        # ロールバック後は新しいバージョンになる
        assert rolled_back.version == 3

    def test_rollback_to_nonexistent_version_raises_error(self, prompt_service):
        """存在しないバージョンへのロールバックはエラーになる"""
        with pytest.raises(ValueError, match="Version .* not found"):
            prompt_service.rollback_prompt("system", 99)

    def test_rollback_nonexistent_prompt_raises_error(self, prompt_service):
        """存在しないプロンプトのロールバックはエラーになる"""
        with pytest.raises(ValueError, match="not found"):
            prompt_service.rollback_prompt("nonexistent", 1)


class TestPromptServiceGetHistory:
    """get_prompt_history メソッドのテスト"""

    def test_get_prompt_history(self, prompt_service):
        """プロンプトの履歴を取得できる"""
        history = prompt_service.get_prompt_history("category_troubleshooting")

        assert len(history) == 1
        assert history[0].version == 1

    def test_get_prompt_history_empty(self, prompt_service):
        """履歴がない場合は空リストを返す"""
        history = prompt_service.get_prompt_history("system")

        assert history == []

    def test_get_prompt_history_nonexistent(self, prompt_service):
        """存在しないプロンプトの履歴は空リストを返す"""
        history = prompt_service.get_prompt_history("nonexistent")

        assert history == []


class TestPromptServicePersistence:
    """永続化のテスト"""

    def test_persistence_on_update(self, temp_prompts_file):
        """更新がファイルに永続化される"""
        PromptService.reset_instance()
        with patch.object(PromptService, "_get_default_data_path", return_value=temp_prompts_file):
            service1 = PromptService.get_instance()
            service1.update_prompt("system", "永続化テスト")

            # 新しいインスタンスで確認
            PromptService.reset_instance()
            service2 = PromptService.get_instance()
            prompt = service2.get_prompt("system")

            assert prompt.content == "永続化テスト"

        PromptService.reset_instance()

    def test_singleton_pattern(self, temp_prompts_file):
        """シングルトンパターンが機能する"""
        PromptService.reset_instance()
        with patch.object(PromptService, "_get_default_data_path", return_value=temp_prompts_file):
            instance1 = PromptService.get_instance()
            instance2 = PromptService.get_instance()

            assert instance1 is instance2

        PromptService.reset_instance()
