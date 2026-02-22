from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.llm_factory import get_llm


@tool
def generate_answer(query: str, relevant_documents: list[dict], category: str = "") -> str:
    """検索結果に基づいてユーザーへの回答を生成します。

    Args:
        query: ユーザーの質問
        relevant_documents: 関連ドキュメントのリスト（search_knowledge の結果）
        category: 質問カテゴリ（操作方法、障害・トラブル、契約・料金 等）

    Returns:
        生成された回答テキスト
    """
    llm = get_llm(temperature=0.3)

    context = ""
    for i, doc in enumerate(relevant_documents):
        content = doc.get("content", "")
        source = doc.get("metadata", {}).get("source", "不明")
        context += f"[参考{i+1}] (出典: {source})\n{content}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """あなたは製品サポートのカスタマーサポート担当者です。
以下の参考情報に基づいて、ユーザーの質問に丁寧に回答してください。

ルール:
1. 参考情報に含まれる内容のみを使って回答する
2. 参考情報にない内容は「確認が必要です」と案内する
3. 手順がある場合は番号付きリストで示す
4. 丁寧で分かりやすい日本語を使用する
5. 回答の最後に関連する追加情報があれば案内する"""),
        ("human", "質問カテゴリ: {category}\nユーザーの質問: {query}\n\n参考情報:\n{context}"),
    ])

    response = (prompt | llm).invoke({"query": query, "category": category, "context": context})
    return response.content.strip()
