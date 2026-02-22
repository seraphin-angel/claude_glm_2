from enum import Enum

from pydantic import BaseModel, Field


class StreamEventType(str, Enum):
    """SSE ストリームイベントタイプ"""

    TOKEN = "token"
    HITL_REQUEST = "hitl_request"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"
    DONE = "done"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"


class StreamEvent(BaseModel):
    """SSE ストリームイベント"""

    type: StreamEventType
    content: str | None = Field(None, description="テキストコンテンツ")
    request_id: str | None = Field(None, description="HITL リクエストID")
    question: str | None = Field(None, description="HITL 質問文")
    options: list[str] | None = Field(None, description="HITL 選択肢")
    input_type: str | None = Field(None, description="HITL 入力タイプ: buttons | text")
    tool_name: str | None = Field(None, description="ツール名")
