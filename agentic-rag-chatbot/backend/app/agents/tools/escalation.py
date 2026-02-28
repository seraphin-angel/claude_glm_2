"""エスカレーションツール - 有人サポートへの問題委譲"""

from typing import Any

from langchain_core.tools import ToolException, tool
from pydantic import BaseModel, Field

from app.services.escalation_service import EscalationService


class EscalationInput(BaseModel):
    """エスカレーション入力モデル"""

    reason: str = Field(
        description="エスカレーションの理由（例: ユーザーが有人対応を希望、技術的に解決不可能）"
    )
    urgency: str = Field(
        description="緊急度: low（低）, medium（中）, high（高）"
    )
    summary: str = Field(
        default="",
        description="会話の要約（空の場合は自動生成されます）"
    )


def get_conversation_history() -> list[dict[str, str]] | None:
    """現在のセッションから会話履歴を取得する。

    Note: 実際のセッション管理システムと連携する必要があります。
    現在は簡易実装としてNoneを返します。
    """
    # NOTE: 会話履歴の自動取得は未実装です（制限事項としてREADMEに記載済み）
    return None


@tool("escalate_to_human", args_schema=EscalationInput)
def escalate_to_human(
    reason: str,
    urgency: str,
    summary: str = "",
) -> str:
    """解決できない問題を有人サポートにエスカレーションします。

    このツールは以下の場合に使用してください:
    - ユーザーが明示的に有人対応を希望した場合
    - 技術的に解決不可能な問題（バグ、システム障害など）
    - 法的・金銭的な重要事項（返金、契約解除など）
    - ユーザーが同じ質問を3回以上繰り返している場合

    Args:
        reason: エスカレーションの理由
        urgency: 緊急度 (low, medium, high)
        summary: 会話の要約（空の場合は自動生成）

    Returns:
        エスカレーション完了メッセージ（チケットID含む）

    Raises:
        ToolException: エスカレーション処理に失敗した場合
    """
    try:
        service = EscalationService.get_instance()

        # 会話履歴を取得（サマリー自動生成用）
        conversation_history = get_conversation_history()

        # チケット作成
        ticket = service.create_ticket(
            reason=reason,
            urgency=urgency,
            summary=summary,
            conversation_history=conversation_history,
        )

        return (
            f"エスカレーションを受け付けました。\n"
            f"チケットID: {ticket['id']}\n"
            f"担当者より折り返しご連絡いたします。"
        )

    except ValueError as e:
        raise ToolException(f"入力値エラー: {e}") from e
    except Exception as e:
        raise ToolException(f"エスカレーション処理エラー: {e}") from e
