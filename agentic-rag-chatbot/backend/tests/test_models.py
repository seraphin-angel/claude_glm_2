"""データモデルのユニットテスト"""

import pytest
from pydantic import ValidationError
from uuid import UUID

from app.models.chat import ChatRequest, ChatStartResponse
from app.models.hitl import HITLRequest, HITLResponse, ResumeRequest
from app.models.messages import StreamEvent, StreamEventType
from app.agents.state import AgentState


# ---------------------------------------------------------------------------
# ChatRequest テスト
# ---------------------------------------------------------------------------


class TestChatRequest:
    def test_valid_message(self):
        """正常なメッセージでモデルが作成できること"""
        req = ChatRequest(message="Hello, world!")
        assert req.message == "Hello, world!"
        assert req.thread_id is None

    def test_with_thread_id(self):
        """thread_id を指定して作成できること"""
        req = ChatRequest(message="続きの質問", thread_id="550e8400-e29b-41d4-a716-446655440000")
        assert req.thread_id == UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_empty_message_raises_error(self):
        """空文字列は ValidationError になること"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message",) for e in errors)

    def test_message_max_length_boundary(self):
        """2000文字ちょうどは許容されること"""
        req = ChatRequest(message="a" * 2000)
        assert len(req.message) == 2000

    def test_message_exceeds_max_length(self):
        """2001文字以上は ValidationError になること"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="a" * 2001)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message",) for e in errors)

    def test_message_min_length_boundary(self):
        """1文字は許容されること"""
        req = ChatRequest(message="x")
        assert req.message == "x"

    def test_invalid_thread_id_raises_error(self):
        """不正な thread_id は ValidationError になること"""
        with pytest.raises(ValidationError):
            ChatRequest(message="テスト", thread_id="not-a-uuid")


# ---------------------------------------------------------------------------
# ChatStartResponse テスト
# ---------------------------------------------------------------------------


class TestChatStartResponse:
    def test_valid_creation(self):
        """正常なレスポンスが作成できること"""
        resp = ChatStartResponse(thread_id="thread-xyz-789")
        assert resp.thread_id == "thread-xyz-789"
        assert resp.status == "streaming"

    def test_custom_status(self):
        """status を明示的に指定できること"""
        resp = ChatStartResponse(thread_id="t-001", status="started")
        assert resp.status == "started"


# ---------------------------------------------------------------------------
# StreamEventType テスト
# ---------------------------------------------------------------------------


class TestStreamEventType:
    def test_enum_values(self):
        """すべての列挙値が正しいこと"""
        assert StreamEventType.TOKEN == "token"
        assert StreamEventType.HITL_REQUEST == "hitl_request"
        assert StreamEventType.MESSAGE_COMPLETE == "message_complete"
        assert StreamEventType.ERROR == "error"
        assert StreamEventType.DONE == "done"
        assert StreamEventType.TOOL_START == "tool_start"
        assert StreamEventType.TOOL_END == "tool_end"

    def test_string_inheritance(self):
        """StreamEventType が str のサブクラスであること"""
        assert isinstance(StreamEventType.TOKEN, str)


# ---------------------------------------------------------------------------
# StreamEvent テスト
# ---------------------------------------------------------------------------


class TestStreamEvent:
    def test_token_event(self):
        """TOKEN イベントが作成できること"""
        event = StreamEvent(type=StreamEventType.TOKEN, content="Hello")
        assert event.type == StreamEventType.TOKEN
        assert event.content == "Hello"
        assert event.request_id is None

    def test_hitl_request_event(self):
        """HITL_REQUEST イベントが作成できること"""
        event = StreamEvent(
            type=StreamEventType.HITL_REQUEST,
            request_id="req-001",
            question="どの製品をお探しですか？",
            options=["製品A", "製品B", "製品C"],
            input_type="buttons",
        )
        assert event.type == StreamEventType.HITL_REQUEST
        assert event.request_id == "req-001"
        assert event.question == "どの製品をお探しですか？"
        assert event.options == ["製品A", "製品B", "製品C"]
        assert event.input_type == "buttons"

    def test_error_event(self):
        """ERROR イベントが作成できること"""
        event = StreamEvent(type=StreamEventType.ERROR, content="Internal server error")
        assert event.type == StreamEventType.ERROR
        assert event.content == "Internal server error"

    def test_done_event(self):
        """DONE イベントが作成できること"""
        event = StreamEvent(type=StreamEventType.DONE)
        assert event.type == StreamEventType.DONE
        assert event.content is None

    def test_message_complete_event(self):
        """MESSAGE_COMPLETE イベントが作成できること"""
        event = StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            content="回答が完了しました。",
        )
        assert event.type == StreamEventType.MESSAGE_COMPLETE

    def test_tool_start_event(self):
        """TOOL_START イベントが作成できること"""
        event = StreamEvent(type=StreamEventType.TOOL_START, tool_name="vector_search")
        assert event.type == StreamEventType.TOOL_START
        assert event.tool_name == "vector_search"

    def test_tool_end_event(self):
        """TOOL_END イベントが作成できること"""
        event = StreamEvent(type=StreamEventType.TOOL_END, tool_name="vector_search")
        assert event.type == StreamEventType.TOOL_END
        assert event.tool_name == "vector_search"

    def test_string_type_coercion(self):
        """文字列でタイプを指定できること（str Enum の利点）"""
        event = StreamEvent(type="token", content="test")
        assert event.type == StreamEventType.TOKEN

    def test_all_fields_optional_except_type(self):
        """type 以外はすべて省略可能であること"""
        event = StreamEvent(type=StreamEventType.DONE)
        assert event.content is None
        assert event.request_id is None
        assert event.question is None
        assert event.options is None
        assert event.input_type is None
        assert event.tool_name is None


# ---------------------------------------------------------------------------
# HITLRequest テスト
# ---------------------------------------------------------------------------


class TestHITLRequest:
    def test_valid_with_options(self):
        """選択肢ありの正常な HITL リクエストが作成できること"""
        req = HITLRequest(
            request_id="req-001",
            question="カテゴリを選択してください",
            options=["技術サポート", "請求", "一般"],
            input_type="buttons",
        )
        assert req.request_id == "req-001"
        assert req.question == "カテゴリを選択してください"
        assert req.options == ["技術サポート", "請求", "一般"]
        assert req.input_type == "buttons"

    def test_valid_text_input(self):
        """テキスト入力タイプの HITL リクエストが作成できること"""
        req = HITLRequest(
            request_id="req-002",
            question="詳細を教えてください",
            input_type="text",
        )
        assert req.options is None
        assert req.input_type == "text"

    def test_default_input_type(self):
        """デフォルトの input_type が 'buttons' であること"""
        req = HITLRequest(request_id="req-003", question="どれを選びますか？")
        assert req.input_type == "buttons"


# ---------------------------------------------------------------------------
# HITLResponse テスト
# ---------------------------------------------------------------------------


class TestHITLResponse:
    def test_valid_response(self):
        """正常な HITL レスポンスが作成できること"""
        resp = HITLResponse(request_id="req-001", response="技術サポート")
        assert resp.request_id == "req-001"
        assert resp.response == "技術サポート"

    def test_empty_response_raises_error(self):
        """空文字列の response は ValidationError になること"""
        with pytest.raises(ValidationError) as exc_info:
            HITLResponse(request_id="req-001", response="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("response",) for e in errors)


# ---------------------------------------------------------------------------
# ResumeRequest テスト
# ---------------------------------------------------------------------------


class TestResumeRequest:
    def test_valid_resume_request(self):
        """正常な再開リクエストが作成できること"""
        req = ResumeRequest(request_id="req-001", response="はい")
        assert req.request_id == "req-001"
        assert req.response == "はい"

    def test_empty_response_raises_error(self):
        """空文字列の response は ValidationError になること"""
        with pytest.raises(ValidationError) as exc_info:
            ResumeRequest(request_id="req-001", response="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("response",) for e in errors)


# ---------------------------------------------------------------------------
# AgentState テスト
# ---------------------------------------------------------------------------


class TestAgentState:
    def test_typed_dict_keys(self):
        """AgentState が必要なキーを持つ TypedDict であること"""
        annotations = AgentState.__annotations__
        expected_keys = {
            "messages",
            "thread_id",
            "query_category",
            "rewritten_query",
            "search_results",
            "relevance_score",
            "generated_answer",
            "quality_check_passed",
        }
        assert expected_keys.issubset(set(annotations.keys()))

    def test_agent_state_creation(self):
        """AgentState インスタンスを辞書として作成できること"""
        state: AgentState = {
            "messages": [],
            "thread_id": "thread-001",
            "query_category": "technical",
            "rewritten_query": "製品の設定方法は？",
            "search_results": [],
            "relevance_score": 0.85,
            "generated_answer": "設定方法は以下の通りです...",
            "quality_check_passed": True,
        }
        assert state["thread_id"] == "thread-001"
        assert state["relevance_score"] == 0.85
        assert state["quality_check_passed"] is True

    def test_search_results_is_list_of_dicts(self):
        """search_results が dict のリストを格納できること"""
        state: AgentState = {
            "messages": [],
            "thread_id": "t-001",
            "query_category": "",
            "rewritten_query": "",
            "search_results": [
                {"id": "doc-1", "content": "サンプル内容", "score": 0.9},
                {"id": "doc-2", "content": "別の内容", "score": 0.7},
            ],
            "relevance_score": 0.0,
            "generated_answer": "",
            "quality_check_passed": False,
        }
        assert len(state["search_results"]) == 2
        assert state["search_results"][0]["id"] == "doc-1"


# ---------------------------------------------------------------------------
# MEDIUM問題修正テスト（#15: ChatRequest.channel）
# ---------------------------------------------------------------------------

class TestChatRequestChannelValidation:
    """ChatRequest.channel バリデーションテスト（#15）"""

    def test_channel_with_normal_value_is_valid(self):
        """通常のチャネル値は有効"""
        from app.models.chat import ChatRequest
        request = ChatRequest(message="test", channel="slack")
        assert request.channel == "slack"

    def test_channel_too_long_is_rejected(self):
        """チャネル値が長すぎる場合はバリデーションエラー"""
        from pydantic import ValidationError
        from app.models.chat import ChatRequest
        try:
            ChatRequest(message="test", channel="a" * 100)
            assert False, "Should raise ValidationError"
        except ValidationError:
            pass

    def test_channel_none_is_valid(self):
        """チャネルがNoneの場合は有効"""
        from app.models.chat import ChatRequest
        request = ChatRequest(message="test", channel=None)
        assert request.channel is None
