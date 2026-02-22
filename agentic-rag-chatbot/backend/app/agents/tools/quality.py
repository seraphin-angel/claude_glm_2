from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.llm_factory import get_llm
from app.agents.output_models import QualityOutput


@tool
def check_quality(query: str, answer: str, source_documents: list[dict]) -> dict:
    """生成された回答の品質をチェックします。

    ハルシネーション（参考情報にない内容の捏造）と充足性（質問への回答として十分か）を評価。

    Args:
        query: ユーザーの元の質問
        answer: 生成された回答
        source_documents: 回答生成に使用したドキュメント

    Returns:
        品質チェック結果（passed, hallucination_score, sufficiency_score, issues）
    """
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(QualityOutput)

    context = "\n".join(doc.get("content", "") for doc in source_documents)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """あなたは回答品質の評価エキスパートです。以下の回答を評価してください。

以下の2つの観点で評価してください:

1. ハルシネーション評価 (hallucination_score: 0.0-1.0)
   - 1.0: 回答が完全に参考情報に基づいている
   - 0.5: 一部に参考情報にない推測が含まれる
   - 0.0: 大部分が参考情報にない捏造

2. 充足性評価 (sufficiency_score: 0.0-1.0)
   - 1.0: ユーザーの質問に完全に回答できている
   - 0.5: 部分的にしか回答できていない
   - 0.0: 質問に全く回答できていない"""),
        ("human", "ユーザーの質問: {query}\n\n生成された回答:\n{answer}\n\n参考情報（ソースドキュメント）:\n{context}"),
    ])

    try:
        result = (prompt | structured_llm).invoke({"query": query, "answer": answer, "context": context})
    except Exception:
        return {
            "passed": False,
            "hallucination_score": 0.0,
            "sufficiency_score": 0.0,
            "issues": ["品質チェックのレスポンスが解析できませんでした"],
            "suggestions": "品質チェックのパースに失敗したため、デフォルト値を使用",
        }

    hallucination_score = result.hallucination_score
    sufficiency_score = result.sufficiency_score
    passed = hallucination_score >= 0.6 and sufficiency_score >= 0.6

    return {
        "passed": passed,
        "hallucination_score": hallucination_score,
        "sufficiency_score": sufficiency_score,
        "issues": result.issues,
        "suggestions": result.suggestions or "",
    }
