from pydantic import BaseModel, Field


class HITLRequest(BaseModel):
    """HITL リクエスト（フロントエンドへ送信）"""

    request_id: str = Field(..., description="リクエストID")
    question: str = Field(..., description="ユーザーへの質問")
    options: list[str] | None = Field(None, description="選択肢（ボタン表示用）")
    input_type: str = Field(default="buttons", description="入力タイプ: buttons | text")


class HITLResponse(BaseModel):
    """HITL レスポンス（フロントエンドから受信）"""

    request_id: str = Field(..., description="対応するリクエストID")
    response: str = Field(..., min_length=1, description="ユーザーの回答")


class ResumeRequest(BaseModel):
    """チャット再開リクエスト"""

    request_id: str = Field(..., description="HITL リクエストID")
    response: str = Field(..., min_length=1, description="ユーザーの回答")
