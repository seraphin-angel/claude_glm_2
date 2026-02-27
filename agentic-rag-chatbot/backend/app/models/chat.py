import base64
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# サポートする画像形式
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class ChatRequest(BaseModel):
    """チャットリクエスト"""

    message: str = Field(..., min_length=1, max_length=2000, description="ユーザーメッセージ")
    thread_id: UUID | None = Field(None, description="既存スレッドID（新規の場合はNone）")
    image_data: str | None = Field(None, description="Base64エンコードされた画像データ")
    # P3-53: マルチチャネル対応
    channel: str | None = Field(None, max_length=64, description="チャネルタイプ（slack/line/email）")
    channel_thread_id: str | None = Field(None, max_length=256, description="チャネル固有のスレッドID")

    @field_validator("image_data")
    @classmethod
    def validate_image_data(cls, v: str | None) -> str | None:
        """画像データのバリデーション"""
        if v is None:
            return v
        
        # Base64デコードしてサイズチェック
        try:
            decoded = base64.b64decode(v)
        except Exception:
            raise ValueError("無効なBase64エンコードです")
        
        if len(decoded) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError("画像サイズが大きすぎます（最大10MB）")
        
        return v


class ImageUploadRequest(BaseModel):
    """画像アップロードリクエスト"""

    image_data: str = Field(..., description="Base64エンコードされた画像データ")
    filename: str = Field(..., min_length=1, max_length=255, description="ファイル名")
    mime_type: str = Field(..., description="MIMEタイプ")

    @field_validator("image_data")
    @classmethod
    def validate_image_data(cls, v: str) -> str:
        """画像データのバリデーション"""
        if not v:
            raise ValueError("画像データが必要です")
        
        # Base64デコードしてサイズチェック
        try:
            decoded = base64.b64decode(v)
        except Exception:
            raise ValueError("無効なBase64エンコードです")
        
        if len(decoded) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError("画像サイズが大きすぎます（最大10MB）")
        
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """MIMEタイプのバリデーション"""
        if v.lower() not in SUPPORTED_IMAGE_TYPES:
            supported = ", ".join(sorted(SUPPORTED_IMAGE_TYPES))
            raise ValueError(f"サポートされていない画像形式です。対応形式: {supported}")
        return v.lower()


class ImageUploadResponse(BaseModel):
    """画像アップロードレスポンス"""

    image_id: str = Field(..., description="画像ID")
    status: str = Field(default="uploaded", description="ステータス")


class ChatStartResponse(BaseModel):
    """チャット開始レスポンス"""

    thread_id: str = Field(..., description="スレッドID")
    status: str = Field(default="streaming", description="ステータス")
