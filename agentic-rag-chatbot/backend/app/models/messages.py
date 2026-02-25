from enum import Enum

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """参照元ドキュメント情報"""

    id: str = Field(..., description="ドキュメントID")
    title: str = Field(default="不明", description="ドキュメントタイトル")
    section: str = Field(default="", description="セクション名")
    score: float = Field(..., description="関連度スコア (0.0-1.0)")
    snippet: str = Field(..., description="コンテンツの抜粋")


class QualityScore(BaseModel):
    """品質スコア情報"""

    is_relevant: bool = Field(..., description="関連性があるかどうか")
    confidence: float = Field(..., description="信頼度スコア (0.0-1.0)")
    reasoning: str = Field(default="", description="評価理由")


class StreamEventType(str, Enum):
    """SSE ストリームイベントタイプ"""

    TOKEN = "token"
    HITL_REQUEST = "hitl_request"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"
    DONE = "done"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    SOURCE = "source"
    QUALITY = "quality"


class StreamEvent(BaseModel):
    """SSE ストリームイベント"""

    type: StreamEventType
    content: str | None = Field(None, description="テキストコンテンツ")
    request_id: str | None = Field(None, description="HITL リクエストID")
    question: str | None = Field(None, description="HITL 質問文")
    options: list[str] | None = Field(None, description="HITL 選択肢")
    input_type: str | None = Field(None, description="HITL 入力タイプ: buttons | text")
    tool_name: str | None = Field(None, description="ツール名")
    documents: list[SourceDocument] | None = Field(None, description="参照元ドキュメント一覧")
    is_relevant: bool | None = Field(None, description="関連性があるかどうか")
    confidence: float | None = Field(None, description="信頼度スコア")
    reasoning: str | None = Field(None, description="評価理由")
