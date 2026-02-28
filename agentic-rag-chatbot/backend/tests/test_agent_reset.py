"""Tests for reset_agent() asyncio API modernization.

This test module verifies that reset_agent() uses non-deprecated asyncio APIs
(Python 3.10+) and handles various event loop states correctly.

TDD Red-Green-Refactor cycle:
1. RED: These tests verify the expected behavior after modernization
2. GREEN: Implement the fix to pass tests
3. REFACTOR: Clean up and optimize
"""

import asyncio
import warnings
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Import the module under test
from app.agents.agent import reset_agent


class TestResetAgentAsyncioAPI:
    """Test reset_agent() uses modern asyncio APIs (Python 3.10+)."""

    @pytest.mark.asyncio
    async def test_reset_agent_with_running_loop_uses_get_running_loop(self):
        """When event loop is running, should use get_running_loop() not get_event_loop().

        This verifies we're using the non-deprecated API.
        """
        # Setup: Create a mock checkpointer context
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        # Patch the global _checkpointer_context
        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    # Capture warnings during reset_agent call
                    with warnings.catch_warnings(record=True) as warning_list:
                        warnings.simplefilter("always")

                        reset_agent()

                        # Give event loop a chance to process scheduled tasks
                        await asyncio.sleep(0)

                        # Check that no deprecation warning about get_event_loop was raised
                        for w in warning_list:
                            assert "get_event_loop" not in str(w.message).lower(), (
                                f"Found deprecated get_event_loop usage: {w.message}"
                            )

    def test_reset_agent_without_running_loop_creates_new_loop(self):
        """When no event loop is running, should handle gracefully without deprecated API.

        Should not call asyncio.get_event_loop() which is deprecated in Python 3.10+.
        """
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        # Ensure no running loop
        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    with patch("app.agents.agent._persistence_healthy", True):
                        # This should not use deprecated get_event_loop()
                        # Instead should use get_running_loop() with RuntimeError handling
                        reset_agent()

                        # Verify globals were reset
                        from app.agents import agent

                        assert agent._agent is None
                        assert agent._checkpointer is None
                        assert agent._checkpointer_context is None
                        assert agent._persistence_healthy is True

    def test_reset_agent_handles_runtime_error_gracefully(self):
        """When get_running_loop() raises RuntimeError, should handle gracefully.

        get_running_loop() raises RuntimeError when no loop is running.
        The code should catch this and handle appropriately.
        """
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    # Should not raise even when no loop is running
                    # (which is the case when called outside async context)
                    reset_agent()

                    # Verify cleanup happened
                    from app.agents import agent

                    assert agent._agent is None
                    assert agent._checkpointer is None
                    assert agent._checkpointer_context is None

    @pytest.mark.asyncio
    async def test_reset_agent_async_context_schedules_cleanup(self):
        """When called from async context, should schedule cleanup via create_task."""
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    # In async context, loop is running
                    loop = asyncio.get_running_loop()

                    # Patch create_task to verify it's called
                    original_create_task = loop.create_task
                    create_task_called = []

                    def track_create_task(coro):
                        create_task_called.append(coro)
                        return original_create_task(coro)

                    with patch.object(loop, "create_task", track_create_task):
                        reset_agent()

                        # Give event loop a chance to process
                        await asyncio.sleep(0)

                    # Verify globals were reset
                    from app.agents import agent

                    assert agent._agent is None
                    assert agent._checkpointer is None
                    assert agent._checkpointer_context is None

    def test_reset_agent_no_checkpointer_context_does_nothing_async(self):
        """When _checkpointer_context is None, should simply reset globals."""
        with patch("app.agents.agent._checkpointer_context", None):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    with patch("app.agents.agent._persistence_healthy", False):
                        reset_agent()

                        from app.agents import agent

                        assert agent._agent is None
                        assert agent._checkpointer is None
                        assert agent._checkpointer_context is None
                        assert agent._persistence_healthy is True


class TestResetAgentNoDeprecationWarning:
    """Verify that reset_agent() does not trigger deprecation warnings."""

    @pytest.mark.asyncio
    async def test_no_get_event_loop_deprecation_warning_in_async_context(self):
        """Ensure asyncio.get_event_loop() deprecation warning is not triggered in async context.

        In Python 3.10+, asyncio.get_event_loop() emits a DeprecationWarning
        when called from a coroutine.
        """
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        # Capture all warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings

            with patch("app.agents.agent._checkpointer_context", mock_context):
                with patch("app.agents.agent._agent", MagicMock()):
                    with patch("app.agents.agent._checkpointer", MagicMock()):
                        reset_agent()

                        # Process any scheduled tasks
                        await asyncio.sleep(0)

            # Check for any asyncio deprecation warnings related to get_event_loop
            get_event_loop_warnings = [
                w for w in warning_list
                if "get_event_loop" in str(w.message).lower()
                or ("no current event loop" in str(w.message).lower())
            ]

            # We should not have any asyncio.get_event_loop deprecation warnings
            assert len(get_event_loop_warnings) == 0, (
                f"Found deprecation warnings: {[str(w.message) for w in get_event_loop_warnings]}"
            )

    def test_no_get_event_loop_deprecation_warning_sync(self):
        """Ensure no deprecation warning in sync context."""
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            with patch("app.agents.agent._checkpointer_context", mock_context):
                with patch("app.agents.agent._agent", MagicMock()):
                    with patch("app.agents.agent._checkpointer", MagicMock()):
                        reset_agent()

            # Check for get_event_loop warnings
            get_event_loop_warnings = [
                w for w in warning_list
                if "get_event_loop" in str(w.message).lower()
            ]

            assert len(get_event_loop_warnings) == 0, (
                f"Found deprecation warnings: {[str(w.message) for w in get_event_loop_warnings]}"
            )


class TestResetAgentEdgeCases:
    """Test edge cases and error handling."""

    def test_reset_agent_cleanup_exception_logged(self):
        """When cleanup raises exception, should log warning but not crash."""
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(side_effect=RuntimeError("Cleanup failed"))

        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    # Should not raise, just log warning
                    reset_agent()

                    # Verify globals were still reset
                    from app.agents import agent

                    assert agent._agent is None
                    assert agent._checkpointer is None
                    assert agent._checkpointer_context is None

    @pytest.mark.asyncio
    async def test_reset_agent_in_asyncio_run_context(self):
        """Test reset_agent works correctly when called from asyncio.run()."""
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock()):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    # Should work without errors
                    reset_agent()

                    # Verify cleanup
                    from app.agents import agent

                    assert agent._agent is None
                    assert agent._checkpointer is None
                    assert agent._checkpointer_context is None

    def test_reset_agent_globals_always_reset(self):
        """Verify that globals are always reset even if cleanup fails."""
        mock_context = AsyncMock()
        mock_context.__aexit__ = AsyncMock(side_effect=Exception("Any error"))

        with patch("app.agents.agent._checkpointer_context", mock_context):
            with patch("app.agents.agent._agent", MagicMock(return_value="agent")):
                with patch("app.agents.agent._checkpointer", MagicMock()):
                    with patch("app.agents.agent._persistence_healthy", False):
                        reset_agent()

                        from app.agents import agent

                        # Globals must be reset regardless of cleanup success
                        assert agent._agent is None
                        assert agent._checkpointer is None
                        assert agent._checkpointer_context is None
                        assert agent._persistence_healthy is True
