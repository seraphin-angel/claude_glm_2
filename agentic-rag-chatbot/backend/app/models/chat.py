from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """チャットリクエスト"""

    message: str = Field(..., min_length=1, max_length=2000, description="ユーザーメッセージ")
    thread_id: UUID | None = Field(None, description="既存スレッドID（新規の場合はNone）")


class ChatStartResponse(BaseModel):
    """チャット開始レスポンス"""

    thread_id: str = Field(..., description="スレッドID")
    status: str = Field(default="streaming", description="ステータス")
