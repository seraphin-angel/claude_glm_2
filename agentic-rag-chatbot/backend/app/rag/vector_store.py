import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.config.settings import get_settings


class VectorStore:
    """ChromaDB ベクトルストア ラッパー"""

    _instance: "VectorStore | None" = None

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def get_instance(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """ドキュメントをベクトルストアに追加"""
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        self._collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> dict:
        """類似検索を実行"""
        kwargs: dict = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)

    def get_all_documents(self) -> list[dict]:
        """コレクション内の全ドキュメントを取得してリストで返す"""
        result = self._collection.get(include=["documents", "metadatas"])
        docs = []
        if result and result.get("documents"):
            for i, content in enumerate(result["documents"]):
                metadata = result["metadatas"][i] if result.get("metadatas") else {}
                doc_id = result["ids"][i] if result.get("ids") else f"doc_{i}"
                docs.append({"content": content, "metadata": metadata, "id": doc_id})
        return docs

    @property
    def count(self) -> int:
        return self._collection.count()
