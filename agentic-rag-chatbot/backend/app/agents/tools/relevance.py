import uuid

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.llm_factory import get_llm
from app.agents.output_models import RelevanceOutput
from app.config.settings import get_settings
from app.core.logging import get_logger
from app.services.gap_service import KnowledgeGapService

logger = get_logger(__name__)


@tool
def check_relevance(query: str, search_results: list[dict]) -> dict:
    """検索結果がユーザーの質問に対して十分な関連性を持つか評価します。

    Args:
        query: ユーザーの質問（リライト済み）
        search_results: search_knowledge の検索結果リスト

    Returns:
        関連性評価結果（is_relevant, score, relevant_docs, reason）
    """
    settings = get_settings()
    avg_score = sum(d.get("relevance_score", 0) for d in search_results) / max(len(search_results), 1)
    if avg_score >= settings.relevance_skip_threshold:
        return {
            "is_relevant": True,
            "score": avg_score,
            "relevant_doc_indices": list(range(len(search_results))),
            "reason": "高スコアのためLLM評価をスキップしました",
        }

    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(RelevanceOutput)

    docs_text = ""
    for i, doc in enumerate(search_results):
        content = doc.get("content", "")
        score = doc.get("relevance_score", 0)
        docs_text += f"[文書{i+1}] (スコア: {score:.2f})\n{content}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """あなたは検索結果の関連性を評価するエキスパートです。

以下を評価してください:
1. 検索結果はユーザーの質問に回答するのに十分な情報を含んでいるか
2. 関連性スコア (0.0-1.0)
3. 特に関連性の高い文書のインデックス（0始まり）"""),
        ("human", "ユーザーの質問: {query}\n\n検索結果:\n{docs_text}"),
    ])

    try:
        result = (prompt | structured_llm).invoke({"query": query, "docs_text": docs_text})
        output = {
            "is_relevant": result.is_relevant,
            "score": result.score,
            "relevant_doc_indices": result.relevant_doc_indices,
            "reason": result.reason or "",
        }
        if not output["is_relevant"]:
            KnowledgeGapService.get_instance().record_gap(query, reason=output["reason"])
        return output
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(
            "LLM relevance evaluation failed, falling back to score-based judgment",
            exc_info=True,
            error_id=error_id,
            fallback_used=True,
            error_type=type(e).__name__,
        )
        avg_score = sum(d.get("relevance_score", 0) for d in search_results) / max(len(search_results), 1)
        is_relevant = avg_score > 0.5
        fallback_reason = f"[警告] LLM評価エラー(ID:{error_id}) - 簡易判定を使用"
        if not is_relevant:
            KnowledgeGapService.get_instance().record_gap(query, reason=fallback_reason)
        return {
            "is_relevant": is_relevant,
            "score": avg_score,
            "relevant_doc_indices": list(range(len(search_results))),
            "reason": fallback_reason,
            "evaluation_error": True,
            "error_id": error_id,
        }
