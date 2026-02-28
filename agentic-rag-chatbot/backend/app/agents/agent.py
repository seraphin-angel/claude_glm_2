import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.prompts import PRODUCT_SUPPORT_SYSTEM_PROMPT
from app.agents.tools import (
    ask_human,
    check_quality,
    check_relevance,
    classify_query,
    escalate_to_human,
    generate_answer,
    rewrite_query,
    search_knowledge,
)
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# グローバル変数で checkpointer のタイプを管理
_use_postgres = True


def build_agent(checkpointer=None):
    """製品サポート Deep Agent を構築する。

    Args:
        checkpointer: LangGraph checkpointer（デフォルトは PostgresSaver または MemorySaver）

    Returns:
        コンパイル済み LangGraph エージェント
    """
    llm = get_llm(temperature=0.1, streaming=True)

    tools = [
        classify_query,
        rewrite_query,
        search_knowledge,
        check_relevance,
        generate_answer,
        check_quality,
        ask_human,
        escalate_to_human,
    ]

    if checkpointer is None:
        checkpointer = MemorySaver()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        prompt=PRODUCT_SUPPORT_SYSTEM_PROMPT,
    )

    return agent


# シングルトンでエージェントとチェックポインタを管理
_agent = None
_checkpointer = None
_checkpointer_context = None
# Persistence health status
_persistence_healthy = True


async def get_agent():
    """エージェントのシングルトンインスタンスを取得（非同期）"""
    global _agent, _checkpointer, _checkpointer_context, _use_postgres, _persistence_healthy
    if _agent is None:
        if _use_postgres:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                settings = get_settings()
                _checkpointer = AsyncPostgresSaver.from_conn_string(
                    settings.database_url
                )
                # コンテキストマネージャとして初期化
                _checkpointer_context = await _checkpointer.__aenter__()
                # テーブルを作成（初回のみ必要）
                await _checkpointer_context.setup()
                _agent = build_agent(checkpointer=_checkpointer_context)
                _persistence_healthy = True
                logger.info("PostgresSaver initialized successfully")
            except Exception as e:
                logger.error(
                    "Failed to initialize PostgresSaver, falling back to MemorySaver. "
                    "Chat session history will NOT persist across server restarts. "
                    "THIS IS A CRITICAL DEGRADED STATE.",
                    exc_info=True,
                )
                _persistence_healthy = False
                _checkpointer = MemorySaver()
                _checkpointer_context = None
                _agent = build_agent(checkpointer=_checkpointer)
        else:
            _checkpointer = MemorySaver()
            _checkpointer_context = None
            _persistence_healthy = True  # MemorySaver is intentionally used
            _agent = build_agent(checkpointer=_checkpointer)
    return _agent


def get_checkpointer():
    """チェックポインタのシングルトンインスタンスを取得"""
    global _checkpointer
    if _checkpointer is None:
        raise RuntimeError("Agent not initialized. Call get_agent() first.")
    return _checkpointer


def is_persistence_healthy() -> bool:
    """Check if persistence layer is functioning properly.

    Returns:
        True if PostgresSaver is working or MemorySaver is intentionally used.
        False if PostgresSaver failed and fell back to MemorySaver.
    """
    return _persistence_healthy


def reset_agent():
    """エージェントをリセット（テスト用）"""
    global _agent, _checkpointer, _checkpointer_context, _persistence_healthy
    if _checkpointer_context is not None:
        # 非同期コンテキストマネージャのクリーンアップが必要だが、
        # 同期関数なのでここでは参照を解除するだけ
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # イベントループが実行中の場合は非同期でクリーンアップをスケジュール
                asyncio.create_task(_checkpointer_context.__aexit__(None, None, None))
            else:
                # イベントループが実行中でない場合は同期的に実行
                loop.run_until_complete(_checkpointer_context.__aexit__(None, None, None))
        except Exception as e:
            logger.warning(
                "Failed to cleanup checkpointer context",
                exc_info=True,
            )
    _agent = None
    _checkpointer = None
    _checkpointer_context = None
    _persistence_healthy = True  # Reset to default healthy state


def use_memory_saver():
    """テスト用: MemorySaver を使用するように設定"""
    global _use_postgres
    _use_postgres = False
    reset_agent()


def use_postgres_saver():
    """PostgresSaver を使用するように設定"""
    global _use_postgres
    _use_postgres = True
    reset_agent()
