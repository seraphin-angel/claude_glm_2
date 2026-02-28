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


class TestEscalationServiceCreateTicketAsync:
    """create_ticket_async メソッドのテスト"""

    @pytest.mark.asyncio
    async def test_create_ticket_async_basic(self, service: EscalationService):
        """基本的な非同期チケット作成"""
        ticket = await service.create_ticket_async(
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

    @pytest.mark.asyncio
    async def test_create_ticket_async_with_conversation_history(
        self,
        service: EscalationService,
        sample_conversation_history: list[dict],
    ):
        """会話履歴付き非同期チケット作成"""
        with patch.object(
            service, "_generate_summary_async", return_value="Async generated summary"
        ) as mock_gen:
            ticket = await service.create_ticket_async(
                reason="技術的に解決不可",
                urgency="medium",
                summary="",
                conversation_history=sample_conversation_history,
            )

            mock_gen.assert_called_once_with(sample_conversation_history)
            assert ticket["summary"] == "Async generated summary"

    @pytest.mark.asyncio
    async def test_create_ticket_async_invalid_urgency(self, service: EscalationService):
        """無効な緊急度でエラー"""
        with pytest.raises(ValueError, match="urgency must be one of"):
            await service.create_ticket_async(
                reason="test",
                urgency="critical",  # invalid
                summary="test",
            )


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

    def test_generate_summary_llm_failure_logs_error(
        self, service: EscalationService, sample_conversation_history: list[dict]
    ):
        """LLM失敗時にerrorレベルでexc_info=Trueでログ出力される"""
        with patch("app.agents.llm_factory.get_llm") as mock_get_llm:
            mock_get_llm.side_effect = Exception("LLM connection error")

            with patch("app.services.escalation_service.logger") as mock_logger:
                summary = service._generate_summary(sample_conversation_history)

                assert summary == "（サマリー生成エラー）"
                # errorレベルで、exc_info=Trueでログ出力されることを確認
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args
                assert call_args[1].get("exc_info") is True


class TestEscalationServiceAsyncGenerateSummary:
    """_generate_summary_async メソッドのテスト（非同期化: TDD RED）"""

    @pytest.mark.asyncio
    async def test_generate_summary_async_uses_ainvoke(
        self, service: EscalationService, sample_conversation_history: list[dict]
    ):
        """ainvokeが呼ばれることを検証"""
        with patch("app.agents.llm_factory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            # ainvokeはコルーチンを返す必要がある
            async def mock_ainvoke(prompt):
                class MockResponse:
                    content = "非同期で生成されたサマリー"
                return MockResponse()

            mock_llm.ainvoke = mock_ainvoke
            mock_get_llm.return_value = mock_llm

            summary = await service._generate_summary_async(sample_conversation_history)

            assert summary == "非同期で生成されたサマリー"

    @pytest.mark.asyncio
    async def test_generate_summary_async_sets_session_id(
        self, service: EscalationService, sample_conversation_history: list[dict]
    ):
        """セッションIDが設定されることを検証"""
        with patch("app.agents.llm_factory.get_llm") as mock_get_llm, \
             patch("app.agents.llm_factory.set_session_id") as mock_set_session, \
             patch("app.agents.llm_factory.clear_session_id") as mock_clear_session:

            mock_llm = MagicMock()
            async def mock_ainvoke(prompt):
                class MockResponse:
                    content = "サマリー"
                return MockResponse()
            mock_llm.ainvoke = mock_ainvoke
            mock_get_llm.return_value = mock_llm

            await service._generate_summary_async(sample_conversation_history)

            # セッションIDが設定されたことを確認
            mock_set_session.assert_called_once()
            # セッションIDがクリアされたことを確認
            mock_clear_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_async_clears_session_on_error(
        self, service: EscalationService, sample_conversation_history: list[dict]
    ):
        """エラー時もセッションIDがクリアされることを検証"""
        with patch("app.agents.llm_factory.get_llm") as mock_get_llm, \
             patch("app.agents.llm_factory.set_session_id") as mock_set_session, \
             patch("app.agents.llm_factory.clear_session_id") as mock_clear_session, \
             patch("app.services.escalation_service.logger"):

            mock_get_llm.side_effect = Exception("LLM error")

            summary = await service._generate_summary_async(sample_conversation_history)

            assert summary == "（サマリー生成エラー）"
            # エラー時もクリアが呼ばれることを確認
            mock_clear_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_async_empty_history(
        self, service: EscalationService
    ):
        """空の履歴の場合はLLMを呼ばずに早期リターン"""
        summary = await service._generate_summary_async([])

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


class TestEscalationServiceSaveError:
    """_save メソッドのエラーハンドリングテスト（TDD: Issue #2）"""

    def test_save_raises_ioerror_on_write_failure(self, temp_persist_path: Path):
        """_save失敗時にIOErrorが発生することをテスト"""
        EscalationService.reset_instance()
        service = EscalationService(persist_path=str(temp_persist_path))

        # write_textを失敗させる
        with patch.object(Path, "write_text", side_effect=PermissionError("write denied")):
            with pytest.raises(IOError) as exc_info:
                service._save()

            assert "Failed to save escalation data" in str(exc_info.value)

        EscalationService.reset_instance()

    def test_create_ticket_propagates_save_error(self, temp_persist_path: Path):
        """create_ticketで_saveが失敗した場合、エラーが伝播することをテスト"""
        EscalationService.reset_instance()
        service = EscalationService(persist_path=str(temp_persist_path))

        # _saveを失敗させる
        with patch.object(service, "_save", side_effect=IOError("disk full")):
            with pytest.raises(IOError) as exc_info:
                service.create_ticket(
                    reason="test reason",
                    urgency="high",
                    summary="test summary",
                )

            assert "disk full" in str(exc_info.value)

        EscalationService.reset_instance()

    def test_save_logs_error_with_details_on_failure(self, temp_persist_path: Path):
        """_save失敗時にエラー詳細を含むログが出力されることをテスト"""
        EscalationService.reset_instance()
        service = EscalationService(persist_path=str(temp_persist_path))

        with patch.object(Path, "write_text", side_effect=PermissionError("write denied")):
            with patch("app.services.escalation_service.logger") as mock_logger:
                with pytest.raises(IOError):
                    service._save()

                # errorレベルでログが出力されることを確認
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args
                # DATA LOSS RISK が含まれることを確認
                assert "DATA LOSS RISK" in call_args[0][0]

        EscalationService.reset_instance()
