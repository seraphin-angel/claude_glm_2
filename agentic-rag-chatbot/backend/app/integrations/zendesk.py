"""P3-50: CRM/チケットシステム連携 - Zendeskアダプター"""

from typing import Any, Optional

import httpx

from app.integrations.base import BaseTicketAdapter, TicketData, TicketPriority, TicketStatus


class ZendeskAdapter(BaseTicketAdapter):
    """Zendesk Support APIアダプター。"""

    PRIORITY_MAP: dict[TicketPriority, str] = {
        TicketPriority.LOW: "low",
        TicketPriority.MEDIUM: "normal",
        TicketPriority.HIGH: "high",
        TicketPriority.URGENT: "urgent",
    }

    def __init__(
        self,
        subdomain: str,
        email: str,
        api_token: str,
    ) -> None:
        """Zendeskアダプターを初期化する。

        Args:
            subdomain: ZendeskサブドメインURL（例: "your-company"）
            email: 認証用メールアドレス
            api_token: Zendesk APIトークン
        """
        self._base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self._auth = (f"{email}/token", api_token)

    def _map_priority(self, priority: TicketPriority) -> str:
        """優先度をZendesk形式にマッピングする。"""
        return self.PRIORITY_MAP.get(priority, "normal")

    def _build_ticket_payload(self, ticket_data: TicketData) -> dict[str, Any]:
        """Zendesk APIのチケットペイロードを構築する。"""
        return {
            "ticket": {
                "subject": ticket_data.title,
                "comment": {"body": ticket_data.description},
                "priority": self._map_priority(ticket_data.priority),
                "tags": list(ticket_data.tags),
                "custom_fields": [
                    {"id": "tenant_id", "value": ticket_data.tenant_id},
                    {"id": "user_id", "value": ticket_data.user_id},
                ],
                **({"metadata": ticket_data.metadata} if ticket_data.metadata else {}),
            }
        }

    async def create_ticket(self, ticket_data: TicketData) -> dict[str, Any]:
        """Zendeskにチケットを作成する。

        Args:
            ticket_data: チケットデータ

        Returns:
            作成結果
        """
        payload = self._build_ticket_payload(ticket_data)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/tickets.json",
                json=payload,
                auth=self._auth,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        ticket_id = str(data["ticket"]["id"])
        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": data["ticket"].get("status", "new"),
            "adapter": "zendesk",
        }

    async def get_ticket(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """Zendeskからチケットを取得する。

        Args:
            ticket_id: チケットID

        Returns:
            チケット情報（見つからない場合はNone）
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}/tickets/{ticket_id}.json",
                auth=self._auth,
                timeout=30.0,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        ticket = data["ticket"]
        return {
            "ticket_id": str(ticket["id"]),
            "title": ticket.get("subject", ""),
            "status": ticket.get("status", ""),
            "priority": ticket.get("priority", ""),
            "adapter": "zendesk",
        }

    async def update_ticket(
        self,
        ticket_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Zendeskのチケットを更新する。

        Args:
            ticket_id: チケットID
            updates: 更新内容

        Returns:
            更新結果
        """
        payload: dict[str, Any] = {"ticket": {}}

        if "status" in updates:
            payload["ticket"]["status"] = updates["status"]
        if "comment" in updates:
            payload["ticket"]["comment"] = {"body": updates["comment"], "public": False}
        if "priority" in updates:
            payload["ticket"]["priority"] = updates["priority"]

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self._base_url}/tickets/{ticket_id}.json",
                json=payload,
                auth=self._auth,
                timeout=30.0,
            )
            response.raise_for_status()

        return {
            "success": True,
            "ticket_id": ticket_id,
            "adapter": "zendesk",
        }

    async def close_ticket(
        self,
        ticket_id: str,
        resolution: str,
    ) -> dict[str, Any]:
        """Zendeskのチケットをクローズする。

        Args:
            ticket_id: チケットID
            resolution: 解決内容

        Returns:
            クローズ結果
        """
        return await self.update_ticket(
            ticket_id,
            {
                "status": "closed",
                "comment": resolution,
            },
        )
