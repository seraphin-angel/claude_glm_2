"""Tests for PostgresSaver integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPostgresSaverIntegration:
    """PostgresSaver 統合テスト"""

    def test_settings_database_url_default(self):
        """デフォルトのデータベースURL設定をテスト"""
        from app.config.settings import Settings

        settings = Settings()
        assert "postgresql://" in settings.database_url
        assert "chatbot_user" in settings.database_url
        assert "chatbot_db" in settings.database_url

    def test_settings_database_pool_settings(self):
        """データベースプール設定をテスト"""
        from app.config.settings import Settings

        settings = Settings()
        assert settings.database_pool_size > 0
        assert settings.database_max_overflow >= 0

    @pytest.mark.asyncio
    async def test_get_agent_with_memory_saver_fallback(self):
        """MemorySaver フォールバックをテスト"""
        from app.agents.agent import reset_agent, use_memory_saver, get_agent

        # リセットして MemorySaver モードに設定
        reset_agent()
        use_memory_saver()

        # エージェントを取得
        agent = await get_agent()
        assert agent is not None

        # クリーンアップ
        reset_agent()

    @pytest.mark.asyncio
    async def test_get_agent_memory_saver_mode(self):
        """MemorySaver モードでのエージェント取得をテスト"""
        from app.agents.agent import (
            reset_agent,
            use_memory_saver,
            get_agent,
            get_checkpointer,
        )

        # リセットして MemorySaver モードに設定
        reset_agent()
        use_memory_saver()

        # エージェントを取得
        agent = await get_agent()
        assert agent is not None

        # checkpointer が MemorySaver であることを確認
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = get_checkpointer()
        assert isinstance(checkpointer, MemorySaver)

        # クリーンアップ
        reset_agent()

    @pytest.mark.asyncio
    async def test_postgres_saver_fallback_on_connection_error(self):
        """PostgreSQL 接続エラー時のフォールバックをテスト"""
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        # リセット
        reset_agent()
        use_postgres_saver()

        # PostgresSaver のインポートをモックしてエラーを発生させる
        with patch.dict(
            "sys.modules",
            {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
        ):
            # 無効な接続文字列で PostgresSaver を試行
            with patch(
                "app.config.settings.get_settings"
            ) as mock_settings:
                mock_settings.return_value.database_url = (
                    "postgresql://invalid:invalid@invalid:5432/invalid"
                )

                # エージェントを取得（フォールバックが動作するはず）
                agent = await get_agent()
                assert agent is not None

        # クリーンアップ
        reset_agent()

    def test_use_memory_saver_flag(self):
        """use_memory_saver フラグ設定をテスト"""
        from app.agents.agent import (
            reset_agent,
            use_memory_saver,
            use_postgres_saver,
        )
        import app.agents.agent as agent_module

        # MemorySaver モードに設定
        use_memory_saver()
        assert agent_module._use_postgres is False

        # PostgresSaver モードに設定
        use_postgres_saver()
        assert agent_module._use_postgres is True

        # クリーンアップ
        reset_agent()


class TestPostgresSaverConfiguration:
    """PostgresSaver 設定テスト"""

    def test_docker_compose_postgres_service(self):
        """docker-compose.yml に PostgreSQL サービスが含まれることをテスト"""
        import yaml
        from pathlib import Path

        docker_compose_path = Path("/workspace/agentic-rag-chatbot/docker-compose.yml")
        if docker_compose_path.exists():
            with open(docker_compose_path) as f:
                config = yaml.safe_load(f)

            assert "services" in config
            assert "postgres" in config["services"]

            postgres_service = config["services"]["postgres"]
            assert "5432" in str(postgres_service.get("ports", []))
            assert "POSTGRES_USER" in postgres_service.get("environment", {})
            assert "POSTGRES_PASSWORD" in postgres_service.get("environment", {})
            assert "POSTGRES_DB" in postgres_service.get("environment", {})

    def test_pyproject_postgres_dependencies(self):
        """pyproject.toml に PostgreSQL 依存関係が含まれることをテスト"""
        from pathlib import Path
        import tomllib

        pyproject_path = Path("/workspace/agentic-rag-chatbot/backend/pyproject.toml")
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        dependencies = config.get("project", {}).get("dependencies", [])
        dependency_names = [d.split(">=")[0].split("==")[0].split("<")[0] for d in dependencies]

        assert "asyncpg" in dependency_names
        assert "langgraph-checkpoint-postgres" in dependency_names


@pytest.mark.integration
class TestPostgresSaverLive:
    """PostgresSaver ライブテスト（PostgreSQL コンテナが必要）"""

    @pytest.mark.asyncio
    async def test_postgres_saver_connection(self):
        """実際の PostgreSQL 接続をテスト（統合テスト）"""
        import os

        # PostgreSQL が利用可能な場合のみテスト
        if not os.environ.get("TEST_POSTGRES_URL"):
            pytest.skip("TEST_POSTGRES_URL not set, skipping live test")

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        db_url = os.environ.get("TEST_POSTGRES_URL")

        async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
            await checkpointer.setup()
            # 接続成功
            assert checkpointer is not None

    @pytest.mark.asyncio
    async def test_conversation_persistence(self):
        """会話の永続化をテスト（統合テスト）"""
        import os

        # PostgreSQL が利用可能な場合のみテスト
        if not os.environ.get("TEST_POSTGRES_URL"):
            pytest.skip("TEST_POSTGRES_URL not set, skipping live test")

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import HumanMessage

        db_url = os.environ.get("TEST_POSTGRES_URL")
        test_thread_id = "test-persistence-thread"

        # 最初のエージェントでメッセージを保存
        async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
            await checkpointer.setup()

            # チェックポイントが保存されることを確認
            config = {"configurable": {"thread_id": test_thread_id}}

            # チェックポイントを保存
            from langgraph.checkpoint.base import Checkpoint

            checkpoint = Checkpoint(
                v=1,
                id="test-checkpoint-id",
                ts="2024-01-01T00:00:00Z",
                channel_values={"messages": [HumanMessage(content="test")]},
                channel_versions={},
                versions_seen={},
            )

            await checkpointer.aput(config, checkpoint, {}, {})

        # 新しい接続でチェックポイントを復元
        async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
            restored = await checkpointer.aget(config)
            assert restored is not None
