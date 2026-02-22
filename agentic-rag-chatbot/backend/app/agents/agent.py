from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.agents.llm_factory import get_llm
from app.agents.prompts import PRODUCT_SUPPORT_SYSTEM_PROMPT
from app.agents.tools import (
    ask_human,
    check_quality,
    check_relevance,
    classify_query,
    generate_answer,
    rewrite_query,
    search_knowledge,
)


def build_agent(checkpointer=None):
    """製品サポート Deep Agent を構築する。

    Args:
        checkpointer: LangGraph checkpointer（デフォルトは MemorySaver）

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


def get_agent():
    """エージェントのシングルトンインスタンスを取得"""
    global _agent, _checkpointer
    if _agent is None:
        _checkpointer = MemorySaver()
        _agent = build_agent(checkpointer=_checkpointer)
    return _agent


def get_checkpointer():
    """チェックポインタのシングルトンインスタンスを取得"""
    global _checkpointer
    if _checkpointer is None:
        get_agent()
    return _checkpointer


def reset_agent():
    """エージェントをリセット（テスト用）"""
    global _agent, _checkpointer
    _agent = None
    _checkpointer = None
