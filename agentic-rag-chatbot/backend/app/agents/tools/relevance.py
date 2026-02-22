from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.llm_factory import get_llm
from app.agents.output_models import RelevanceOutput


@tool
def check_relevance(query: str, search_results: list[dict]) -> dict:
    """検索結果がユーザーの質問に対して十分な関連性を持つか評価します。

    Args:
        query: ユーザーの質問（リライト済み）
        search_results: search_knowledge の検索結果リスト

    Returns:
        関連性評価結果（is_relevant, score, relevant_docs, reason）
    """
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
        return {
            "is_relevant": result.is_relevant,
            "score": result.score,
            "relevant_doc_indices": result.relevant_doc_indices,
            "reason": result.reason or "",
        }
    except Exception:
        avg_score = sum(d.get("relevance_score", 0) for d in search_results) / max(len(search_results), 1)
        return {
            "is_relevant": avg_score > 0.5,
            "score": avg_score,
            "relevant_doc_indices": list(range(len(search_results))),
            "reason": "LLM評価に失敗したため、スコアベースで判定しました",
        }
