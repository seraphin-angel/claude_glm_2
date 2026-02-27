"""P3-53: マルチチャネル対応 - Slack アダプター"""

import hashlib
import hmac
import logging
import time
from typing import Any, Optional

import httpx

from app.channels.base import BaseChannelAdapter
from app.channels.models import ChannelMessage, ChannelType

logger = logging.getLogger(__name__)


class SlackAdapter(BaseChannelAdapter):
    """Slack Webhook アダプター。

    Slack API を使用してメッセージの送受信を行う。
    """

    API_BASE_URL = "https://slack.com/api"

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
    ):
        """Slack アダプターを初期化する。

        Args:
            bot_token: Slack Bot User OAuth Token (xoxb-...)
            signing_secret: Slack Signing Secret
        """
        self._bot_token = bot_token
        self._signing_secret = signing_secret

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.SLACK

    async def send_message(
        self,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Slack にメッセージを送信する。

        Args:
            recipient_id: チャネルID (C...) またはユーザーID (U...)
            content: メッセージ本文
            thread_id: 親メッセージのタイムスタンプ（スレッド返信の場合）

        Returns:
            送信結果
        """
        headers = {
            "Authorization": f"Bearer {self._bot_token}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "channel": recipient_id,
            "text": content,
        }

        if thread_id:
            payload["thread_ts"] = thread_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/chat.postMessage",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Slack send_message HTTP error: status=%s url=%s",
                e.response.status_code,
                e.request.url,
            )
            return {"success": False, "error": f"HTTP error: {e.response.status_code}"}
        except httpx.RequestError as e:
            logger.error(
                "Slack send_message request error: %s",
                type(e).__name__,
            )
            return {"success": False, "error": f"Request error: {type(e).__name__}"}

        if not data.get("ok"):
            return {
                "success": False,
                "error": data.get("error", "Unknown error"),
            }

        return {
            "success": True,
            "message_id": data["ts"],
            "thread_id": data.get("thread_ts", data["ts"]),
            "channel": data["channel"],
        }

    async def parse_event(
        self,
        event_data: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        """Slack イベントを解析する。

        Args:
            event_data: Slack Event API からのイベントデータ

        Returns:
            ChannelMessage または None
        """
        event = event_data.get("event")
        if not event or event.get("type") != "message":
            return None

        # ボットメッセージや編集イベントは無視
        if event.get("bot_id") or event.get("subtype"):
            return None

        return ChannelMessage(
            channel=ChannelType.SLACK,
            channel_message_id=event["ts"],
            channel_thread_id=event.get("thread_ts"),
            sender_id=event.get("user", "unknown"),
            sender_name=None,  # ユーザー名は別途 API で取得が必要
            content=event.get("text", ""),
            timestamp=self._ts_to_iso(event["ts"]),
            metadata={
                "channel": event.get("channel"),
                "team": event_data.get("team_id"),
            },
        )

    async def verify_signature(
        self,
        signature: str,
        body: bytes,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Slack 署名を検証する。

        Args:
            signature: X-Slack-Signature ヘッダー値
            body: リクエストボディ
            timestamp: X-Slack-Request-Timestamp ヘッダー値

        Returns:
            署名が有効なら True
        """
        if not timestamp:
            return False

        # リプレイアタック防止（5分以内のリクエストのみ許可）
        current_time = int(time.time())
        try:
            request_time = int(timestamp)
        except (ValueError, TypeError):
            return False
        if abs(current_time - request_time) > 300:
            return False

        # 署名検証
        sig_basestring = f"v0:{timestamp}:".encode() + body
        computed_signature = "v0=" + hmac.new(
            self._signing_secret.encode(),
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, computed_signature)

    async def health_check(self) -> bool:
        """Slack API への接続を確認する。"""
        headers = {
            "Authorization": f"Bearer {self._bot_token}",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/auth.test",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("ok", False)
        except httpx.HTTPStatusError as e:
            logger.error(
                "Slack health_check HTTP error: status=%s url=%s",
                e.response.status_code,
                e.request.url,
            )
            return False
        except httpx.RequestError as e:
            logger.error(
                "Slack health_check request error: %s",
                type(e).__name__,
            )
            return False
        except Exception as e:
            logger.error(
                "Slack health_check unexpected error: %s",
                type(e).__name__,
                exc_info=True,
            )
            return False

    @staticmethod
    def _ts_to_iso(ts: str) -> str:
        """Slack タイムスタンプを ISO 8601 形式に変換する。"""
        try:
            unix_time = float(ts.split(".")[0])
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(unix_time))
        except (ValueError, IndexError):
            logger.warning("_ts_to_iso: failed to parse timestamp %r, using fallback", ts)
            return "1970-01-01T00:00:00Z"
