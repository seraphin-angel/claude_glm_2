"""P3-50: CRM/チケットシステム連携 - モックアダプター（テスト・開発用）"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.integrations.base import BaseTicketAdapter, TicketData, TicketStatus


class MockTicketAdapter(BaseTicketAdapter):
    """テスト・開発用のモックチケットアダプター。

    チケットはインメモリで管理し、外部システムへの接続は行わない。
    """

    def __init__(self) -> None:
        # チケットIDをキーとするインメモリストレージ（不変辞書として管理）
        self._tickets: dict[str, dict[str, Any]] = {}

    async def create_ticket(self, ticket_data: TicketData) -> dict[str, Any]:
        """チケットを作成する。

        Args:
            ticket_data: チケットデータ

        Returns:
            作成結果
        """
        ticket_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "title": ticket_data.title,
            "description": ticket_data.description,
            "priority": ticket_data.priority.value,
            "status": TicketStatus.OPEN.value,
            "tenant_id": ticket_data.tenant_id,
            "user_id": ticket_data.user_id,
            "metadata": ticket_data.metadata or {},
            "tags": list(ticket_data.tags),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 不変パターン: 新しい辞書を作成
        self._tickets = {**self._tickets, ticket_id: ticket}

        return {
            "success": True,
            "ticket_id": ticket_id,
            "adapter": "mock",
        }

    async def get_ticket(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """チケットを取得する。

        Args:
            ticket_id: チケットID

        Returns:
            チケット情報（見つからない場合はNone）
        """
        return self._tickets.get(ticket_id)

    async def update_ticket(
        self,
        ticket_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """チケットを更新する。

        Args:
            ticket_id: チケットID
            updates: 更新内容

        Returns:
            更新結果
        """
        existing = self._tickets.get(ticket_id)
        if existing is None:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        # 不変パターン: 更新済みチケットを新しい辞書で作成
        updated = {
            **existing,
            **updates,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tickets = {**self._tickets, ticket_id: updated}

        return {
            "success": True,
            "ticket_id": ticket_id,
            "adapter": "mock",
        }

    async def close_ticket(
        self,
        ticket_id: str,
        resolution: str,
    ) -> dict[str, Any]:
        """チケットをクローズする。

        Args:
            ticket_id: チケットID
            resolution: 解決内容

        Returns:
            クローズ結果
        """
        existing = self._tickets.get(ticket_id)
        if existing is None:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        closed = {
            **existing,
            "status": TicketStatus.CLOSED.value,
            "resolution": resolution,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tickets = {**self._tickets, ticket_id: closed}

        return {
            "success": True,
            "ticket_id": ticket_id,
            "adapter": "mock",
        }
