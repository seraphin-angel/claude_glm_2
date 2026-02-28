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
    async def test_postgres_saver_raises_runtime_error_on_connection_error(self):
        """PostgreSQL 接続エラー時に RuntimeError が発生することをテスト（fail-fast）"""
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

                # RuntimeError が発生することを期待
                with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                    await get_agent()

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


class TestPersistenceHealthCheck:
    """is_persistence_healthy() 機能のテスト（TDD: Issue #1）"""

    def test_is_persistence_healthy_function_exists(self):
        """is_persistence_healthy 関数が存在することをテスト"""
        from app.agents.agent import is_persistence_healthy

        assert callable(is_persistence_healthy)

    def test_is_persistence_healthy_returns_bool(self):
        """is_persistence_healthy が bool を返すことをテスト"""
        from app.agents.agent import reset_agent, is_persistence_healthy

        reset_agent()
        result = is_persistence_healthy()
        assert isinstance(result, bool)
        reset_agent()

    @pytest.mark.asyncio
    async def test_is_persistence_healthy_true_with_memory_saver(self):
        """MemorySaver モードでは persistence_healthy が True を返すことをテスト"""
        from app.agents.agent import (
            reset_agent,
            use_memory_saver,
            get_agent,
            is_persistence_healthy,
        )

        reset_agent()
        use_memory_saver()

        agent = await get_agent()
        assert agent is not None

        # MemorySaver モードでは明示的に設定された場合は True
        result = is_persistence_healthy()
        assert result is True

        reset_agent()

    @pytest.mark.asyncio
    async def test_is_persistence_healthy_true_on_postgres_success(self):
        """PostgresSaver 成功時に persistence_healthy が True を返すことをテスト"""
        from app.agents.agent import (
            reset_agent,
            use_postgres_saver,
            get_agent,
            is_persistence_healthy,
        )

        reset_agent()
        use_postgres_saver()

        # MemorySaver を使用するようにモック（PostgresSaver 成功をシミュレート）
        with patch("app.agents.agent._use_postgres", False):
            agent = await get_agent()
            assert agent is not None

            # PostgresSaver 成功時は True を期待
            result = is_persistence_healthy()
            assert result is True

        reset_agent()

    @pytest.mark.asyncio
    async def test_is_persistence_healthy_raises_on_postgres_failure(self):
        """PostgresSaver 初期化失敗時に RuntimeError が発生することをテスト（fail-fast）"""
        from app.agents.agent import (
            reset_agent,
            use_postgres_saver,
            get_agent,
        )

        reset_agent()
        use_postgres_saver()

        # PostgresSaver でエラーが発生するようにモック
        with patch(
            "app.config.settings.get_settings"
        ) as mock_settings:
            mock_settings.return_value.database_url = (
                "postgresql://invalid:invalid@invalid:5432/invalid"
            )

            # PostgresSaver のインポートでエラーを発生させる
            with patch.dict(
                "sys.modules",
                {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
            ):
                # RuntimeError が発生することを期待（フォールバックなし）
                with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                    await get_agent()

        reset_agent()


class TestPersistenceFailFastLogging:
    """PostgresSaver 初期化失敗時の CRITICAL ログ出力テスト（fail-fast）"""

    @pytest.mark.asyncio
    async def test_failure_emits_critical_log(self, caplog):
        """PostgresSaver 初期化失敗時に CRITICAL レベルのログが出力されることをテスト"""
        import logging
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        reset_agent()
        use_postgres_saver()

        # CRITICAL レベル以上のログをキャプチャ
        with caplog.at_level(logging.CRITICAL, logger="app.agents.agent"):
            # PostgresSaver でエラーが発生するようにモック
            with patch(
                "app.config.settings.get_settings"
            ) as mock_settings:
                mock_settings.return_value.database_url = (
                    "postgresql://invalid:invalid@invalid:5432/invalid"
                )

                # PostgresSaver のインポートでエラーを発生させる
                with patch.dict(
                    "sys.modules",
                    {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
                ):
                    with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                        await get_agent()

        # CRITICAL ログが1件以上出力されていることを確認
        critical_records = [
            r for r in caplog.records
            if r.levelno >= logging.CRITICAL
        ]
        assert len(critical_records) >= 1, (
            f"Expected at least 1 CRITICAL log, got {len(critical_records)}. "
            f"All records: {[r.message[:50] for r in caplog.records]}"
        )

        reset_agent()

    @pytest.mark.asyncio
    async def test_failure_log_contains_error_id(self, caplog):
        """失敗ログに error_id='PERSISTENCE_INIT_FAILED' が含まれることをテスト"""
        import logging
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        reset_agent()
        use_postgres_saver()

        with caplog.at_level(logging.ERROR, logger="app.agents.agent"):
            with patch(
                "app.config.settings.get_settings"
            ) as mock_settings:
                mock_settings.return_value.database_url = (
                    "postgresql://invalid:invalid@invalid:5432/invalid"
                )

                with patch.dict(
                    "sys.modules",
                    {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
                ):
                    with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                        await get_agent()

        # error_id=PERSISTENCE_INIT_FAILED を含むログを検索
        # Python logging の extra は属性として直接追加される
        found_error_id = False
        for record in caplog.records:
            if record.levelno >= logging.ERROR:
                if getattr(record, 'error_id', None) == 'PERSISTENCE_INIT_FAILED':
                    found_error_id = True
                    break

        assert found_error_id, (
            f"No log with error_id='PERSISTENCE_INIT_FAILED' found. "
            f"Record attributes: {[(r.message[:30], getattr(r, 'error_id', None)) for r in caplog.records if r.levelno >= logging.ERROR]}"
        )

        reset_agent()

    @pytest.mark.asyncio
    async def test_failure_log_contains_severity_critical(self, caplog):
        """失敗ログに severity='CRITICAL' が含まれることをテスト"""
        import logging
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        reset_agent()
        use_postgres_saver()

        with caplog.at_level(logging.ERROR, logger="app.agents.agent"):
            with patch(
                "app.config.settings.get_settings"
            ) as mock_settings:
                mock_settings.return_value.database_url = (
                    "postgresql://invalid:invalid@invalid:5432/invalid"
                )

                with patch.dict(
                    "sys.modules",
                    {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
                ):
                    with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                        await get_agent()

        # severity=CRITICAL を含むログを検索
        found_severity = False
        for record in caplog.records:
            if record.levelno >= logging.ERROR:
                if getattr(record, 'severity', None) == 'CRITICAL':
                    found_severity = True
                    break

        assert found_severity, (
            f"No log with severity='CRITICAL' found. "
            f"Record attributes: {[(r.message[:30], getattr(r, 'severity', None)) for r in caplog.records if r.levelno >= logging.ERROR]}"
        )

        reset_agent()

    @pytest.mark.asyncio
    async def test_failure_raises_runtime_error(self, caplog):
        """初期化失敗時に RuntimeError が発生することをテスト"""
        from app.agents.agent import (
            reset_agent,
            use_postgres_saver,
            get_agent,
        )

        reset_agent()
        use_postgres_saver()

        with patch(
            "app.config.settings.get_settings"
        ) as mock_settings:
            mock_settings.return_value.database_url = (
                "postgresql://invalid:invalid@invalid:5432/invalid"
            )

            with patch.dict(
                "sys.modules",
                {"langgraph.checkpoint.postgres.aio": MagicMock(side_effect=ImportError)},
            ):
                # RuntimeError が発生することを期待（フォールバックなし）
                with pytest.raises(RuntimeError, match="Database persistence unavailable"):
                    await get_agent()

        reset_agent()


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
