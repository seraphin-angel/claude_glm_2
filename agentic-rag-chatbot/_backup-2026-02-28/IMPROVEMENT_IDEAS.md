# Agentic RAG チャットボット — 改善アイディア総合レポート

> 分析日: 2026-02-23
> 対象バージョン: 0.1.0
> 分析手法: 5つの専門家ペルソナによる多角的エージェントチーム分析

---

## 目次

1. [エグゼクティブサマリー](#1-エグゼクティブサマリー)
2. [分析ペルソナと手法](#2-分析ペルソナと手法)
3. [Critical — 即時対応すべき課題](#3-critical--即時対応すべき課題)
4. [RAG パイプライン・回答精度の改善](#4-rag-パイプライン回答精度の改善)
5. [UX・UI の改善](#5-uxui-の改善)
6. [セキュリティ・プライバシーの強化](#6-セキュリティプライバシーの強化)
7. [エンタープライズ対応](#7-エンタープライズ対応)
8. [製品戦略・差別化](#8-製品戦略差別化)
9. [実装ロードマップ](#9-実装ロードマップ)
10. [優先度別サマリーテーブル](#10-優先度別サマリーテーブル)

---

## 1. エグゼクティブサマリー

本レポートは、Agentic RAG チャットボットの使い勝手と精度を向上させるため、5つの異なる専門家ペルソナ（UXデザイナー、AIエンジニア、エンタープライズ顧客、セキュリティ専門家、プロダクトマネージャー）が並列にコードベースを分析し、改善アイディアを洗い出した結果を統合したものである。

### 現状の強み

| 要素 | 評価 |
|------|------|
| LangGraph ReAct エージェント（7ツールの自律ループ） | 競合にない差別化ポイント |
| HITL（Human-in-the-Loop）中断・再開 | 曖昧さの対話的解消は希少 |
| 品質チェック（ハルシネーション評価+充足性評価） | 業界でも先進的 |
| SSE リアルタイムストリーミング | ChatGPT ライクな体験を低コストで実現 |
| クエリリライト（代名詞解決・曖昧表現の具体化） | RAG 精度向上に直結 |

### 発見された課題の件数

| カテゴリ | Critical | High | Medium | Low | 合計 |
|---------|----------|------|--------|-----|------|
| セキュリティ | 3 | 6 | 8 | 4 | 21 |
| RAG・回答精度 | 1 | 6 | 8 | 4 | 19 |
| UX・UI | 0 | 8 | 9 | 3 | 20 |
| エンタープライズ | 2 | 5 | 7 | 4 | 18 |
| 製品戦略 | 1 | 5 | 7 | 5 | 18 |

---

## 2. 分析ペルソナと手法

| ペルソナ | 専門領域 | 分析の重点 |
|---------|---------|-----------|
| UX デザイナー | UI/UX、アクセシビリティ、モバイル対応 | フロントエンドのコンポーネント・フック・SSE通信を精査 |
| AI エンジニア | RAG、LLM、検索精度、プロンプトエンジニアリング | エージェントツール・RAGパイプライン・品質チェックを精査 |
| エンタープライズ顧客 | スケーラビリティ、運用、コンプライアンス | アーキテクチャ全体・設定管理・永続化を精査 |
| セキュリティ専門家 | 脆弱性、認証、データ保護 | API エンドポイント・入力検証・シークレット管理を精査 |
| プロダクトマネージャー | 製品戦略、差別化、ロードマップ | 競合比較・機能拡張・ビジネスインパクトを分析 |

---

## 3. Critical — 即時対応すべき課題

以下は複数のペルソナが共通して指摘した、最も緊急性の高い課題である。

### 3-1. 品質チェックのフォールバックバグ（`quality.py`）

**発見者:** AIエンジニア、セキュリティ専門家

`check_quality` ツールの JSON パースエラー時に `passed=True`（合格）をデフォルト返却しており、品質チェックが実質的にバイパスされる。

```python
# 現状（危険）
except (json.JSONDecodeError, IndexError):
    return {
        "passed": True,           # 品質チェックが無条件合格
        "hallucination_score": 0.7,
        ...
    }

# 改善案（安全方向のフォールバック）
except (json.JSONDecodeError, IndexError):
    return {
        "passed": False,          # エラー時は不合格にする
        "hallucination_score": 0.0,
        ...
    }
```

| 項目 | 内容 |
|------|------|
| 影響 | ハルシネーションを含む回答がユーザーに届くリスク |
| 難易度 | 低（1行の変更） |
| 優先度 | **P0** |

---

### 3-2. 認証機構の完全不在

**発見者:** セキュリティ専門家、エンタープライズ顧客

全 API エンドポイントに認証が一切なく、誰でもチャットを利用でき、OpenAI API コストを無制限に消費させることが可能。

```python
# 現状: 認証なし
@router.post("", response_model=dict)
async def start_chat(request: ChatRequest):
    service = get_chat_service()
    ...

# 改善案: JWT認証ミドルウェアの追加
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.post("", response_model=dict)
async def start_chat(request: ChatRequest, user=Depends(verify_token)):
    ...
```

| 項目 | 内容 |
|------|------|
| 影響 | コストインジェクション攻撃、ナレッジベースへの不正アクセス、会話傍受 |
| 難易度 | 中 |
| 優先度 | **P0** |

---

### 3-3. レート制限の完全不在

**発見者:** セキュリティ専門家、エンタープライズ顧客

API エンドポイントにレート制限がなく、大量リクエストによる DoS 攻撃や OpenAI API コスト爆発のリスクがある。

```python
# 改善案: slowapi によるレート制限
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=dict)
@limiter.limit("10/minute")
async def start_chat(request: Request, body: ChatRequest):
    ...
```

| 項目 | 内容 |
|------|------|
| 影響 | サービス停止、コスト爆発 |
| 難易度 | 低 |
| 優先度 | **P0** |

---

### 3-4. エラーメッセージへの内部情報漏洩

**発見者:** セキュリティ専門家、UXデザイナー

`chat_service.py` が例外のスタックトレースをそのまま SSE でユーザーに送信しており、内部構造が露出する。

```python
# 現状（情報漏洩リスク）
content=f"エラーが発生しました: {error_str}"

# 改善案
logger.error(f"Agent error for thread {thread_id}: {error_str}", exc_info=True)
content="処理中にエラーが発生しました。しばらく待ってから再度お試しください。"
```

| 項目 | 内容 |
|------|------|
| 影響 | API キー情報、ファイルパス、内部構造の漏洩 |
| 難易度 | 低 |
| 優先度 | **P0** |

---

### 3-5. SSE キューのメモリリーク

**発見者:** セキュリティ専門家、エンタープライズ顧客

`ChatService._queues` と `_tasks` にサイズ制限がなく、`cleanup()` が API から呼ばれない。SSE 切断後もキューが残留し続ける。

```python
# 改善案
def __init__(self):
    self._queues: dict[str, asyncio.Queue] = {}
    self._max_concurrent = 1000

def get_or_create_queue(self, thread_id: str) -> asyncio.Queue:
    if len(self._queues) >= self._max_concurrent:
        self._evict_oldest()
    if thread_id not in self._queues:
        self._queues[thread_id] = asyncio.Queue(maxsize=100)
    return self._queues[thread_id]

# SSE 終了時に cleanup を呼ぶ
async def event_generator():
    try:
        ...
    finally:
        service.cleanup(thread_id)
```

| 項目 | 内容 |
|------|------|
| 影響 | メモリ枯渇によるサービス停止 |
| 難易度 | 低 |
| 優先度 | **P0** |

---

## 4. RAG パイプライン・回答精度の改善

### 4-1. 日本語特化の埋め込みモデルへの切り替え

**現状:** ChromaDB デフォルトの `all-MiniLM-L6-v2`（英語最適化、384次元）を使用。日本語の意味的類似性表現が不十分。

**改善案:**
- `intfloat/multilingual-e5-large`（多言語対応、高精度）
- `text-embedding-3-large`（OpenAI、3072次元、コストと精度のバランス良好）
- `cl-nagoya/sup-simcse-ja-large`（日本語特化）

**期待効果:** 日本語クエリとドキュメントのマッチング精度が 20-40% 向上。「ログできない」→「ログインできない場合」のような表記揺れでの改善が顕著。

| 難易度 | 優先度 |
|--------|--------|
| 低（モデル変更+再インデックス） | **P1** |

---

### 4-2. ハイブリッド検索（BM25 + ベクトル検索）の導入

**現状:** `retriever.py` はベクトル類似検索のみ。エラーコード（`E001`）、固有名詞（「製品B」）、数値（「月額8,000円」）はキーワード検索が優位。

**改善案:** BM25 インデックスを並行保持し、Reciprocal Rank Fusion (RRF) で結果を統合。

```python
from rank_bm25 import BM25Okapi

def hybrid_retrieve(query: str, n_results: int = 5) -> list[dict]:
    bm25_results = bm25_search(query, top_k=n_results * 2)
    vector_results = vector_search(query, n_results=n_results * 2)
    return reciprocal_rank_fusion([bm25_results, vector_results], k=60, top_n=n_results)
```

**期待効果:** キーワード一致が重要なクエリでの精度が 30% 向上。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P1** |

---

### 4-3. チャンキング戦略の最適化

**現状:** `chunk_size=500, chunk_overlap=50`（オーバーラップ率 10%）。手順リストが途中で切断される問題。チャンクにヘッダー階層情報が含まれない。

**改善案:**

```python
# チャンクサイズ拡大 + オーバーラップ率引き上げ
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,  # 約20%
    keep_separator=True,
)

# コンテキスト付きチャンキング
def _add_context_to_chunk(chunk_text: str, metadata: dict) -> str:
    context_prefix = ""
    if metadata.get("title"):
        context_prefix += f"[{metadata['title']}]"
    if metadata.get("section"):
        context_prefix += f"[{metadata['section']}]"
    return f"{context_prefix}\n{chunk_text}"
```

**期待効果:** 手順リストの完全性向上、文脈保持による検索精度改善。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 4-4. LLM インスタンスの共有・シングルトン化

**現状:** 各ツール（`classify.py`, `rewrite.py`, `relevance.py`, `generate.py`, `quality.py`）が毎回 `ChatOpenAI` インスタンスを生成。

**改善案:**

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_llm_zero_temp() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)

@lru_cache(maxsize=1)
def get_llm_creative() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.3)
```

**期待効果:** 接続プール効率化、メモリ使用量削減。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P0** |

---

### 4-5. StructuredOutput の導入

**現状:** 全ツールが LLM レスポンスを手動で JSON パース。パース失敗時のフォールバック処理が不安定。

**改善案:**

```python
from pydantic import BaseModel, Field
from typing import Literal

class ClassificationResult(BaseModel):
    category: Literal["操作方法", "障害・トラブル", "契約・料金", "その他", "out_of_scope", "unclear"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str

structured_llm = llm.with_structured_output(ClassificationResult)
result = structured_llm.invoke(classification_prompt)
```

**期待効果:** JSON パースエラーの完全排除、型安全性の向上。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P0** |

---

### 4-6. カテゴリ別プロンプト + Few-shot 例の追加

**現状:** `prompts.py` にはワークフロー指示のみで模範回答例なし。カテゴリに関わらず同一プロンプト。

**改善案:**

```python
CATEGORY_PROMPTS = {
    "障害・トラブル": """
トラブルシューティングのエキスパートとして:
1. 問題の症状を確認 → 2. 一般的な原因から順に確認ステップ提示
3. 各ステップの期待結果を明示 → 4. 解決しない場合のエスカレーション先を案内
    """,
    "契約・料金": """
金額・期間は参考情報から正確に引用。条件・例外事項を漏らさず記載。
変動可能性のある情報には「最新情報はサポートへ確認」と添える。
    """,
    "操作方法": """
各ステップは番号付きリスト。UI要素は【】で囲む。
    """,
}

# 引用付き回答の指示を追加
CITATION_PROMPT = "回答末尾に出典を明記: 【参考: {source} > {section}】"
```

**期待効果:** カテゴリに応じた回答品質向上、フォーマットの一貫性確保。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 4-7. Cross-Encoder によるリランキング

**現状:** `check_relevance` の `relevant_doc_indices` が `generate_answer` で活用されていない。フィルタリングなしで全ドキュメントが渡される。

**改善案:**

```python
from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_results(query: str, documents: list[dict]) -> list[dict]:
    pairs = [(query, doc["content"]) for doc in documents]
    scores = cross_encoder.predict(pairs)
    ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked]
```

**期待効果:** 無関係なドキュメントの排除によるハルシネーション率低下。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 4-8. Multi-Query / HyDE によるクエリ拡張

**現状:** `rewrite.py` は1つのリライトクエリのみ生成。検索カバレッジが限定的。

**改善案:**

```python
# Multi-Query: 複数のクエリバリエーションを生成
def rewrite_query_multi(query: str) -> list[str]:
    prompt = f"質問に対して検索に有効な異なる表現を3つ生成: {query}"
    # 3つのクエリで並列検索し結果を統合

# HyDE: 仮説的回答文書を生成して検索に使用
def rewrite_query_hyde(query: str) -> str:
    prompt = f"以下の質問に対する理想的な回答文書を書いてください: {query}"
    # 生成された文書をクエリとして埋め込み検索に使用
```

**期待効果:** 検索リコールが 20-35% 向上。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 4-9. ツール使用の最適化（不要な LLM コール削減）

**現状:** 単純なクエリでも最大 6 回の LLM 呼び出しが発生。1回の回答生成コストが高い。

**改善案:**

```python
# 高スコア検索結果が揃った場合は check_relevance をスキップ
def should_skip_relevance_check(results: list[dict]) -> bool:
    avg = sum(d["relevance_score"] for d in results) / len(results)
    return avg > 0.85

# 分類・評価用に低コストモデル、回答生成用に高精度モデルを段階的使用
get_llm_for_classification()  # gpt-4o-mini
get_llm_for_generation()      # gpt-4o
```

**期待効果:** API コスト 20-30% 削減、レスポンス時間短縮。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 4-10. エージェント反復回数の制限

**現状:** `create_react_agent` に反復回数制限がなく、品質チェック失敗のループで無限に LLM を呼び出す可能性。

**改善案:**

```python
# astream_events のラッパーでステップ数を監視
MAX_STEPS = 10
step_count = 0
async for event in agent.astream_events(...):
    step_count += 1
    if step_count > MAX_STEPS:
        raise RuntimeError("Max agent steps exceeded")
```

プロンプトにも明示的なリトライ制限を追記:
- `check_quality` 不合格時は最大2回まで再試行
- 3回目以降は `ask_human` でエスカレーション

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P0** |

---

### 4-11. RAG 評価フレームワーク + ゴールデンデータセット

**現状:** RAG パイプラインの品質を定量的に評価する仕組みがない。

**改善案:**

```python
# RAGAS による自動評価
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness, context_precision, context_recall

# ゴールデンデータセットの構築
GOLDEN_QA = [
    {"question": "パスワードを5回間違えたら？", "expected_contains": ["ロック", "30分", "自動解除"]},
    {"question": "スタンダードプランのAPI制限？", "expected_contains": ["300リクエスト/分"]},
]

# pytest での自動評価
@pytest.mark.parametrize("qa", GOLDEN_QA)
async def test_rag_quality(qa):
    result = await run_pipeline(qa["question"])
    for text in qa["expected_contains"]:
        assert text in result["answer"]
```

**期待効果:** 改善効果の定量測定、デグレッション自動検出。

| 難易度 | 優先度 |
|--------|--------|
| 低（データセット）〜中（RAGAS） | **P1** |

---

## 5. UX・UI の改善

### 5-1. Markdown レンダリングの実装

**現状:** `MessageBubble.tsx` は `whitespace-pre-wrap` でプレーンテキスト表示。エージェントが生成する番号付きリストやコードブロックが整形されない。

**改善案:**

```tsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

{isUser ? (
  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
) : (
  <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-sm">
    {message.content}
  </ReactMarkdown>
)}
```

**期待効果:** 回答の可読性が大幅に向上。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 5-2. サジェストチップ（Welcome 画面の改善）

**現状:** 空の会話状態は「製品サポートへようこそ」の2行のみ。ユーザーが何を質問すべきかのヒントが皆無。

**改善案:**

```tsx
const SUGGESTED_QUESTIONS = [
  { icon: "📘", label: "操作方法", question: "製品Aの初期設定方法を教えてください" },
  { icon: "🔧", label: "障害対応", question: "ログインできなくなりました" },
  { icon: "💳", label: "契約・料金", question: "プランをアップグレードするには？" },
  { icon: "❓", label: "解約", question: "解約手続きの方法は？" },
]
// カードクリックで自動送信
```

**期待効果:** 初回ユーザーの質問開始率向上、エージェントの得意領域の明示。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 5-3. ツール実行状態のわかりやすい可視化

**現状:** ツール名が内部名（`search_knowledge` 等）のまま表示。過去のツール実行ログが蓄積されない。

**改善案:**

```typescript
const TOOL_LABELS: Record<string, { label: string; description: string }> = {
  classify_query:    { label: "質問を分類中",     description: "カテゴリを判定しています" },
  rewrite_query:     { label: "クエリを最適化中", description: "検索に適した形に変換中" },
  search_knowledge:  { label: "ナレッジを検索中", description: "関連ドキュメントを探しています" },
  check_relevance:   { label: "関連性を確認中",   description: "検索結果の品質を評価中" },
  generate_answer:   { label: "回答を生成中",     description: "ドキュメントに基づき回答作成中" },
  check_quality:     { label: "品質チェック中",   description: "回答の正確性を検証中" },
  ask_human:         { label: "確認が必要です",   description: "追加情報が必要です" },
}

// ツール実行履歴をステップ一覧として蓄積表示
const [toolHistory, setToolHistory] = useState<Array<{ name: string; status: 'running' | 'done' }>>([])
```

**期待効果:** エージェントの動作理解によるユーザー不安解消、RAG システムの信頼性認知向上。

| 難易度 | 優先度 |
|--------|--------|
| 低（ラベル化）〜中（履歴蓄積） | **P1** |

---

### 5-4. ストリーミングカーソルの追加

**現状:** ストリーミング中に「まだ生成中」の視覚的な合図がない。

**改善案:**

```css
@keyframes blink { 50% { opacity: 0 } }
.streaming-cursor::after {
  content: '▌';
  animation: blink 1s step-end infinite;
}
```

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 5-5. テキストエリアへの入力変更（複数行対応）

**現状:** `ChatInput.tsx` は単一行 `<input>` のみ。長文やエラーログの貼り付けが不可能。

**改善案:** `<textarea>` ベースの自動拡張コンポーネントに変更。`Shift+Enter` で改行、`Enter` で送信。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 5-6. 「新しい会話」ボタンの追加

**現状:** 会話をリセットする手段がなく、ブラウザリロードが必要。

**改善案:** ヘッダーに「新しい会話」ボタンを追加。クリック時に `messages`・`threadIdRef`・`status` をリセット。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 5-7. 回答に対するフィードバック機能（👍/👎）

**現状:** ユーザーからの回答品質フィードバックを収集する手段がない。

**改善案:**

```tsx
{message.role === 'assistant' && (
  <div className="flex gap-1 mt-2">
    <button aria-label="役に立った" onClick={() => submitFeedback(message.id, 'positive')}>
      <ThumbsUp className="h-3 w-3" />
    </button>
    <button aria-label="役に立たなかった" onClick={() => submitFeedback(message.id, 'negative')}>
      <ThumbsDown className="h-3 w-3" />
    </button>
  </div>
)}
```

**期待効果:** ユーザー満足度データの収集、ナレッジベース・プロンプトの継続的改善。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P1** |

---

### 5-8. 回答のコピーボタン

**現状:** テキストをクリップボードにコピーする機能がない。手順やエラーメッセージのコピー需要が高い。

**改善案:** アシスタントメッセージにホバー時表示のコピーボタンを追加。`navigator.clipboard.writeText()` で実装。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P2** |

---

### 5-9. インテリジェント自動スクロール

**現状:** `useAutoScroll.ts` がメッセージ変化のたびに強制的に最下部へスクロール。古いメッセージ確認中でも最下部に戻される。

**改善案:** ユーザーが最下部付近（100px以内）にいる場合のみ自動スクロール。上方スクロール時は「最新メッセージへ ↓」フローティングボタンを表示。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 5-10. SSE 自動リトライ

**現状:** `sse.ts` の `onerror` はエラーを通知して接続を閉じるだけ。ネットワーク瞬断に対するリトライなし。

**改善案:** 指数バックオフ付き自動リトライ（最大3回）。リトライ中は「再接続中...(1/3)」を表示。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P1** |

---

### 5-11. HITL ボタン選択の視覚フィードバック

**現状:** `ClarificationButtons.tsx` のボタンクリック時に選択状態のハイライトがない。

**改善案:** ローカル `selectedOption` state で選択ボタンを `variant="default"` に切り替え、200ms 遅延後に送信。

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1** |

---

### 5-12. アクセシビリティ改善

**現状の問題点:**
- 送信ボタンに `aria-label` がない
- `TypingIndicator` に `aria-live` がない
- カラーコントラスト比が WCAG 2.1 AA 基準を下回る可能性
- HITL ウィジェット表示時にフォーカスが移動しない

**改善案:**

```tsx
// 送信ボタン
<Button aria-label="メッセージを送信" ...><Send aria-hidden="true" /></Button>

// TypingIndicator
<div role="status" aria-live="polite" aria-label="回答を生成しています">...</div>

// HITL フォーカス移動
useEffect(() => { firstInteractiveRef.current?.focus() }, [])

// コントラスト比改善
--muted-foreground: oklch(0.45 0 0);  // 4.5:1 以上を確保
```

| 難易度 | 優先度 |
|--------|--------|
| 低 | **P1**（WCAG準拠は必須） |

---

### 5-13. モバイル対応の改善

**現状の問題点:**
- `h-[calc(100vh-120px)]` が iOS Safari の `100vh` 問題に対応していない
- ボタンのタッチターゲットが 44px 未満
- ソフトウェアキーボード表示時のレイアウト崩れ

**改善案:**

```tsx
// dvh による動的ビューポート高さ
<div className="w-full max-w-3xl h-[calc(100dvh-120px)]">

// タッチターゲットの拡大
<Button className="min-h-[44px] md:min-h-[36px]">

// visualViewport API でキーボード検知
window.visualViewport?.addEventListener('resize', handler)
```

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 5-14. エラー時のリカバリ手段

**現状:** エラー表示はメッセージをそのまま表示するだけで、行動指示がない。

**改善案:**
- ユーザー向けエラーメッセージのマッピング（429→「リクエスト集中」、500→「サーバー問題」等）
- 「再送信する」「最初からやり直す」ボタンの追加
- エラーアイコン（`AlertCircle`）の追加

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 5-15. 長時間待機への対応

**現状:** フロントエンドにタイムアウト管理がなく、エージェントの応答が遅い場合も通知なしに待ち続ける。

**改善案:** 30秒後に「処理に時間がかかっています」バナー、60秒後に「キャンセルして再試行」ボタンを表示。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P2** |

---

## 6. セキュリティ・プライバシーの強化

### 6-1. プロンプトインジェクション対策

**現状:** 全ツールがユーザー入力を f-string でプロンプトに直接展開。サニタイゼーションなし。

**改善案:**

```python
# ユーザー入力を構造化メッセージとして渡す
from langchain_core.messages import HumanMessage, SystemMessage

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_query),
]

# インジェクション検出
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"system prompt",
]

def detect_injection(text: str) -> bool:
    return any(re.search(p, text.lower()) for p in INJECTION_PATTERNS)
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Critical | 中 | **P0** |

---

### 6-2. thread_id の UUID 強制バリデーション

**現状:** `thread_id` にフォーマットバリデーションがなく、任意文字列が通過する。

```python
from pydantic import UUID4
from fastapi import Path

@router.get("/stream/{thread_id}")
async def stream_chat(thread_id: UUID4 = Path(...)):
    if str(thread_id) not in service._queues:
        raise HTTPException(status_code=404, detail="Thread not found")
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| High | 低 | **P0** |

---

### 6-3. セキュリティヘッダーの追加

**現状:** `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy` 等が未設定。

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Medium | 低 | **P1** |

---

### 6-4. CORS 設定の適正化

**現状:** `allow_methods=["*"]`, `allow_headers=["*"]` で過剰に許可。

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Medium | 低 | **P1** |

---

### 6-5. API キーの SecretStr 化

**現状:** `openai_api_key: str = ""` でデフォルトが空文字。ログに平文出力されるリスク。

```python
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    openai_api_key: SecretStr

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr) -> SecretStr:
        key = v.get_secret_value()
        if not key or not key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key")
        return v
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Medium | 低 | **P1** |

---

### 6-6. SSE エンドポイントの認証

**現状:** SSE に認証がなく、thread_id を知っていれば他人の会話を傍受可能。

**改善案:** クエリパラメータで短命トークンを受け取り、スレッドの所有者検証を実施。

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| High | 中 | **P1** |

---

### 6-7. n_results パラメータの上限制限

**現状:** `search_knowledge` の `n_results` に上限がなく、`n_results=10000` 等の指定が可能。

```python
MAX_SEARCH_RESULTS = 20
n_results = max(1, min(n_results, MAX_SEARCH_RESULTS))
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Medium | 低 | **P1** |

---

### 6-8. FastAPI ドキュメントの本番環境無効化

**現状:** `/docs`（Swagger UI）と `/redoc` がデフォルトで公開。

```python
app = FastAPI(
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
)
```

| 重要度 | 難易度 | 優先度 |
|--------|--------|--------|
| Low | 低 | **P2** |

---

## 7. エンタープライズ対応

### 7-1. 永続化チェックポインタへの移行

**現状:** `MemorySaver` はプロセス再起動で全会話履歴が消失。水平スケーリング不可。

**改善案:** LangGraph の `PostgresSaver` または `RedisSaver` に移行。`asyncio.Queue` を Redis Streams に置換。

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| デプロイ時のサポート会話消失を防止 | 中〜高 | **P0** |

---

### 7-2. 詳細ヘルスチェック

**現状:** `GET /api/health` は `{"status": "ok"}` のみ。ChromaDB・OpenAI の疎通確認なし。

**改善案:**

```python
@router.get("/api/health/detailed")
async def health_detailed():
    return {
        "status": "ok",
        "chromadb": {"connected": True, "doc_count": store.count},
        "openai": {"reachable": True},
        "active_sessions": len(service._queues),
        "memory_usage_mb": get_memory_usage(),
    }
```

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| SLA 監視、障害早期発見 | 低〜中 | **P1** |

---

### 7-3. 構造化ロギング・監査ログ

**現状:** リクエスト/レスポンスのロギングなし。LLM呼び出しのトレースなし。

**改善案:**

```python
# OpenTelemetry or LangSmith によるトレーシング
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 構造化ログ: ユーザーID、スレッドID、LLM呼び出し回数、トークン数を記録
```

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| ISO 27001 / SOC 2 監査要件対応 | 中 | **P1** |

---

### 7-4. LLM コスト可視化・制御

**現状:** トークン消費量の記録が一切なし。月額コストが予測不能。

**改善案:** `get_openai_callback()` でトークン消費量を記録。ユーザー/テナントごとの月間上限設定。コスト予測ダッシュボード。

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| 予算管理、コスト爆発防止 | 中 | **P1** |

---

### 7-5. マルチテナント対応

**現状:** ChromaDB コレクションは1つのみ。テナント識別子が存在しない。

**改善案:** API リクエストからテナントIDを取得し、コレクションをテナントごとに分離。

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| SaaS 型での複数顧客提供 | 高 | **P2** |

---

### 7-6. ナレッジベース管理 UI

**現状:** ドキュメント追加は `data/sample_docs/` への手動ファイル配置のみ。ChromaDB 削除+再起動が必要。

**改善案:**

```python
@router.post("/api/knowledge")            # ドキュメント追加
@router.put("/api/knowledge/{doc_id}")     # ドキュメント更新
@router.delete("/api/knowledge/{doc_id}")  # ドキュメント削除
@router.get("/api/knowledge/gaps")         # ナレッジギャップ検出
```

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| サポートチームの自律運用 | 中 | **P1** |

---

### 7-7. データ保持ポリシー

**改善案:** テナントごとにデータ保持期間を設定（30日/90日/365日）。GDPR「忘れられる権利」対応。自動削除ジョブの実装。

| 影響 | 難易度 | 優先度 |
|------|--------|--------|
| 個人情報保護法・GDPR 対応 | 中 | **P2** |

---

## 8. 製品戦略・差別化

### 8-1. 回答の根拠（ソースドキュメント）可視化

**現状:** `check_quality` のスコアや `search_knowledge` の検索元がフロントエンドに表示されない。

**改善案:**

```tsx
{message.sourceDocuments && (
  <details className="mt-2 text-xs text-muted-foreground">
    <summary>参照した根拠を見る</summary>
    {message.sourceDocuments.map(doc => <SourceCard key={doc.id} doc={doc} />)}
  </details>
)}
```

**期待効果:** 「説明可能な AI」として Zendesk AI / Intercom が持たない差別化ポイントを確立。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 8-2. エスカレーションツール（第8のツール）

**現状:** `ask_human` は追加情報収集のみ。人間オペレーターへの引き継ぎ機能がない。

**改善案:**

```python
@tool
def escalate_to_human(
    issue_summary: str,
    category: str,
    conversation_history: list[dict],
    priority: str = "normal"
) -> dict:
    """解決できない問題を有人サポートにエスカレーション"""
    ticket = ticket_service.create(summary=issue_summary, history=conversation_history)
    return {"ticket_id": ticket.id, "estimated_response_time": ticket.eta}
```

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P1** |

---

### 8-3. プロアクティブ FAQ サジェスト

**現状:** 完全にリアクティブ。ユーザーが質問するまでエージェントは何もしない。

**改善案:** ユーザーの現在地（ページURL）に基づく関連 FAQ のプッシュ表示。当日のトップ質問のリアルタイムバッジ。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P2** |

---

### 8-4. 画像添付（スクリーンショット解析）

**現状:** テキスト入力のみ。エラー画面のスクリーンショット添付不可。

**改善案:**

```python
@tool
def analyze_image(image_base64: str, question: str) -> str:
    """スクリーンショットからエラーコード・問題内容を抽出"""
    llm = ChatOpenAI(model="gpt-4o", ...)  # Vision対応
    ...
```

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 8-5. 多言語対応

**現状:** 日本語専用。プロンプト・UI ともにハードコード。

**改善案:** 言語自動検出、言語別システムプロンプト、ナレッジベースの `language` メタデータ、フロントエンド i18n 対応。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 8-6. マルチチャネル対応

**改善案:** `ChatRequest` に `channel` フィールドを追加。LINE / Slack / メールの Webhook アダプターを構築。

| 難易度 | 優先度 |
|--------|--------|
| 中〜高 | **P2** |

---

### 8-7. パーソナライゼーション

**改善案:** `user_id` による会話履歴の個人別蓄積。ユーザーのプラン情報に基づくカスタマイズ回答。過去の質問パターンからの FAQ 先出し。

| 難易度 | 優先度 |
|--------|--------|
| 中 | **P2** |

---

### 8-8. ナレッジギャップ自動検出

**改善案:** `check_relevance.is_relevant=false` のクエリを蓄積し、「回答できなかった質問ベスト10」を管理者に通知。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P1** |

---

### 8-9. システムプロンプトの管理 UI

**現状:** `prompts.py` にハードコード。コード変更なしに調整不可。

**改善案:** データベースで管理し、管理 UI で編集可能に。A/B テスト機能。変更履歴とロールバック。

| 難易度 | 優先度 |
|--------|--------|
| 低〜中 | **P2** |

---

## 9. 実装ロードマップ

### フェーズ 1（即時〜1ヶ月）— 基盤の安全性確保

| # | 改善項目 | カテゴリ | 難易度 |
|---|---------|---------|--------|
| 1 | 品質チェックフォールバックを `passed=False` に修正 | RAG | 低 |
| 2 | レート制限の実装（slowapi） | セキュリティ | 低 |
| 3 | エラーメッセージの内部情報除去 | セキュリティ | 低 |
| 4 | SSE キューのメモリリーク修正（cleanup/maxsize） | セキュリティ | 低 |
| 5 | thread_id の UUID バリデーション | セキュリティ | 低 |
| 6 | LLM インスタンスのシングルトン化 | RAG | 低 |
| 7 | StructuredOutput 導入 | RAG | 低 |
| 8 | エージェント反復回数制限 | RAG | 低 |
| 9 | プロンプトインジェクション対策 | セキュリティ | 中 |
| 10 | JWT 認証の実装 | セキュリティ | 中 |

### フェーズ 2（1〜3ヶ月）— 精度と UX の向上

| # | 改善項目 | カテゴリ | 難易度 |
|---|---------|---------|--------|
| 11 | 日本語特化の埋め込みモデルへの切り替え | RAG | 低 |
| 12 | チャンキング戦略の最適化 | RAG | 低 |
| 13 | カテゴリ別プロンプト + Few-shot 例 | RAG | 低 |
| 14 | ゴールデンデータセット構築 | RAG | 低 |
| 15 | Markdown レンダリング実装 | UX | 低〜中 |
| 16 | サジェストチップ（Welcome 画面） | UX | 低 |
| 17 | ツール実行状態の可視化改善 | UX | 低 |
| 18 | アクセシビリティ改善（aria-label 等） | UX | 低 |
| 19 | 回答フィードバック（👍/👎） | UX | 中 |
| 20 | SSE 自動リトライ | UX | 中 |
| 21 | セキュリティヘッダー追加 | セキュリティ | 低 |
| 22 | ナレッジベース管理 API | エンタープライズ | 中 |
| 23 | 詳細ヘルスチェック | エンタープライズ | 低〜中 |

### フェーズ 3（3〜6ヶ月）— エンタープライズ品質

| # | 改善項目 | カテゴリ | 難易度 |
|---|---------|---------|--------|
| 24 | PostgresSaver への移行 | エンタープライズ | 中〜高 |
| 25 | ハイブリッド検索（BM25+ベクトル） | RAG | 中 |
| 26 | Cross-Encoder リランキング | RAG | 中 |
| 27 | RAGAS 評価フレームワーク | RAG | 中 |
| 28 | 構造化ロギング・監査ログ | エンタープライズ | 中 |
| 29 | LLM コスト可視化 | エンタープライズ | 中 |
| 30 | 回答の根拠可視化 | 製品戦略 | 低〜中 |
| 31 | エスカレーションツール | 製品戦略 | 中 |
| 32 | モバイル対応強化 | UX | 低〜中 |

### フェーズ 4（6〜12ヶ月）— プラットフォーム化

| # | 改善項目 | カテゴリ | 難易度 |
|---|---------|---------|--------|
| 33 | マルチテナント対応 | エンタープライズ | 高 |
| 34 | 画像添付（スクリーンショット解析） | 製品戦略 | 中 |
| 35 | 多言語対応 | 製品戦略 | 中 |
| 36 | マルチチャネル（LINE/Slack/メール） | 製品戦略 | 中〜高 |
| 37 | パーソナライゼーション | 製品戦略 | 中 |
| 38 | CRM/チケットシステム連携 | エンタープライズ | 高 |
| 39 | A/B テスト基盤 | 製品戦略 | 高 |
| 40 | データ保持ポリシー（GDPR対応） | エンタープライズ | 中 |

---

## 10. 優先度別サマリーテーブル

### P0 — 即時対応（10件）

| # | 改善項目 | 難易度 | カテゴリ |
|---|---------|--------|---------|
| 1 | `quality.py` フォールバック修正（`passed=False`） | 低 | RAG |
| 2 | レート制限の実装 | 低 | セキュリティ |
| 3 | エラーメッセージの内部情報除去 | 低 | セキュリティ |
| 4 | SSE キューのメモリリーク修正 | 低 | セキュリティ |
| 5 | thread_id UUID バリデーション | 低 | セキュリティ |
| 6 | LLM インスタンスのシングルトン化 | 低 | RAG |
| 7 | StructuredOutput 導入 | 低 | RAG |
| 8 | エージェント反復回数制限 | 低 | RAG |
| 9 | プロンプトインジェクション対策 | 中 | セキュリティ |
| 10 | JWT 認証の実装 | 中 | セキュリティ |

### P1 — 第1四半期（23件）

| # | 改善項目 | 難易度 | カテゴリ |
|---|---------|--------|---------|
| 11 | 日本語特化埋め込みモデル | 低 | RAG |
| 12 | チャンキング最適化 | 低 | RAG |
| 13 | カテゴリ別プロンプト + Few-shot | 低 | RAG |
| 14 | ゴールデンデータセット | 低 | RAG |
| 15 | ツール使用最適化（コスト削減） | 低〜中 | RAG |
| 16 | ハイブリッド検索（BM25+ベクトル） | 中 | RAG |
| 17 | Markdown レンダリング | 低〜中 | UX |
| 18 | サジェストチップ | 低 | UX |
| 19 | ツール実行可視化 | 低〜中 | UX |
| 20 | ストリーミングカーソル | 低 | UX |
| 21 | テキストエリア化 | 低 | UX |
| 22 | 新しい会話ボタン | 低〜中 | UX |
| 23 | フィードバック（👍/👎） | 中 | UX |
| 24 | SSE 自動リトライ | 中 | UX |
| 25 | HITL ボタンフィードバック | 低 | UX |
| 26 | アクセシビリティ | 低 | UX |
| 27 | モバイル対応 | 低〜中 | UX |
| 28 | エラーリカバリ手段 | 低〜中 | UX |
| 29 | セキュリティヘッダー | 低 | セキュリティ |
| 30 | CORS 適正化 | 低 | セキュリティ |
| 31 | API キー SecretStr 化 | 低 | セキュリティ |
| 32 | ナレッジ管理 API | 中 | エンタープライズ |
| 33 | ナレッジギャップ検出 | 低〜中 | 製品戦略 |

### P2 — 第2四半期（14件）

| # | 改善項目 | 難易度 | カテゴリ |
|---|---------|--------|---------|
| 34 | Cross-Encoder リランキング | 中 | RAG |
| 35 | Multi-Query / HyDE | 中 | RAG |
| 36 | RAGAS 評価フレームワーク | 中 | RAG |
| 37 | コピーボタン | 低 | UX |
| 38 | インテリジェント自動スクロール | 中 | UX |
| 39 | 長時間待機通知 | 低〜中 | UX |
| 40 | PostgresSaver 移行 | 中〜高 | エンタープライズ |
| 41 | 構造化ロギング | 中 | エンタープライズ |
| 42 | LLM コスト可視化 | 中 | エンタープライズ |
| 43 | 詳細ヘルスチェック | 低〜中 | エンタープライズ |
| 44 | 回答の根拠可視化 | 低〜中 | 製品戦略 |
| 45 | エスカレーションツール | 中 | 製品戦略 |
| 46 | プロアクティブ FAQ | 低〜中 | 製品戦略 |
| 47 | システムプロンプト管理 UI | 低〜中 | 製品戦略 |

### P3 — 第3四半期以降（9件）

| # | 改善項目 | 難易度 | カテゴリ |
|---|---------|--------|---------|
| 48 | マルチテナント対応 | 高 | エンタープライズ |
| 49 | データ保持ポリシー（GDPR） | 中 | エンタープライズ |
| 50 | CRM/チケットシステム連携 | 高 | エンタープライズ |
| 51 | 画像添付（Vision API） | 中 | 製品戦略 |
| 52 | 多言語対応 | 中 | 製品戦略 |
| 53 | マルチチャネル（LINE/Slack/メール） | 中〜高 | 製品戦略 |
| 54 | パーソナライゼーション | 中 | 製品戦略 |
| 55 | A/B テスト基盤 | 高 | 製品戦略 |
| 56 | ガードレール/ジェイルブレイク対策 | 高 | セキュリティ |

---

## 競合比較マトリクス（改善後の想定）

| 機能 | 本製品（改善後） | Zendesk AI | Intercom | Drift |
|------|---------------|-----------|---------|-------|
| Agentic RAG ループ | 自律8ツール | 固定フロー | 固定フロー | ルールベース |
| 品質保証・根拠可視化 | ハルシネーション評価+出典表示 | なし | なし | なし |
| HITL 中断・再開 | LangGraph interrupt | 有人ルーティング | 有人ルーティング | なし |
| ハイブリッド検索 | BM25+ベクトル+リランキング | 不明 | 不明 | なし |
| マルチチャネル | Web+Email+LINE+Slack | 全チャネル | 全チャネル | Web+Email |
| ナレッジ管理 | 管理UI+ギャップ検出 | 管理UI | 管理UI | 管理UI |
| 多言語 | 自動検出+動的プロンプト | 対応 | 対応 | 限定的 |
| パーソナライズ | ユーザー履歴連動 | 対応 | 対応 | 限定的 |
| 価格 | 自社ホスト可能（低コスト） | 高額 SaaS | 高額 SaaS | 高額 SaaS |

---

> 本レポートは、5つの専門家ペルソナ（UXデザイナー、AIエンジニア、エンタープライズ顧客、セキュリティ専門家、プロダクトマネージャー）による並列分析の結果を統合・重複排除したものです。合計 56 件の改善アイディアを優先度順に整理しました。
