"""P3-50: CRM/チケットシステム連携 - アダプターインターフェース定義"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class TicketPriority(str, Enum):
    """チケット優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    """チケット状態"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketData(BaseModel):
    """チケットデータモデル"""

    model_config = {"frozen": True}

    title: str
    description: str
    priority: TicketPriority
    tenant_id: str
    user_id: str
    status: TicketStatus = TicketStatus.OPEN
    metadata: Optional[dict[str, Any]] = None
    tags: list[str] = []


class BaseTicketAdapter(ABC):
    """チケットシステムアダプターの抽象基底クラス。

    各CRM/チケットシステムはこのインターフェースを実装する。
    """

    @abstractmethod
    async def create_ticket(self, ticket_data: TicketData) -> dict[str, Any]:
        """チケットを作成する。

        Args:
            ticket_data: チケットデータ

        Returns:
            作成結果（success, ticket_id を含む辞書）
        """
        ...

    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """チケットを取得する。

        Args:
            ticket_id: チケットID

        Returns:
            チケット情報（見つからない場合はNone）
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...
