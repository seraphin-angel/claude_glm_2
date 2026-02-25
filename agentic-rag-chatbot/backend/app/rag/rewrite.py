"""Multi-Query / HyDE による検索クエリ拡張モジュール

このモジュールは以下の機能を提供:
- Multi-Query: 1つのクエリから複数のバリエーションを生成
- HyDE (Hypothetical Document Embeddings): 仮説的回答を生成して検索に使用
"""

from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm_factory import get_llm
from app.core.logging import get_logger

logger = get_logger(__name__)

# Multi-Query 用プロンプト
_MULTI_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたは検索クエリの拡張エキスパートです。
ユーザーの質問から、同じ意味を表す異なる表現のクエリを{n}個生成してください。

ルール:
1. 元の質問の意図を保つ
2. 異なる単語や表現を使用する
3. 検索に適した簡潔な表現にする
4. 1行に1つのクエリを記述
5. 番号付きで出力（例: 1. クエリ1）
6. 元のクエリもバリエーションに含める"""),
    ("human", "元の質問: {query}\n\n{n}個の検索クエリバリエーションを生成してください:"),
])

# HyDE 用プロンプト
_HYDE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """あなたはナレッジベースの専門家です。
ユーザーの質問に対する「理想的な回答文書」を生成してください。

ルール:
1. 質問に対して完全で正確な回答を書く
2. 専門用語を適切に使用
3. 具体的な詳細を含める
4. 回答文書のみを出力（説明不要）"""),
    ("human", "質問: {query}\n\n理想的な回答文書を生成してください:"),
])


def rewrite_query_multi(query: str, n: int = 3) -> list[str]:
    """Multi-Query: 質問を複数のバリエーションに展開する

    Args:
        query: 元の検索クエリ
        n: 生成するクエリの数（デフォルト: 3）

    Returns:
        生成されたクエリバリエーションのリスト
        エラー時は元のクエリのみを含むリストを返す
    """
    try:
        llm = get_llm(temperature=0.3)
        chain = _MULTI_QUERY_PROMPT | llm

        response = chain.invoke({"query": query, "n": n})
        content = response.content.strip()

        if not content:
            logger.warning("multi_query_empty_response", query=query)
            return [query]

        # 番号付きリストをパース
        variations = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # "1. クエリ" 形式から番号を除去
            if line[0].isdigit() and "." in line:
                line = line.split(".", 1)[1].strip()
            if line:
                variations.append(line)

        if not variations:
            return [query]

        # 元のクエリが含まれていない場合は追加
        if query not in variations:
            variations.insert(0, query)

        logger.info(
            "multi_query_generated",
            original_query=query,
            variations_count=len(variations),
        )

        return variations[:n]  # 指定数に制限

    except Exception as e:
        logger.error("multi_query_error", query=query, error=str(e))
        return [query]


def rewrite_query_hyde(query: str) -> str:
    """HyDE (Hypothetical Document Embeddings): 仮説的回答文書を生成する

    生成された仮説回答は、元のクエリよりも関連文書と類似した
    埋め込みを持つ可能性が高く、検索リコールの向上が期待できる。

    Args:
        query: 元の検索クエリ

    Returns:
        生成された仮説的回答文書
        エラー時は元のクエリを返す
    """
    try:
        llm = get_llm(temperature=0.5)
        chain = _HYDE_PROMPT | llm

        response = chain.invoke({"query": query})
        hypothetical_answer = response.content.strip()

        if not hypothetical_answer or len(hypothetical_answer) < 10:
            logger.warning("hyde_short_response", query=query)
            return query

        logger.info(
            "hyde_generated",
            original_query=query,
            answer_length=len(hypothetical_answer),
        )

        return hypothetical_answer

    except Exception as e:
        logger.error("hyde_error", query=query, error=str(e))
        return query
