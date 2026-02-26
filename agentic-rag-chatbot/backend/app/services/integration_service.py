"""P3-50: CRM/チケットシステム連携 - 連携サービス"""

from threading import Lock
from typing import Any, Optional

from app.integrations.base import BaseTicketAdapter, TicketData, TicketPriority


_URGENCY_TO_PRIORITY: dict[str, TicketPriority] = {
    "low": TicketPriority.LOW,
    "medium": TicketPriority.MEDIUM,
    "high": TicketPriority.HIGH,
    "critical": TicketPriority.URGENT,
}


class IntegrationService:
    """CRM/チケットシステム連携管理サービス。

    テナントごとにアダプターを管理し、チケット操作のファサードを提供する。
    """

    _instance: Optional["IntegrationService"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        # テナントIDをキーとするアダプター辞書（不変パターン）
        self._adapters: dict[str, BaseTicketAdapter] = {}

    @classmethod
    def get_instance(cls) -> "IntegrationService":
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
        adapter: BaseTicketAdapter,
    ) -> None:
        """テナントにアダプターを登録する。

        Args:
            tenant_id: テナントID
            adapter: チケットアダプター
        """
        # 不変パターン: 新しい辞書を作成
        self._adapters = {**self._adapters, tenant_id: adapter}

    def get_adapter(self, tenant_id: str) -> Optional[BaseTicketAdapter]:
        """テナントのアダプターを取得する。

        Args:
            tenant_id: テナントID

        Returns:
            アダプター（登録されていない場合はNone）
        """
        return self._adapters.get(tenant_id)

    def list_registered_tenants(self) -> list[str]:
        """アダプターが登録されているテナント一覧を取得する。

        Returns:
            テナントIDのリスト
        """
        return list(self._adapters.keys())

    def unregister_adapter(self, tenant_id: str) -> bool:
        """テナントのアダプター登録を解除する。

        Args:
            tenant_id: テナントID

        Returns:
            解除成功した場合はTrue
        """
        if tenant_id not in self._adapters:
            return False
        # 不変パターン: 当該テナントを除いた新しい辞書を作成
        self._adapters = {
            tid: adapter
            for tid, adapter in self._adapters.items()
            if tid != tenant_id
        }
        return True

    async def create_ticket(
        self,
        tenant_id: str,
        ticket_data: TicketData,
    ) -> dict[str, Any]:
        """テナントのアダプター経由でチケットを作成する。

        Args:
            tenant_id: テナントID
            ticket_data: チケットデータ

        Returns:
            作成結果

        Raises:
            ValueError: アダプターが登録されていない場合
        """
        adapter = self._adapters.get(tenant_id)
        if adapter is None:
            raise ValueError(
                f"No adapter registered for tenant '{tenant_id}'"
            )
        return await adapter.create_ticket(ticket_data)

    async def get_ticket(
        self,
        tenant_id: str,
        ticket_id: str,
    ) -> Optional[dict[str, Any]]:
        """テナントのアダプター経由でチケットを取得する。

        Args:
            tenant_id: テナントID
            ticket_id: チケットID

        Returns:
            チケット情報（見つからない場合はNone）

        Raises:
            ValueError: アダプターが登録されていない場合
        """
        adapter = self._adapters.get(tenant_id)
        if adapter is None:
            raise ValueError(
                f"No adapter registered for tenant '{tenant_id}'"
            )
        return await adapter.get_ticket(ticket_id)

    async def on_escalation(
        self,
        tenant_id: str,
        user_id: str,
        reason: str,
        urgency: str,
        summary: str,
    ) -> Optional[dict[str, Any]]:
        """エスカレーション発生時にCRMチケットを自動作成するフック。

        Args:
            tenant_id: テナントID
            user_id: ユーザーID
            reason: エスカレーション理由
            urgency: 緊急度（low/medium/high/critical）
            summary: 会話サマリー

        Returns:
            チケット作成結果（アダプター未登録の場合はNone）
        """
        adapter = self._adapters.get(tenant_id)
        if adapter is None:
            return None

        priority = _URGENCY_TO_PRIORITY.get(urgency.lower(), TicketPriority.MEDIUM)

        ticket_data = TicketData(
            title=f"[エスカレーション] {reason[:80]}",
            description=f"ユーザーID: {user_id}\n\n理由: {reason}\n\n会話サマリー:\n{summary}",
            priority=priority,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata={
                "source": "chatbot_escalation",
                "urgency": urgency,
            },
            tags=["escalation", "chatbot"],
        )

        return await adapter.create_ticket(ticket_data)
