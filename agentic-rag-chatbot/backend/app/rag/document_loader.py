import hashlib
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config.settings import get_settings
from app.rag.vector_store import VectorStore


def _generate_doc_id(content: str, source: str) -> str:
    """ドキュメントIDをハッシュで生成"""
    hash_input = f"{source}:{content[:100]}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def _build_header_prefix(metadata: dict) -> str:
    """metadataのヘッダー階層からプレフィックス文字列を生成する"""
    parts = []
    for key in ("title", "section", "subsection"):
        value = metadata.get(key)
        if value:
            parts.append(value)
    if not parts:
        return ""
    return "「" + " > ".join(parts) + "」\n"


def load_markdown_file(file_path: Path) -> list[dict]:
    """Markdownファイルを読み込みチャンクに分割"""
    settings = get_settings()
    content = file_path.read_text(encoding="utf-8")

    # Markdownヘッダーで分割
    headers_to_split_on = [
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_docs = md_splitter.split_text(content)

    # さらに文字数で分割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "、", " "],
    )

    chunks = []
    for doc in md_docs:
        split_texts = text_splitter.split_text(doc.page_content)
        for text in split_texts:
            metadata = dict(doc.metadata)
            metadata["source"] = file_path.name
            # ファイル名からカテゴリを推定
            metadata["category"] = _infer_category(file_path.stem)
            prefix = _build_header_prefix(metadata)
            chunks.append({
                "content": prefix + text,
                "metadata": metadata,
                "id": _generate_doc_id(text, str(file_path)),
            })

    return chunks


def _infer_category(stem: str) -> str:
    """ファイル名からカテゴリを推定"""
    category_map = {
        "product_guide": "操作方法",
        "troubleshooting": "障害・トラブル",
        "contracts": "契約・料金",
    }
    return category_map.get(stem, "その他")


def load_all_documents(docs_dir: str = "data/sample_docs") -> int:
    """指定ディレクトリ内の全Markdownファイルを読み込みベクトルストアに格納"""
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")

    store = VectorStore.get_instance()
    total_loaded = 0

    for md_file in sorted(docs_path.glob("*.md")):
        chunks = load_markdown_file(md_file)
        if chunks:
            store.add_documents(
                documents=[c["content"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
                ids=[c["id"] for c in chunks],
            )
            total_loaded += len(chunks)

    return total_loaded
