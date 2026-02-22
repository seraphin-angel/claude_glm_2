"""LLM ファクトリのテスト"""

from unittest.mock import MagicMock, patch

from app.agents.llm_factory import get_llm


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
            mock_settings.return_value.openai_api_key = "test-key"
            mock_cls.return_value = MagicMock()

            get_llm(temperature=0.5)

        mock_cls.assert_called_once_with(
            model="test-model",
            api_key="test-key",
            temperature=0.5,
            streaming=False,
        )
