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
                # CRITICAL: PostgresSaver initialization failed - fail fast
                logger.critical(
                    "CRITICAL: Failed to initialize PostgresSaver. "
                    "Service cannot start without persistent storage.",
                    exc_info=True,
                    extra={
                        "error_id": "PERSISTENCE_INIT_FAILED",
                        "severity": "CRITICAL",
                    },
                )
                raise RuntimeError(
                    "Database persistence unavailable. "
                    "Please check database configuration and restart the service."
                ) from e
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
    """エージェントをリセット（テスト用）

    Uses modern asyncio API (Python 3.10+):
    - asyncio.get_running_loop() instead of deprecated get_event_loop()
    - Proper RuntimeError handling when no event loop is running
    """
    global _agent, _checkpointer, _checkpointer_context, _persistence_healthy
    if _checkpointer_context is not None:
        # 非同期コンテキストマネージャのクリーンアップが必要だが、
        # 同期関数なのでここでは参照を解除するだけ
        try:
            import asyncio

            try:
                # Python 3.10+ 推奨API: 実行中のループのみを取得
                loop = asyncio.get_running_loop()
                # イベントループが実行中の場合は非同期でクリーンアップをスケジュール
                loop.create_task(_checkpointer_context.__aexit__(None, None, None))
            except RuntimeError:
                # 実行中のイベントループがない場合
                # 新しいイベントループを作成して同期的にクリーンアップを実行
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(
                        _checkpointer_context.__aexit__(None, None, None)
                    )
                finally:
                    loop.close()
        except Exception:
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
