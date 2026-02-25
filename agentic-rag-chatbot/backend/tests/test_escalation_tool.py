"""escalate_to_human ツールのユニットテスト"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import ToolException

from app.agents.tools.escalation import EscalationInput, escalate_to_human


class TestEscalationInput:
    """EscalationInput モデルのテスト"""

    def test_valid_input(self):
        """有効な入力"""
        inp = EscalationInput(
            reason="ユーザーが有人対応を希望",
            urgency="high",
            summary="ログイン問題が解決しない",
        )
        assert inp.reason == "ユーザーが有人対応を希望"
        assert inp.urgency == "high"
        assert inp.summary == "ログイン問題が解決しない"

    def test_valid_urgencies(self):
        """各緊急度"""
        for urgency in ["low", "medium", "high"]:
            inp = EscalationInput(reason="test", urgency=urgency, summary="test")
            assert inp.urgency == urgency

    def test_empty_summary_allowed(self):
        """空のサマリーは許可される（自動生成されるため）"""
        inp = EscalationInput(reason="test", urgency="low", summary="")
        assert inp.summary == ""


class TestEscalateToHumanTool:
    """escalate_to_human ツールのテスト"""

    def test_tool_metadata(self):
        """ツールのメタデータ"""
        assert escalate_to_human.name == "escalate_to_human"
        assert "エスカレーション" in escalate_to_human.description

    def test_successful_escalation(self):
        """正常なエスカレーション"""
        with patch(
            "app.agents.tools.escalation.EscalationService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_ticket.return_value = {
                "id": "ESC-12345678",
                "reason": "テスト理由",
                "urgency": "high",
                "summary": "テストサマリー",
                "status": "open",
            }
            mock_service_class.get_instance.return_value = mock_service

            result = escalate_to_human.invoke(
                {
                    "reason": "テスト理由",
                    "urgency": "high",
                    "summary": "テストサマリー",
                }
            )

            assert "ESC-12345678" in result
            mock_service.create_ticket.assert_called_once_with(
                reason="テスト理由",
                urgency="high",
                summary="テストサマリー",
                conversation_history=None,
            )

    def test_escalation_with_conversation_history(self):
        """会話履歴付きエスカレーション"""
        with patch(
            "app.agents.tools.escalation.EscalationService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_ticket.return_value = {
                "id": "ESC-ABCD1234",
                "reason": "技術的問題",
                "urgency": "medium",
                "summary": "Generated summary",
                "status": "open",
            }
            mock_service_class.get_instance.return_value = mock_service

            with patch(
                "app.agents.tools.escalation.get_conversation_history"
            ) as mock_get_history:
                mock_get_history.return_value = [
                    {"role": "user", "content": "Help"}
                ]

                result = escalate_to_human.invoke(
                    {
                        "reason": "技術的問題",
                        "urgency": "medium",
                        "summary": "",
                    }
                )

                assert "ESC-ABCD1234" in result
                mock_service.create_ticket.assert_called_once()

    def test_escalation_invalid_urgency(self):
        """無効な緊急度でエラー"""
        with patch(
            "app.agents.tools.escalation.EscalationService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_ticket.side_effect = ValueError(
                "urgency must be one of"
            )
            mock_service_class.get_instance.return_value = mock_service

            with pytest.raises((ToolException, ValueError)):
                escalate_to_human.invoke(
                    {
                        "reason": "test",
                        "urgency": "critical",
                        "summary": "test",
                    }
                )

    def test_return_message_format(self):
        """戻り値メッセージのフォーマット"""
        with patch(
            "app.agents.tools.escalation.EscalationService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_ticket.return_value = {
                "id": "ESC-TEST1234",
                "reason": "test",
                "urgency": "low",
                "summary": "test",
                "status": "open",
            }
            mock_service_class.get_instance.return_value = mock_service

            result = escalate_to_human.invoke(
                {"reason": "test", "urgency": "low", "summary": "test"}
            )

            # チケットIDが含まれている
            assert "ESC-TEST1234" in result
            # エスカレーション完了の旨が含まれている
            assert "エスカレーション" in result or "受け付け" in result
