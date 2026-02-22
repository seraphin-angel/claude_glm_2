from app.rag.vector_store import VectorStore


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
