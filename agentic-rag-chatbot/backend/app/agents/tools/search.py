from langchain_core.tools import tool

from app.rag.retriever import retrieve_documents


@tool
def search_knowledge(query: str, category: str | None = None, n_results: int = 5) -> list[dict]:
    """製品サポートのナレッジベースから関連情報を検索します。

    Args:
        query: 検索クエリ
        category: カテゴリでフィルタ（操作方法、障害・トラブル、契約・料金、その他）。None の場合は全カテゴリから検索。
        n_results: 返す結果の数（デフォルト5）

    Returns:
        検索結果のリスト。各結果は content, metadata, relevance_score, id を含む。
    """
    results = retrieve_documents(
        query=query,
        n_results=n_results,
        category=category,
    )

    if not results:
        return [{"content": "関連するドキュメントが見つかりませんでした。", "metadata": {}, "relevance_score": 0.0, "id": "none"}]

    return results
