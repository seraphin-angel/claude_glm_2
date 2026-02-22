from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.types import interrupt

from app.agents.llm_factory import get_llm
from app.agents.output_models import ClassifyOutput


@tool
def classify_query(query: str) -> dict:
    """ユーザーの質問を分類し、適切なカテゴリを判定します。

    カテゴリ:
    - 操作方法: 製品の使い方や設定に関する質問
    - 障害・トラブル: エラーや不具合に関する質問
    - 契約・料金: プラン、料金、契約に関する質問
    - その他: 上記に分類できない製品関連の質問
    - out_of_scope: 製品サポートの範囲外の質問
    - unclear: 質問が曖昧で分類できない場合

    Args:
        query: ユーザーの質問文

    Returns:
        分類結果を含む辞書（category, confidence, needs_clarification）
    """
    llm = get_llm(temperature=0.0)
    structured_llm = llm.with_structured_output(ClassifyOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """あなたは製品サポートの質問分類エキスパートです。
ユーザーの質問を以下のカテゴリから1つ選んで分類してください。

- 操作方法: 製品の使い方、設定方法、機能の説明
- 障害・トラブル: エラー、不具合、動作しない等の問題
- 契約・料金: プラン、料金、契約期間、解約、請求
- その他: 上記に分類できないが製品に関連する質問
- out_of_scope: 製品サポートと無関係（天気、ニュース等）
- unclear: 質問が曖昧で何を聞いているか不明"""),
        ("human", "{query}"),
    ])

    try:
        result = (prompt | structured_llm).invoke({"query": query})
    except Exception:
        result = ClassifyOutput(category="unclear", confidence=0.0, reason="分類に失敗しました")

    category = result.category
    confidence = result.confidence

    if category == "unclear" or confidence < 0.6:
        human_response = interrupt({
            "question": "ご質問の内容を詳しく教えていただけますか？以下のどのカテゴリに関するお問い合わせですか？",
            "options": ["操作方法", "障害・トラブル", "契約・料金", "その他"],
            "input_type": "buttons",
        })
        return {
            "category": human_response,
            "confidence": 1.0,
            "source": "human_clarification",
        }

    if category == "out_of_scope":
        return {
            "category": "out_of_scope",
            "confidence": confidence,
            "reason": result.reason or "製品サポートの範囲外です",
        }

    return {
        "category": category,
        "confidence": confidence,
        "reason": result.reason or "",
    }
