import logging

import fugashi
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


def _tokenize(text: str, tagger: fugashi.Tagger) -> list[str]:
    """fugashi で日本語テキストを分かち書きする"""
    return [word.surface for word in tagger(text) if word.surface.strip()]


class BM25Store:
    """BM25 インデックスのシングルトン管理クラス"""

    _instance: "BM25Store | None" = None

    def __init__(self) -> None:
        self._tagger = fugashi.Tagger()
        self._bm25: BM25Okapi | None = None
        self._documents: list[dict] = []

    @classmethod
    def get_instance(cls) -> "BM25Store":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def build_index(self, documents: list[dict]) -> None:
        """ドキュメントリストから BM25 インデックスを構築する。

        Args:
            documents: {"content": str, "metadata": dict, "id": str} のリスト
        """
        if not documents:
            logger.warning("BM25Store: build_index called with empty documents list")
            self._bm25 = None
            self._documents = []
            return

        self._documents = documents
        tokenized = [_tokenize(doc["content"], self._tagger) for doc in documents]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25Store: built index with {len(documents)} documents")

    def build_index_from_vector_store(self, store: object) -> None:
        """VectorStore から全ドキュメントを取得して BM25 インデックスを構築する。

        Args:
            store: get_all_documents() メソッドを持つ VectorStore インスタンス
        """
        documents = store.get_all_documents()
        self.build_index(documents)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """BM25 でクエリに関連するドキュメントを検索する。

        Args:
            query: 検索クエリ文字列
            top_k: 取得する最大件数

        Returns:
            {"content": str, "metadata": dict, "id": str, "bm25_score": float} のリスト（スコア降順）
        """
        if self._bm25 is None or not self._documents:
            logger.warning("BM25Store: index not built, returning empty results")
            return []

        query_tokens = _tokenize(query, self._tagger)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        return [
            {
                "content": self._documents[i]["content"],
                "metadata": self._documents[i]["metadata"],
                "id": self._documents[i]["id"],
                "bm25_score": float(scores[i]),
            }
            for i in top_indices
            if scores[i] > 0.0
        ]
