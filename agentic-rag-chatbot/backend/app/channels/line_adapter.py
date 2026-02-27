"""P3-53: マルチチャネル対応 - LINE アダプター"""

import base64
import time
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.channels.base import BaseChannelAdapter
from app.channels.models import ChannelMessage, ChannelType

logger = logging.getLogger(__name__)


class LineAdapter(BaseChannelAdapter):
    """LINE Messaging API アダプター。"""

    API_BASE_URL = "https://api.line.me/v2"

    def __init__(
        self,
        channel_access_token: str,
        channel_secret: str,
    ):
        """LINE アダプターを初期化する。

        Args:
            channel_access_token: LINE Channel Access Token
            channel_secret: LINE Channel Secret
        """
        self._channel_access_token = channel_access_token
        self._channel_secret = channel_secret

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.LINE

    async def send_message(
        self,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """LINE にメッセージを送信する。

        Args:
            recipient_id: LINE ユーザーID
            content: メッセージ本文
            thread_id: 未使用（LINE はスレッド未対応）

        Returns:
            送信結果
        """
        headers = {
            "Authorization": f"Bearer {self._channel_access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "to": recipient_id,
            "messages": [
                {
                    "type": "text",
                    "text": content,
                }
            ],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/bot/message/push",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "LINE send_message HTTP error: status=%s url=%s",
                e.response.status_code,
                e.request.url,
            )
            return {"success": False, "error": f"HTTP error: {e.response.status_code}"}
        except httpx.RequestError as e:
            logger.error(
                "LINE send_message request error: %s",
                type(e).__name__,
            )
            return {"success": False, "error": f"Request error: {type(e).__name__}"}

        # LINE API は成功時 sentMessages 配列を返す
        sent_messages = data.get("sentMessages", [])
        message_id = sent_messages[0]["id"] if sent_messages else None

        return {
            "success": True,
            "message_id": message_id,
            "thread_id": thread_id,  # LINE はスレッド未対応
        }

    async def parse_event(
        self,
        event_data: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        """LINE Webhook イベントを解析する。

        Args:
            event_data: LINE Webhook からのイベントデータ

        Returns:
            ChannelMessage または None
        """
        events = event_data.get("events", [])
        if not events:
            return None

        # 最初のメッセージイベントを処理
        for event in events:
            if event.get("type") != "message":
                continue

            message = event.get("message", {})
            if message.get("type") != "text":
                continue

            source = event.get("source", {})
            timestamp_ms = event.get("timestamp", 0)

            # リプレイアタック防止: 5分以上古いイベントを拒否
            if timestamp_ms > 0:
                current_time_ms = int(time.time() * 1000)
                if abs(current_time_ms - timestamp_ms) > 300_000:  # 5分 = 300,000ms
                    logger.warning(
                        "LINE event rejected: timestamp too old. "
                        "event_timestamp_ms=%d, current_ms=%d",
                        timestamp_ms,
                        current_time_ms,
                    )
                    return None

            return ChannelMessage(
                channel=ChannelType.LINE,
                channel_message_id=message.get("id", ""),
                channel_thread_id=None,  # LINE はスレッド未対応
                sender_id=source.get("userId", "unknown"),
                sender_name=None,
                content=message.get("text", ""),
                timestamp=self._ms_to_iso(timestamp_ms),
                metadata={
                    "reply_token": event.get("replyToken"),
                    "source_type": source.get("type"),
                    "group_id": source.get("groupId"),
                    "room_id": source.get("roomId"),
                },
            )

        return None

    async def verify_signature(
        self,
        signature: str,
        body: bytes,
        timestamp: Optional[str] = None,
    ) -> bool:
        """LINE 署名を検証する。

        Args:
            signature: X-Line-Signature ヘッダー値
            body: リクエストボディ
            timestamp: 未使用

        Returns:
            署名が有効なら True
        """
        computed_signature = base64.b64encode(
            hmac.new(
                self._channel_secret.encode(),
                body,
                hashlib.sha256,
            ).digest()
        ).decode()

        return hmac.compare_digest(signature, computed_signature)

    async def health_check(self) -> bool:
        """LINE API への接続を確認する。"""
        headers = {
            "Authorization": f"Bearer {self._channel_access_token}",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/bots/channel/info",
                    headers=headers,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            logger.error(
                "LINE health_check HTTP error: status=%s url=%s",
                e.response.status_code,
                e.request.url,
            )
            return False
        except httpx.RequestError as e:
            logger.error(
                "LINE health_check request error: %s",
                type(e).__name__,
            )
            return False
        except Exception as e:
            logger.error(
                "LINE health_check unexpected error: %s",
                type(e).__name__,
                exc_info=True,
            )
            return False

    @staticmethod
    def _ms_to_iso(timestamp_ms: int) -> str:
        """ミリ秒タイムスタンプを ISO 8601 形式に変換する。"""
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OSError):
            logger.warning("_ms_to_iso: failed to parse timestamp %r, using fallback", timestamp_ms)
            return "1970-01-01T00:00:00Z"
