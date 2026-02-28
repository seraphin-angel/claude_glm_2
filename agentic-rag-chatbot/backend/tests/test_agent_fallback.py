"""Tests for Agent initialization fallback behavior.

Critical Test Cases (Criticality 9-10):
- PostgresSaver初期化失敗時にMemorySaverにフォールバックすること
- is_persistence_healthy() がフォールバック時に False を返すこと
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys


class TestAgentInitializationFallback:
    """Agent初期化フォールバックのテスト"""

    @pytest.mark.asyncio
    async def test_agent_fallback_to_memory_saver_on_postgres_failure(self):
        """PostgresSaver初期化失敗時にMemorySaverにフォールバックすること"""
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent, get_checkpointer
        from langgraph.checkpoint.memory import MemorySaver

        # Arrange: リセットしてPostgresSaverモードに設定
        reset_agent()
        use_postgres_saver()

        # PostgresSaver.from_conn_string が例外を投げるようにモック
        # 注意: get_agent()内で動的インポートされるため、モジュールレベルでパッチ
        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string = AsyncMock(
            side_effect=Exception("Connection failed: host unreachable")
        )

        with patch.dict(
            "sys.modules",
            {"langgraph.checkpoint.postgres.aio": mock_postgres_saver_class}
        ):
            # Act: エージェントを取得
            agent = await get_agent()

            # Assert: エージェントが取得でき、MemorySaverが使用されている
            assert agent is not None
            checkpointer = get_checkpointer()
            assert isinstance(checkpointer, MemorySaver)

        # Cleanup
        reset_agent()

    @pytest.mark.asyncio
    async def test_persistence_unhealthy_on_fallback(self):
        """フォールバック時に is_persistence_healthy() が False を返すこと"""
        from app.agents.agent import (
            reset_agent,
            use_postgres_saver,
            get_agent,
            is_persistence_healthy,
        )

        # Arrange: リセットしてPostgresSaverモードに設定
        reset_agent()
        use_postgres_saver()

        # PostgresSaver初期化でエラーが発生するようにモック
        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        with patch.dict(
            "sys.modules",
            {"langgraph.checkpoint.postgres.aio": mock_postgres_saver_class}
        ):
            # Act: エージェントを取得（フォールバック発生）
            agent = await get_agent()

            # Assert: persistence_healthy が False であること
            assert agent is not None
            assert is_persistence_healthy() is False

        # Cleanup
        reset_agent()

    @pytest.mark.asyncio
    async def test_persistence_healthy_on_explicit_memory_saver(self):
        """明示的にMemorySaverを使用する場合、is_persistence_healthy() が True を返すこと"""
        from app.agents.agent import (
            reset_agent,
            use_memory_saver,
            get_agent,
            is_persistence_healthy,
        )

        # Arrange: 明示的にMemorySaverモードに設定
        reset_agent()
        use_memory_saver()

        # Act: エージェントを取得
        agent = await get_agent()

        # Assert: persistence_healthy が True であること（意図的な使用は正常）
        assert agent is not None
        assert is_persistence_healthy() is True

        # Cleanup
        reset_agent()

    @pytest.mark.asyncio
    async def test_fallback_logs_critical_degraded_state(self, caplog):
        """フォールバック時にCRITICALログが出力されること"""
        import logging
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        # Arrange
        reset_agent()
        use_postgres_saver()

        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with patch.dict(
            "sys.modules",
            {"langgraph.checkpoint.postgres.aio": mock_postgres_saver_class}
        ):
            # Act
            with caplog.at_level(logging.ERROR):
                agent = await get_agent()

            # Assert: エラーログにCRITICAL/DEGRADEDの文言が含まれること
            assert agent is not None
            error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
            assert len(error_logs) > 0
            # "CRITICAL" または "DEGRADED" を含むログがあること
            log_messages = " ".join([r.message for r in error_logs])
            assert "CRITICAL" in log_messages or "DEGRADED" in log_messages

        # Cleanup
        reset_agent()

    @pytest.mark.asyncio
    async def test_multiple_fallback_attempts_remain_stable(self):
        """複数回フォールバックが発生しても安定していること"""
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent

        for attempt in range(3):
            # Arrange
            reset_agent()
            use_postgres_saver()

            mock_postgres_saver_class = MagicMock()
            mock_postgres_saver_class.from_conn_string = AsyncMock(
                side_effect=Exception(f"Connection failed attempt {attempt}")
            )

            with patch.dict(
                "sys.modules",
                {"langgraph.checkpoint.postgres.aio": mock_postgres_saver_class}
            ):
                # Act
                agent = await get_agent()

                # Assert
                assert agent is not None

            # Cleanup for next iteration
            reset_agent()


class TestAgentRecoveryAfterFallback:
    """フォールバック後の復旧テスト"""

    @pytest.mark.asyncio
    async def test_agent_can_recover_after_initial_failure(self):
        """初期化失敗後、次回は成功する可能性があること"""
        from app.agents.agent import reset_agent, use_postgres_saver, get_agent, is_persistence_healthy, use_memory_saver

        # First attempt: failure -> fallback
        reset_agent()
        use_postgres_saver()

        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with patch.dict(
            "sys.modules",
            {"langgraph.checkpoint.postgres.aio": mock_postgres_saver_class}
        ):
            agent = await get_agent()
            assert is_persistence_healthy() is False

        # Reset and try again with success (simulating recovery)
        reset_agent()
        use_memory_saver()  # Simulate successful connection

        agent = await get_agent()
        assert agent is not None
        assert is_persistence_healthy() is True

        # Cleanup
        reset_agent()
