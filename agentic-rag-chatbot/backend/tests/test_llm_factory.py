"""LLM ファクトリのテスト"""

from unittest.mock import MagicMock, patch

import app.agents.llm_factory as llm_factory_module
from app.agents.llm_factory import get_llm, set_session_id, get_session_id, clear_session_id, log_llm_call


class TestGetLlm:
    def test_returns_same_instance_for_same_params(self):
        """同一パラメータで同じインスタンスが返されることを確認"""
        get_llm.cache_clear()

        with patch("app.agents.llm_factory.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            llm1 = get_llm(temperature=0.0)
            llm2 = get_llm(temperature=0.0)

        assert llm1 is llm2
        assert mock_cls.call_count == 1

    def test_returns_different_instance_for_different_params(self):
        """異なるパラメータで異なるインスタンスが返されることを確認"""
        get_llm.cache_clear()

        with patch("app.agents.llm_factory.ChatOpenAI") as mock_cls:
            mock_cls.side_effect = [MagicMock(), MagicMock()]
            llm1 = get_llm(temperature=0.0)
            llm2 = get_llm(temperature=0.3)

        assert llm1 is not llm2
        assert mock_cls.call_count == 2

    def test_passes_correct_settings(self):
        """正しい設定値が ChatOpenAI に渡されることを確認"""
        get_llm.cache_clear()

        with patch("app.agents.llm_factory.ChatOpenAI") as mock_cls, \
             patch("app.agents.llm_factory.get_settings") as mock_settings:
            mock_settings.return_value.openai_model = "test-model"
            mock_api_key = MagicMock()
            mock_api_key.get_secret_value.return_value = "test-key"
            mock_settings.return_value.openai_api_key = mock_api_key
            mock_cls.return_value = MagicMock()

            get_llm(temperature=0.5)

        mock_cls.assert_called_once_with(
            model="test-model",
            api_key="test-key",
            temperature=0.5,
            streaming=False,
        )


class TestLlmCache:
    def test_in_memory_cache_is_set(self):
        """モジュールレベルで InMemoryCache が設定されていることを確認"""
        from langchain_community.cache import InMemoryCache
        from langchain_core.globals import get_llm_cache

        cache = get_llm_cache()
        assert isinstance(cache, InMemoryCache)


class TestSessionContext:
    """セッションコンテキスト管理のテスト"""

    def test_set_and_get_session_id(self):
        """セッションIDの設定と取得を確認"""
        clear_session_id()
        assert get_session_id() is None

        set_session_id("test-session-123")
        assert get_session_id() == "test-session-123"

        clear_session_id()
        assert get_session_id() is None

    def test_clear_session_id(self):
        """セッションIDのクリアを確認"""
        set_session_id("test-session-456")
        assert get_session_id() == "test-session-456"

        clear_session_id()
        assert get_session_id() is None


class TestCostServiceIntegration:
    """CostService連携のテスト"""

    def test_log_llm_call_records_cost_with_session(self):
        """session_idを指定した場合、CostServiceにコストが記録されることを確認"""
        from app.services.cost_service import CostService

        # Reset singleton
        CostService._instance = None

        log_llm_call(
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
            session_id="test-session-cost",
        )

        # Verify cost was recorded
        service = CostService.get_instance()
        costs = service.get_costs_by_session("test-session-cost")
        assert len(costs) == 1
        assert costs[0].model == "gpt-4o-mini"
        assert costs[0].input_tokens == 100
        assert costs[0].output_tokens == 50

        # Clean up
        CostService._instance = None

    def test_log_llm_call_uses_context_session_id(self):
        """コンテキストのsession_idが使用されることを確認"""
        from app.services.cost_service import CostService

        # Reset singleton and set context
        CostService._instance = None
        clear_session_id()
        set_session_id("context-session-123")

        log_llm_call(
            model="gpt-4o",
            input_tokens=200,
            output_tokens=100,
            duration_ms=300,
        )

        # Verify cost was recorded with context session ID
        service = CostService.get_instance()
        costs = service.get_costs_by_session("context-session-123")
        assert len(costs) == 1
        assert costs[0].model == "gpt-4o"

        # Clean up
        clear_session_id()
        CostService._instance = None

    def test_log_llm_call_no_cost_without_session(self):
        """session_idがない場合、コストが記録されないことを確認"""
        from app.services.cost_service import CostService

        # Reset singleton and clear context
        CostService._instance = None
        clear_session_id()

        log_llm_call(
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            duration_ms=500,
        )

        # Verify no cost was recorded (no session_id available)
        service = CostService.get_instance()
        total = service.get_total_costs()
        # Should have 0 calls because no session_id
        assert total["call_count"] == 0

        # Clean up
        CostService._instance = None

    def test_log_llm_call_no_cost_with_zero_tokens(self):
        """トークン数が0の場合、コストが記録されないことを確認"""
        from app.services.cost_service import CostService

        # Reset singleton
        CostService._instance = None

        log_llm_call(
            model="gpt-4o-mini",
            input_tokens=0,
            output_tokens=0,
            duration_ms=500,
            session_id="zero-tokens-session",
        )

        # Verify no cost was recorded (input_tokens is 0)
        service = CostService.get_instance()
        costs = service.get_costs_by_session("zero-tokens-session")
        assert len(costs) == 0

        # Clean up
        CostService._instance = None
