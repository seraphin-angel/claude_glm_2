import base64
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# サポートする画像形式
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# マジックバイト定義（セキュリティ: 不正ファイルアップロード防止）
MAGIC_BYTES = {
    "image/png": bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),  # PNG signature
    "image/jpeg": bytes([0xFF, 0xD8, 0xFF]),  # JPEG SOI marker
    "image/jpg": bytes([0xFF, 0xD8, 0xFF]),  # JPEG SOI marker (alias)
    "image/gif": b"GIF",  # GIF header starts with "GIF"
    "image/webp": b"RIFF",  # WebP starts with RIFF
}


def _validate_image_magic_bytes(data: bytes, mime_type: str) -> bool:
    """画像のマジックバイトを検証（セキュリティ: 不正ファイルアップロード防止）

    Args:
        data: デコード済み画像データ
        mime_type: MIMEタイプ

    Returns:
        True if magic bytes match, False otherwise
    """
    expected_magic = MAGIC_BYTES.get(mime_type.lower())
    if expected_magic is None:
        # 不明なMIMEタイプは検証をスキップ（MIMEタイプバリデーターで既に弾かれているはず）
        return True

    # WebP special case: RIFF....WEBP
    if mime_type.lower() == "image/webp":
        if len(data) < 12:
            return False
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"

    # その他: 先頭バイトの一致を確認
    if len(data) < len(expected_magic):
        return False
    return data[:len(expected_magic)] == expected_magic


def _validate_image_magic_bytes_any(data: bytes) -> bool:
    """画像データがサポートされているいずれかの形式のマジックバイトと一致するか検証

    ChatRequestのようにMIMEタイプが提供されない場合に使用。

    Args:
        data: デコード済み画像データ

    Returns:
        True if magic bytes match any supported format, False otherwise
    """
    if len(data) < 3:
        return False

    # PNG
    if data[:8] == MAGIC_BYTES["image/png"]:
        return True

    # JPEG
    if data[:3] == MAGIC_BYTES["image/jpeg"]:
        return True

    # GIF
    if data[:3] == MAGIC_BYTES["image/gif"]:
        return True

    # WebP (RIFF....WEBP)
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True

    return False


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

        # マジックバイト検証（セキュリティ: 不正ファイルアップロード防止）
        if not _validate_image_magic_bytes_any(decoded):
            raise ValueError("無効な画像形式です（サポート形式: PNG, JPEG, GIF, WebP）")

        return v


class ImageUploadRequest(BaseModel):
    """画像アップロードリクエスト"""

    image_data: str = Field(..., description="Base64エンコードされた画像データ")
    filename: str = Field(..., min_length=1, max_length=255, description="ファイル名")
    mime_type: str = Field(..., description="MIMEタイプ")

    @field_validator("image_data")
    @classmethod
    def validate_image_data(cls, v: str) -> str:
        """画像データのバリデーション（事前チェックのみ）"""
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

    def model_post_init(self, __context):
        """モデル初期化後の追加バリデーション（マジックバイト検証）"""
        # Base64デコード（再度行う必要がある）
        try:
            decoded = base64.b64decode(self.image_data)
        except Exception:
            # 既にfield_validatorで検証済みだが、念のため
            return

        # マジックバイト検証
        if not _validate_image_magic_bytes(decoded, self.mime_type):
            raise ValueError(
                f"Invalid image format: ファイルのマジックバイトが {self.mime_type} と一致しません"
            )


class ImageUploadResponse(BaseModel):
    """画像アップロードレスポンス"""

    image_id: str = Field(..., description="画像ID")
    status: str = Field(default="uploaded", description="ステータス")


class ChatStartResponse(BaseModel):
    """チャット開始レスポンス"""

    thread_id: str = Field(..., description="スレッドID")
    status: str = Field(default="streaming", description="ステータス")
