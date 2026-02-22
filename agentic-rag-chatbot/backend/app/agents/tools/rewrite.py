from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.llm_factory import get_llm


@tool
def rewrite_query(query: str, conversation_context: str = "") -> str:
    """ユーザーの質問をRAG検索に最適化された形にリライトします。

    会話の文脈を考慮し、代名詞の解決や曖昧な表現の具体化を行います。

    Args:
        query: ユーザーの現在の質問
        conversation_context: 直前の会話コンテキスト（任意）

    Returns:
        リライトされた検索クエリ
    """
    llm = get_llm(temperature=0.0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """あなたは検索クエリの最適化エキスパートです。
ユーザーの質問を、ナレッジベース検索に最適な形にリライトしてください。

ルール:
1. 代名詞（「それ」「これ」「あれ」）を具体的な名詞に置換
2. 曖昧な表現を具体化
3. 検索に不要な敬語やフィラーを除去
4. 会話コンテキストがある場合、前の話題を考慮
5. リライト結果のみを出力（説明不要）"""),
        ("human", "会話コンテキスト:\n{conversation_context}\n\nユーザーの質問: {query}"),
    ])

    effective_context = conversation_context if conversation_context else "（なし）"
    response = (prompt | llm).invoke({"query": query, "conversation_context": effective_context})
    rewritten = response.content.strip()

    if len(rewritten) < 3:
        return query

    return rewritten
