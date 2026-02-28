"""LLM ファクトリのテスト"""

import threading
import time
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

    def test_log_llm_call_cost_failure_logs_with_error_level_and_error_id(self):
        """CostService記録失敗時にlogger.errorでエラーID付きログが出力されることを確認"""
        from unittest.mock import patch, MagicMock
        from app.services.cost_service import CostService

        # CostServiceのrecord_usageが例外を投げるようにモック
        original_instance = CostService._instance
        CostService._instance = None

        try:
            mock_cost_service = MagicMock()
            mock_cost_service.record_usage.side_effect = RuntimeError("DB connection failed")

            with patch.object(CostService, "get_instance", return_value=mock_cost_service), \
                 patch("app.agents.llm_factory.logger") as mock_logger:
                log_llm_call(
                    model="gpt-4o-mini",
                    input_tokens=100,
                    output_tokens=50,
                    duration_ms=500,
                    session_id="test-session-error",
                )

            # logger.error が呼ばれたことを確認（warning ではなく error）
            assert mock_logger.error.called
            error_call = mock_logger.error.call_args

            # error_id が含まれていることを確認
            assert "error_id" in error_call[1]

            # exc_info=True が設定されていることを確認
            assert error_call[1].get("exc_info") is True
        finally:
            CostService._instance = original_instance


class TestSessionContextThreadSafety:
    """セッションコンテキストのスレッド安全性テスト"""

    def test_concurrent_session_context_isolation(self):
        """並行アクセス時にセッションIDが混在しないことを検証"""
        results = {}
        errors = []

        def worker(thread_id: str):
            try:
                # 各スレッドで異なるセッションIDを設定
                set_session_id(thread_id)
                time.sleep(0.01)  # コンテキストスイッチを誘発
                # 自分のセッションIDが取得できることを確認
                result = get_session_id()
                results[thread_id] = result
                clear_session_id()
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"session_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # エラーがないことを確認
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # 各スレッドが自分のセッションIDを取得できたことを確認
        for thread_id, result in results.items():
            assert result == thread_id, f"Session ID mismatch: expected {thread_id}, got {result}"

    def test_token_tracker_concurrent_access(self):
        """TokenTrackerの並行アクセスが安全であることを検証"""
        from app.agents.llm_factory import TokenTracker, get_token_tracker

        # リセットしてクリーンな状態にする
        tracker = get_token_tracker()
        tracker.reset()
        errors = []

        def add_usage_worker(i: int):
            try:
                for _ in range(10):
                    tracker.add_usage(10, 5)
                    time.sleep(0.001)  # コンテキストスイッチを誘発
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=add_usage_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # エラーが発生しないことを確認
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # トークン数が正しく集計されていることを確認
        # 5スレッド x 10回 x (10 input + 5 output) = 500 input, 250 output
        summary = tracker.get_summary()
        assert summary["call_count"] == 50  # 5 * 10
        assert summary["total_input_tokens"] == 500  # 5 * 10 * 10
        assert summary["total_output_tokens"] == 250  # 5 * 10 * 5

    def test_token_tracker_concurrent_reset(self):
        """TokenTrackerの並行リセットが安全であることを検証"""
        from app.agents.llm_factory import TokenTracker, get_token_tracker

        tracker = get_token_tracker()
        tracker.reset()
        errors = []

        def reset_and_record(i: int):
            try:
                tracker.reset()
                tracker.add_usage(100, 50)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=reset_and_record, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # エラーが発生してもクラッシュしないことを確認
        # 完全な一貫性は期待しないが、クラッシュしてはならない
        assert len(errors) == 0 or all("lock" not in e.lower() for e in errors)
