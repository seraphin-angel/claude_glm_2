"""P3-53: マルチチャネル対応 - データモデル"""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    """サポートするチャネルタイプ"""
    SLACK = "slack"
    LINE = "line"
    EMAIL = "email"
    WEB = "web"  # 既存のWebチャット


class ChannelMessage(BaseModel):
    """チャネルメッセージの統一データモデル"""

    model_config = {"frozen": True}

    channel: ChannelType
    channel_message_id: str = Field(..., description="チャネル固有のメッセージID")
    channel_thread_id: Optional[str] = Field(None, description="チャネル固有のスレッドID")
    sender_id: str = Field(..., description="送信者ID（チャネル固有）")
    sender_name: Optional[str] = Field(None, description="送信者名")
    content: str = Field(..., description="メッセージ本文")
    timestamp: str = Field(..., description="メッセージタイムスタンプ（ISO 8601）")
    metadata: Optional[dict[str, Any]] = Field(None, description="チャネル固有のメタデータ")


class ChannelConfig(BaseModel):
    """チャネル設定"""

    model_config = {"frozen": True}

    channel: ChannelType
    tenant_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ThreadMapping(BaseModel):
    """チャネル間スレッドマッピング"""

    model_config = {"frozen": True}

    internal_thread_id: UUID = Field(..., description="内部スレッドID（UUID）")
    channel: ChannelType
    channel_thread_id: str = Field(..., description="チャネル固有のスレッドID")
    channel_message_id: Optional[str] = Field(None, description="開始メッセージID")
