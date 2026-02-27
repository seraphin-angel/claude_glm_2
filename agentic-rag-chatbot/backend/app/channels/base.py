"""P3-53: マルチチャネル対応 - アダプター基底クラス"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.channels.models import ChannelMessage, ChannelType


class BaseChannelAdapter(ABC):
    """チャネルアダプターの抽象基底クラス。

    各チャネル（Slack, LINE, Email等）はこのインターフェースを実装する。
    """

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """チャネルタイプを返す"""
        ...

    @abstractmethod
    async def send_message(
        self,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """メッセージを送信する。

        Args:
            recipient_id: 送信先ID（チャネル固有）
            content: メッセージ本文
            thread_id: スレッドID（継続会話の場合）
            **kwargs: チャネル固有のオプション

        Returns:
            送信結果（success, message_id, thread_id を含む辞書）
        """
        ...

    @abstractmethod
    async def parse_event(
        self,
        event_data: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        """Webhookイベントを解析して統一メッセージ形式に変換する。

        Args:
            event_data: Webhookからの生データ

        Returns:
            ChannelMessage（解析できない場合はNone）
        """
        ...

    @abstractmethod
    async def verify_signature(
        self,
        signature: str,
        body: bytes,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Webhook署名を検証する。

        Args:
            signature: 受信した署名
            body: リクエストボディ（生バイト）
            timestamp: タイムスタンプ（LINEなどで使用）

        Returns:
            署名が有効ならTrue
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """チャネル接続の健全性を確認する。

        Returns:
            接続が正常ならTrue
        """
        ...
