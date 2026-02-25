import logging
from typing import Any

from app.config.settings import get_settings
from app.rag.bm25_store import BM25Store
from app.rag.rewrite import rewrite_query_hyde, rewrite_query_multi
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

_RRF_K = 60


class CrossEncoderReranker:
    """Cross-Encoder モデルを使用したリランキングクラス。

    シングルトンパターンでモデルを管理し、メモリ使用量を最適化する。
    """

    _instance: "CrossEncoderReranker | None" = None
    _model: Any = None  # CrossEncoder 型（遅延インポート）

    def __init__(self) -> None:
        """初期化は get_instance() 経由でのみ行う。"""
        if CrossEncoderReranker._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")

    @classmethod
    def get_instance(cls) -> "CrossEncoderReranker":
        """シングルトンインスタンスを取得する。"""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンインスタンスをリセットする（テスト用）。"""
        cls._instance = None
        cls._model = None

    def _load_model(self) -> Any:
        """Cross-Encoder モデルを遅延ロードする。"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                settings = get_settings()
                model_name = settings.reranker_model
                logger.info(f"Loading Cross-Encoder model: {model_name}")
                self._model = CrossEncoder(model_name)
                logger.info("Cross-Encoder model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Cross-Encoder model: {e}")
                raise
        return self._model

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """クエリとドキュメントをリランキングする。

        Args:
            query: 検索クエリ
            documents: ドキュメントのリスト（各ドキュメントは id, content, metadata を含む）
            top_k: 返す結果の件数

        Returns:
            リランキングされたドキュメントのリスト（rerank_score を含む）
        """
        if not documents:
            return []

        model = self._load_model()

        # クエリとドキュメントのペアを作成
        pairs = [(query, doc["content"]) for doc in documents]

        # スコアを計算
        scores = model.predict(pairs)

        # ドキュメントにスコアを付与してソート
        scored_docs = []
        for doc, score in zip(documents, scores):
            scored_docs.append({
                **doc,
                "rerank_score": float(score),
            })

        # スコアで降順ソートして top_k 件を返す
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_docs[:top_k]


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
    use_reranker: bool | None = None,
) -> list[dict]:
    """ベクトル検索と BM25 を RRF でマージするハイブリッド検索。
    Cross-Encoder によるリランキングをオプションで適用可能。

    Args:
        query: 検索クエリ
        n_results: 返す結果の件数
        category: カテゴリフィルタ（None の場合は全カテゴリ）
        use_reranker: リランキングを使用するか（None の場合は設定値を使用）

    Returns:
        {"content": str, "metadata": dict, "relevance_score": float, "id": str,
         "rerank_score": float (リランキング時のみ)} のリスト
    """
    settings = get_settings()
    alpha = settings.hybrid_search_alpha

    # リランキング設定の決定
    if use_reranker is None:
        use_reranker = settings.reranker_enabled

    # リランキング用により多くの候補を取得
    retrieval_k = settings.reranker_top_k * 2 if use_reranker else n_results

    vector_results = retrieve_documents(query=query, n_results=retrieval_k, category=category)

    if alpha >= 1.0:
        merged_results = vector_results
    else:
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

        sorted_ids = sorted(rrf_scores, key=lambda doc_id: rrf_scores[doc_id], reverse=True)[:retrieval_k]

        merged_results = [
            {**doc_map[doc_id], "relevance_score": rrf_scores[doc_id]}
            for doc_id in sorted_ids
        ]

    # Cross-Encoder でリランキング
    if use_reranker and merged_results:
        reranker = CrossEncoderReranker.get_instance()
        merged_results = reranker.rerank(query, merged_results, top_k=settings.reranker_top_k)
        logger.debug(f"Reranked {len(merged_results)} documents for query: {query[:50]}...")

    return merged_results[:n_results]


def retrieve_with_multi_query(
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> list[dict]:
    """Multi-Query で複数クエリを生成し、RRF で結果を統合する検索。

    Args:
        query: 元の検索クエリ
        n_results: 返す結果の件数
        category: カテゴリフィルタ（None の場合は全カテゴリ）

    Returns:
        {"content": str, "metadata": dict, "relevance_score": float, "id": str} のリスト
    """
    settings = get_settings()
    n_queries = settings.multi_query_count

    # 複数のクエリバリエーションを生成
    queries = rewrite_query_multi(query, n=n_queries)

    # 各クエリで検索実行
    all_results: list[list[dict]] = []
    for q in queries:
        results = retrieve_documents(query=q, n_results=n_results, category=category)
        all_results.append(results)

    # RRF で結果を統合
    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for results in all_results:
        for rank, doc in enumerate(results):
            doc_id = doc["id"]
            # 各クエリの結果に均等な重みを適用
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (_RRF_K + rank + 1))
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

    # スコアでソートして上位 n_results を返す
    sorted_ids = sorted(rrf_scores, key=lambda doc_id: rrf_scores[doc_id], reverse=True)[:n_results]

    return [
        {**doc_map[doc_id], "relevance_score": rrf_scores[doc_id]}
        for doc_id in sorted_ids
    ]


def retrieve_with_hyde(
    query: str,
    n_results: int = 5,
    category: str | None = None,
) -> list[dict]:
    """HyDE (Hypothetical Document Embeddings) で仮説回答を生成して検索。

    Args:
        query: 元の検索クエリ
        n_results: 返す結果の件数
        category: カテゴリフィルタ（None の場合は全カテゴリ）

    Returns:
        {"content": str, "metadata": dict, "relevance_score": float, "id": str} のリスト
    """
    # 仮説的回答を生成
    hypothetical_answer = rewrite_query_hyde(query)

    # 仮説回答で検索
    return retrieve_documents(query=hypothetical_answer, n_results=n_results, category=category)


def retrieve_with_strategy(
    query: str,
    n_results: int = 5,
    category: str | None = None,
    strategy: str | None = None,
) -> list[dict]:
    """設定に基づいて検索戦略を選択して検索を実行。

    Args:
        query: 検索クエリ
        n_results: 返す結果の件数
        category: カテゴリフィルタ（None の場合は全カテゴリ）
        strategy: 検索戦略（None の場合は設定値を使用）
            - "standard": 通常のベクトル検索
            - "multi_query": Multi-Query 拡張検索
            - "hyde": HyDE 仮説回答検索
            - "hybrid": Multi-Query + RRF 統合（将来的に BM25 と組み合わせ可能）

    Returns:
        {"content": str, "metadata": dict, "relevance_score": float, "id": str} のリスト
    """
    # 戦略が明示的に指定されていない場合は設定を使用
    if strategy is None:
        settings = get_settings()
        strategy = settings.retrieval_strategy

    # 戦略に基づいて検索を実行
    if strategy == "multi_query":
        return retrieve_with_multi_query(query=query, n_results=n_results, category=category)
    elif strategy == "hyde":
        return retrieve_with_hyde(query=query, n_results=n_results, category=category)
    elif strategy == "hybrid":
        # hybrid は現状 multi_query と同じ（将来的に BM25 と組み合わせる可能性）
        return retrieve_with_multi_query(query=query, n_results=n_results, category=category)
    else:
        # standard または無効な値はフォールバック
        return retrieve_documents(query=query, n_results=n_results, category=category)
