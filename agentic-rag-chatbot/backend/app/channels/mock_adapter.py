"""P3-53: マルチチャネル対応 - テスト用モックアダプター"""

import hashlib
import time
from typing import Any, Optional

from app.channels.base import BaseChannelAdapter
from app.channels.models import ChannelMessage, ChannelType


class MockChannelAdapter(BaseChannelAdapter):
    """テスト用モックチャネルアダプター。"""

    def __init__(self, channel_type: ChannelType = ChannelType.WEB):
        self._channel_type = channel_type
        self._sent_messages: list[dict[str, Any]] = []

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    async def send_message(
        self,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        message_id = f"MOCK-{self._channel_type.value}-{int(time.time() * 1000)}"
        result = {
            "success": True,
            "message_id": message_id,
            "thread_id": thread_id or message_id,
            "recipient_id": recipient_id,
            "content": content,
        }
        self._sent_messages.append(result)
        return result

    async def parse_event(
        self,
        event_data: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        if not event_data:
            return None

        return ChannelMessage(
            channel=self._channel_type,
            channel_message_id=event_data.get("message_id", f"mock-{int(time.time())}"),
            channel_thread_id=event_data.get("thread_id"),
            sender_id=event_data.get("sender_id", "mock-user"),
            sender_name=event_data.get("sender_name"),
            content=event_data.get("content", ""),
            timestamp=event_data.get("timestamp", "2024-01-01T00:00:00Z"),
            metadata=event_data.get("metadata"),
        )

    async def verify_signature(
        self,
        signature: str,
        body: bytes,
        timestamp: Optional[str] = None,
    ) -> bool:
        # モックは常にTrueを返す
        return True

    async def health_check(self) -> bool:
        return True

    def get_sent_messages(self) -> list[dict[str, Any]]:
        """テスト用: 送信済みメッセージ一覧を取得"""
        return self._sent_messages.copy()

    def clear_sent_messages(self) -> None:
        """テスト用: 送信済みメッセージをクリア"""
        self._sent_messages = []
