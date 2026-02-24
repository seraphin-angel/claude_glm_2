from app.config.settings import get_settings
from app.rag.bm25_store import BM25Store
from app.rag.vector_store import VectorStore

_RRF_K = 60


def retrieve_documents(
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> list[dict]:
    """ベクトルストアから関連ドキュメントを検索し整形して返す"""
    store = VectorStore.get_instance()

    where = {"category": category} if category else None
    results = store.query(query_text=query, n_results=n_results, where=where)

    documents = []
    if results and results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            distance = results["distances"][0][i] if results.get("distances") else None
            documents.append({
                "content": doc,
                "metadata": metadata,
                "relevance_score": 1.0 - (distance or 0.0),
                "id": results["ids"][0][i] if results.get("ids") else f"doc_{i}",
            })

    return documents


def hybrid_retrieve(
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> list[dict]:
    """ベクトル検索と BM25 を RRF でマージするハイブリッド検索。

    Args:
        query: 検索クエリ
        n_results: 返す結果の件数
        category: カテゴリフィルタ（None の場合は全カテゴリ）

    Returns:
        {"content": str, "metadata": dict, "relevance_score": float, "id": str} のリスト
    """
    settings = get_settings()
    alpha = settings.hybrid_search_alpha

    vector_results = retrieve_documents(query=query, n_results=n_results, category=category)

    if alpha >= 1.0:
        return vector_results

    bm25_results = BM25Store.get_instance().search(query, top_k=settings.bm25_top_k)

    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + alpha * (1.0 / (_RRF_K + rank + 1))
        doc_map[doc_id] = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 - alpha) * (1.0 / (_RRF_K + rank + 1))
        if doc_id not in doc_map:
            doc_map[doc_id] = {
                "content": doc["content"],
                "metadata": doc["metadata"],
                "relevance_score": 0.0,
                "id": doc_id,
            }

    sorted_ids = sorted(rrf_scores, key=lambda doc_id: rrf_scores[doc_id], reverse=True)[:n_results]

    return [
        {**doc_map[doc_id], "relevance_score": rrf_scores[doc_id]}
        for doc_id in sorted_ids
    ]
