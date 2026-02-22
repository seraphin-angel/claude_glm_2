from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Deep Agent の状態定義"""

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    query_category: str
    rewritten_query: str
    search_results: list[dict]
    relevance_score: float
    generated_answer: str
    quality_check_passed: bool
