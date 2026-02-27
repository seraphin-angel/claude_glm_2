"""P3-53: マルチチャネル対応 - チャネル管理サービス"""

from threading import Lock
from typing import Any, Optional
from uuid import UUID, uuid4

from app.channels.base import BaseChannelAdapter
from app.channels.models import ChannelType, ThreadMapping


class ChannelService:
    """チャネル管理サービス。

    テナント・チャネルごとにアダプターを管理し、
    チャネル間スレッドマッピングを提供する。
    """

    _instance: Optional["ChannelService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        # (tenant_id, channel_type) -> adapter の辞書（不変パターン）
        self._adapters: dict[tuple[str, ChannelType], BaseChannelAdapter] = {}
        # 内部スレッドID -> ThreadMapping の辞書
        self._thread_mappings: dict[UUID, ThreadMapping] = {}
        # (channel_type, channel_thread_id) -> internal_thread_id の逆引き
        self._channel_to_internal: dict[tuple[ChannelType, str], UUID] = {}
        # インスタンスレベルのロック（スレッドセーフティ用）
        self._data_lock: Lock = Lock()

    @classmethod
    def get_instance(cls) -> "ChannelService":
        """シングルトンインスタンスを取得する。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンをリセットする（テスト用）。"""
        with cls._lock:
            cls._instance = None

    def register_adapter(
        self,
        tenant_id: str,
        channel: ChannelType,
        adapter: BaseChannelAdapter,
    ) -> None:
        """テナント・チャネルにアダプターを登録する。

        Args:
            tenant_id: テナントID
            channel: チャネルタイプ
            adapter: チャネルアダプター
        """
        with self._data_lock:
            # 不変パターン: 新しい辞書を作成
            self._adapters = {
                **self._adapters,
                (tenant_id, channel): adapter,
            }

    def get_adapter(
        self,
        tenant_id: str,
        channel: ChannelType,
    ) -> Optional[BaseChannelAdapter]:
        """テナント・チャネルのアダプターを取得する。

        Args:
            tenant_id: テナントID
            channel: チャネルタイプ

        Returns:
            アダプター（登録されていない場合はNone）
        """
        return self._adapters.get((tenant_id, channel))

    def unregister_adapter(
        self,
        tenant_id: str,
        channel: ChannelType,
    ) -> bool:
        """テナント・チャネルのアダプター登録を解除する。

        Args:
            tenant_id: テナントID
            channel: チャネルタイプ

        Returns:
            解除成功した場合はTrue
        """
        with self._data_lock:
            key = (tenant_id, channel)
            if key not in self._adapters:
                return False
            # 不変パターン: 当該キーを除いた新しい辞書を作成
            self._adapters = {
                k: v for k, v in self._adapters.items() if k != key
            }
            return True

    def list_registered_channels(self, tenant_id: str) -> list[ChannelType]:
        """テナントに登録されているチャネル一覧を取得する。

        Args:
            tenant_id: テナントID

        Returns:
            チャネルタイプのリスト
        """
        return [
            channel
            for (tid, channel) in self._adapters.keys()
            if tid == tenant_id
        ]

    async def create_thread_mapping(
        self,
        channel: ChannelType,
        channel_thread_id: str,
        channel_message_id: Optional[str] = None,
    ) -> ThreadMapping:
        """チャネルスレッドと内部スレッドのマッピングを作成する。

        Args:
            channel: チャネルタイプ
            channel_thread_id: チャネル固有のスレッドID
            channel_message_id: チャネル固有のメッセージID

        Returns:
            作成されたThreadMapping
        """
        with self._data_lock:
            # 既存のマッピングがあればそれを返す
            existing = self._channel_to_internal.get((channel, channel_thread_id))
            if existing:
                return self._thread_mappings[existing]

            # 新しい内部スレッドIDを生成
            internal_thread_id = uuid4()

            mapping = ThreadMapping(
                internal_thread_id=internal_thread_id,
                channel=channel,
                channel_thread_id=channel_thread_id,
                channel_message_id=channel_message_id,
            )

            # 不変パターン: 新しい辞書を作成
            self._thread_mappings = {
                **self._thread_mappings,
                internal_thread_id: mapping,
            }
            self._channel_to_internal = {
                **self._channel_to_internal,
                (channel, channel_thread_id): internal_thread_id,
            }

            return mapping

    def get_internal_thread_id(
        self,
        channel: ChannelType,
        channel_thread_id: str,
    ) -> Optional[UUID]:
        """チャネルスレッドIDから内部スレッドIDを取得する。

        Args:
            channel: チャネルタイプ
            channel_thread_id: チャネル固有のスレッドID

        Returns:
            内部スレッドID（見つからない場合はNone）
        """
        return self._channel_to_internal.get((channel, channel_thread_id))

    def get_thread_mapping(self, internal_thread_id: UUID) -> Optional[ThreadMapping]:
        """内部スレッドIDからマッピング情報を取得する。

        Args:
            internal_thread_id: 内部スレッドID

        Returns:
            ThreadMapping（見つからない場合はNone）
        """
        return self._thread_mappings.get(internal_thread_id)

    async def route_to_channel(
        self,
        tenant_id: str,
        channel: ChannelType,
        recipient_id: str,
        content: str,
        thread_id: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """メッセージを適切なチャネルにルーティングする。

        Args:
            tenant_id: テナントID
            channel: チャネルタイプ
            recipient_id: 送信先ID
            content: メッセージ本文
            thread_id: チャネルスレッドID
            **kwargs: チャネル固有のオプション

        Returns:
            送信結果

        Raises:
            ValueError: アダプターが登録されていない場合
        """
        adapter = self._adapters.get((tenant_id, channel))
        if adapter is None:
            raise ValueError(
                f"No adapter registered for tenant '{tenant_id}' and channel '{channel.value}'"
            )

        return await adapter.send_message(
            recipient_id=recipient_id,
            content=content,
            thread_id=thread_id,
            **kwargs,
        )

    async def process_incoming_message(
        self,
        tenant_id: str,
        channel: ChannelType,
        event_data: dict[str, Any],
    ) -> tuple[Optional[Any], Optional[UUID]]:
        """受信メッセージを処理し、マッピングを作成する。

        Args:
            tenant_id: テナントID
            channel: チャネルタイプ
            event_data: Webhookイベントデータ

        Returns:
            (ChannelMessage, internal_thread_id) のタプル
        """
        adapter = self._adapters.get((tenant_id, channel))
        if adapter is None:
            raise ValueError(
                f"No adapter registered for tenant '{tenant_id}' and channel '{channel.value}'"
            )

        message = await adapter.parse_event(event_data)
        if message is None:
            return None, None

        # スレッドマッピングを作成または取得
        if message.channel_thread_id:
            mapping = await self.create_thread_mapping(
                channel=channel,
                channel_thread_id=message.channel_thread_id,
                channel_message_id=message.channel_message_id,
            )
            return message, mapping.internal_thread_id

        return message, None
