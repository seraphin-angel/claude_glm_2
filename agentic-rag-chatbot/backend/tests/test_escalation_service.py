"""EscalationService のユニットテスト"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.escalation_service import EscalationService


@pytest.fixture
def temp_persist_path(tmp_path: Path) -> Path:
    """テスト用の一時ファイルパス"""
    return tmp_path / "escalations.json"


@pytest.fixture
def service(temp_persist_path: Path) -> EscalationService:
    """テスト用のEscalationServiceインスタンス"""
    EscalationService.reset_instance()
    service = EscalationService(persist_path=str(temp_persist_path))
    return service


@pytest.fixture
def sample_conversation_history() -> list[dict]:
    """サンプル会話履歴"""
    return [
        {"role": "user", "content": "ログインできません"},
        {"role": "assistant", "content": "メールアドレスは正しいですか？"},
        {"role": "user", "content": "はい、正しいです"},
        {"role": "assistant", "content": "パスワードをリセットしてみてください"},
        {"role": "user", "content": "リセットしても解決しません"},
    ]


class TestEscalationServiceCreateTicket:
    """create_ticket メソッドのテスト"""

    def test_create_ticket_basic(self, service: EscalationService):
        """基本的なチケット作成"""
        ticket = service.create_ticket(
            reason="ユーザーが解決を希望",
            urgency="high",
            summary="ログイン問題が解決しない",
        )

        assert ticket["id"].startswith("ESC-")
        assert ticket["reason"] == "ユーザーが解決を希望"
        assert ticket["urgency"] == "high"
        assert ticket["summary"] == "ログイン問題が解決しない"
        assert ticket["status"] == "open"
        assert "created_at" in ticket

    def test_create_ticket_with_conversation_history(
        self,
        service: EscalationService,
        sample_conversation_history: list[dict],
    ):
        """会話履歴付きチケット作成"""
        with patch.object(
            service, "_generate_summary", return_value="Generated summary"
        ) as mock_gen:
            ticket = service.create_ticket(
                reason="技術的に解決不可",
                urgency="medium",
                summary="",
                conversation_history=sample_conversation_history,
            )

            mock_gen.assert_called_once_with(sample_conversation_history)
            assert ticket["summary"] == "Generated summary"

    def test_create_ticket_invalid_urgency(self, service: EscalationService):
        """無効な緊急度でエラー"""
        with pytest.raises(ValueError, match="urgency must be one of"):
            service.create_ticket(
                reason="test",
                urgency="critical",  # invalid
                summary="test",
            )

    def test_create_ticket_persists_to_file(
        self, service: EscalationService, temp_persist_path: Path
    ):
        """チケットがファイルに永続化される"""
        service.create_ticket(
            reason="Test reason",
            urgency="low",
            summary="Test summary",
        )

        assert temp_persist_path.exists()
        with open(temp_persist_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["reason"] == "Test reason"


class TestEscalationServiceGetTickets:
    """get_tickets メソッドのテスト"""

    def test_get_tickets_empty(self, service: EscalationService):
        """チケットがない場合"""
        tickets = service.get_tickets()
        assert tickets == []

    def test_get_tickets_with_data(self, service: EscalationService):
        """チケットがある場合"""
        service.create_ticket(reason="Reason 1", urgency="low", summary="Summary 1")
        service.create_ticket(reason="Reason 2", urgency="high", summary="Summary 2")

        tickets = service.get_tickets()

        assert len(tickets) == 2
        # 新しい順
        assert tickets[0]["reason"] == "Reason 2"
        assert tickets[1]["reason"] == "Reason 1"

    def test_get_tickets_with_limit(self, service: EscalationService):
        """制限付きで取得"""
        for i in range(5):
            service.create_ticket(
                reason=f"Reason {i}", urgency="low", summary=f"Summary {i}"
            )

        tickets = service.get_tickets(limit=3)

        assert len(tickets) == 3


class TestEscalationServiceGetTicket:
    """get_ticket メソッドのテスト"""

    def test_get_ticket_found(self, service: EscalationService):
        """チケットが見つかる場合"""
        created = service.create_ticket(
            reason="Test", urgency="low", summary="Test summary"
        )

        ticket = service.get_ticket(created["id"])

        assert ticket is not None
        assert ticket["id"] == created["id"]

    def test_get_ticket_not_found(self, service: EscalationService):
        """チケットが見つからない場合"""
        ticket = service.get_ticket("ESC-999")

        assert ticket is None


class TestEscalationServiceGenerateSummary:
    """_generate_summary メソッドのテスト"""

    def test_generate_summary_with_llm(
        self, service: EscalationService, sample_conversation_history: list[dict]
    ):
        """LLMでサマリー生成"""
        with patch("app.agents.llm_factory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value.content = "ユーザーはログイン問題を抱えています"
            mock_get_llm.return_value = mock_llm

            summary = service._generate_summary(sample_conversation_history)

            assert summary == "ユーザーはログイン問題を抱えています"
            mock_llm.invoke.assert_called_once()

    def test_generate_summary_empty_history(self, service: EscalationService):
        """空の履歴の場合"""
        summary = service._generate_summary([])

        assert summary == "（会話履歴なし）"


class TestEscalationServiceSingleton:
    """シングルトンパターンのテスト"""

    def test_singleton_returns_same_instance(self, temp_persist_path: Path):
        """同じインスタンスを返す"""
        EscalationService.reset_instance()

        with patch(
            "app.services.escalation_service.EscalationService.__init__",
            return_value=None,
        ):
            instance1 = EscalationService.get_instance()
            instance2 = EscalationService.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """リセット後に新しいインスタンス"""
        EscalationService.reset_instance()
        EscalationService.reset_instance()

        # リセット後はNoneになる
        assert EscalationService._instance is None


class TestEscalationServicePersistence:
    """永続化のテスト"""

    def test_load_existing_data(self, temp_persist_path: Path):
        """既存データの読み込み"""
        existing_data = [
            {
                "id": "ESC-001",
                "reason": "Existing reason",
                "urgency": "high",
                "summary": "Existing summary",
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        temp_persist_path.parent.mkdir(parents=True, exist_ok=True)
        temp_persist_path.write_text(
            json.dumps(existing_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        EscalationService.reset_instance()
        service = EscalationService(persist_path=str(temp_persist_path))

        tickets = service.get_tickets()

        assert len(tickets) == 1
        assert tickets[0]["id"] == "ESC-001"

    def test_handles_corrupted_file(self, temp_persist_path: Path):
        """破損ファイルの処理"""
        temp_persist_path.parent.mkdir(parents=True, exist_ok=True)
        temp_persist_path.write_text("invalid json", encoding="utf-8")

        EscalationService.reset_instance()
        service = EscalationService(persist_path=str(temp_persist_path))

        # 破損ファイルの場合は空リストで開始
        tickets = service.get_tickets()
        assert tickets == []
