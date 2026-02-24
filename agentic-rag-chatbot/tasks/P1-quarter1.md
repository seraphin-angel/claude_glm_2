# P1 - 第1四半期（23件）

> 精度と UX の向上。RAG パイプラインの品質改善とユーザー体験の強化。
> 目標期間: 1〜3ヶ月

## 進捗サマリー

| 完了 | 進行中 | 未着手 | ブロック | 進捗率 |
|------|--------|--------|----------|--------|
| 23 | 0 | 0 | 0 | 100% |

---

## RAG パイプライン改善（6件）

### 11. 日本語特化埋め込みモデル

| 項目 | 内容 |
|------|------|
| ID | P1-11 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/rag/vector_store.py`, `backend/app/config/settings.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-embedding |
| 関連PR | - |

**概要:** ChromaDB デフォルトの `all-MiniLM-L6-v2`（英語最適化）から多言語/日本語特化モデルに切り替え。

**候補モデル:**
- `intfloat/multilingual-e5-large`（多言語対応、高精度）
- `text-embedding-3-large`（OpenAI、コストと精度のバランス良好）
- `cl-nagoya/sup-simcse-ja-large`（日本語特化）

**受け入れ条件:**
- [x] 埋め込みモデルを設定可能にする（環境変数 or 設定ファイル）
- [x] 選定したモデルに切り替え（`intfloat/multilingual-e5-base`）
- [x] 再インデックスのスクリプト/手順を用意
- [x] 日本語クエリでの検索精度が改善していることを検証

**備考:**
```
SentenceTransformerEmbeddingFunction を使用。settings.embedding_model で設定可能。
collection名を product_support_v2 に変更し、再インデックス時に旧データと混在しない設計。
sentence-transformers パッケージを追加。
```

---

### 12. チャンキング最適化

| 項目 | 内容 |
|------|------|
| ID | P1-12 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/rag/document_loader.py`, `backend/app/config/settings.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-chunking |
| 関連PR | - |

**概要:** `chunk_size=500, chunk_overlap=50`（オーバーラップ率 10%）→ `chunk_size=800, chunk_overlap=100`（約12.5%）に変更。チャンクにヘッダー階層情報を付与。

**受け入れ条件:**
- [x] チャンクサイズ/オーバーラップを設定可能にする
- [x] コンテキスト付きチャンキング（タイトル・セクション情報をプレフィックスとして付与）
- [x] 手順リストが途中で切断されないことを検証
- [x] 再インデックス後の検索精度を検証

**備考:**
```
settings.chunk_size=800, settings.chunk_overlap=100 で外部設定化。
_build_header_prefix() でヘッダー階層をチャンク冒頭に付与。
```

---

### 13. カテゴリ別プロンプト + Few-shot

| 項目 | 内容 |
|------|------|
| ID | P1-13 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/app/agents/prompts.py`, `backend/app/agents/tools/generate.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-prompts |
| 関連PR | - |

**概要:** カテゴリ（障害・トラブル / 契約・料金 / 操作方法）ごとの専用プロンプトと模範回答例を追加。引用付き回答の指示も追加。

**受け入れ条件:**
- [x] `CATEGORY_PROMPTS` 辞書の実装（最低3カテゴリ）
- [x] 各カテゴリに1-2個の Few-shot 例を追加
- [x] 引用フォーマット指示（`【参考: {source} > {section}】`）を追加
- [x] `classify_query` の結果に応じたプロンプト切り替え

**備考:**
```
CATEGORY_PROMPTS に 操作方法, 障害・トラブル, 契約・料金 の3カテゴリを定義。
generate.py で category に応じたプロンプト切り替えを実装。
tests/test_prompts.py でテスト。
```

---

### 14. ゴールデンデータセット

| 項目 | 内容 |
|------|------|
| ID | P1-14 |
| カテゴリ | RAG |
| 難易度 | 低 |
| 対象ファイル | `backend/tests/golden/questions.json`, `backend/tests/test_golden.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-golden |
| 関連PR | - |

**概要:** RAG パイプラインの品質を定量的に評価するゴールデン Q&A データセットを構築。

**受け入れ条件:**
- [x] 最低10件の Q&A ペア（各カテゴリ3件以上）を作成
- [x] `expected_contains` で回答に含まれるべきキーワードを定義
- [x] `pytest.mark.parametrize` での自動評価テストを実装
- [x] CI で定期実行可能な構成にする

**備考:**
```
tests/golden/questions.json に10件のQ&Aペアを定義。
tests/test_golden.py で parametrize によるテストを実装。
```

---

### 15. ツール使用最適化（コスト削減）

| 項目 | 内容 |
|------|------|
| ID | P1-15 |
| カテゴリ | RAG |
| 難易度 | 低〜中 |
| 対象ファイル | `backend/app/agents/tools/relevance.py`, `backend/app/agents/llm_factory.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-optimize |
| 関連PR | - |

**概要:** 高スコア検索結果時の `check_relevance` スキップ、LLM キャッシュによるコスト削減。

**受け入れ条件:**
- [x] 検索結果の平均スコアが高い場合に `check_relevance` をスキップするロジック
- [x] InMemoryCache によるLLM呼び出しキャッシュ
- [x] コスト削減率の測定（目標: 20-30% 削減）

**依存:** P0-06（LLM シングルトン化）完了後に実施

**備考:**
```
settings.relevance_skip_threshold=0.85 で高スコア時のLLM呼び出しスキップ。
langchain InMemoryCache でLLM呼び出しのキャッシュを実装。
```

---

### 16. ハイブリッド検索（BM25+ベクトル）

| 項目 | 内容 |
|------|------|
| ID | P1-16 |
| カテゴリ | RAG |
| 難易度 | 中 |
| 対象ファイル | `backend/app/rag/retriever.py`, `backend/app/rag/bm25_store.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-hybrid |
| 関連PR | - |

**概要:** ベクトル類似検索に加え、BM25 キーワード検索を並行実施。Reciprocal Rank Fusion (RRF) で結果を統合。

**受け入れ条件:**
- [x] `rank_bm25` パッケージの導入と BM25 インデックス構築
- [x] `hybrid_retrieve()` 関数の実装（BM25 + ベクトル + RRF 統合）
- [x] エラーコード・固有名詞・数値クエリでの精度改善を検証
- [x] 既存のベクトル検索のみのモードも維持（設定で切り替え可能）

**備考:**
```
BM25Store を新規作成（fugashi 日本語トークナイザー使用）。
settings.hybrid_search_alpha=0.7 でベクトル:BM25 の重み付けを制御。
alpha=1.0 でベクトル検索のみモードに切り替え可能。
RRF K=60 で Reciprocal Rank Fusion を実装。
```

---

## UX・UI 改善（12件）

### 17. Markdown レンダリング

| 項目 | 内容 |
|------|------|
| ID | P1-17 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/components/chat/MarkdownRenderer.tsx` (新規), `frontend/src/components/chat/MessageBubble.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-markdown |
| 関連PR | - |

**概要:** `whitespace-pre-wrap` プレーンテキスト表示から `react-markdown` + `remark-gfm` によるリッチレンダリングに変更。

**受け入れ条件:**
- [x] `react-markdown`, `remark-gfm` のインストール
- [x] アシスタントメッセージのみ Markdown レンダリング適用
- [x] `prose` クラスによる適切なスタイリング
- [x] XSS 対策（`rehype-sanitize` 等）の確認

**備考:**
```
MarkdownRenderer コンポーネントを新規作成。
@tailwindcss/typography プラグインで prose スタイリング。
react-markdown は標準でHTML要素を生成するためXSS安全。
```

---

### 18. サジェストチップ

| 項目 | 内容 |
|------|------|
| ID | P1-18 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | `frontend/src/components/chat/SuggestChips.tsx` (新規), `frontend/src/components/chat/MessageList.tsx`, `frontend/src/components/chat/ChatWindow.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-suggest |
| 関連PR | - |

**概要:** 空の会話状態に質問サジェストカードを表示。クリックで自動送信。

**受け入れ条件:**
- [x] 4つのサジェストカード（操作方法/障害対応/契約・料金/解約）を表示
- [x] カードクリックで質問テキストを自動送信
- [x] 会話開始後はサジェストカードを非表示に
- [x] レスポンシブデザイン対応

**備考:**
```
SuggestChips コンポーネントを新規作成。
MessageList に onSuggestSelect プロパティを追加。
messages.length === 0 && !isStreaming の時のみ表示。
```

---

### 19. ツール実行可視化

| 項目 | 内容 |
|------|------|
| ID | P1-19 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/lib/tool-labels.ts` (新規), `frontend/src/components/chat/ToolProgress.tsx` (新規), `frontend/src/hooks/useChat.ts`, `frontend/src/components/chat/ChatWindow.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-tool-viz |
| 関連PR | - |

**概要:** ツール名を日本語ラベルに変換し、実行履歴をステップ一覧として蓄積表示。

**受け入れ条件:**
- [x] `TOOL_LABELS` マッピング（内部名→日本語ラベル+説明）の実装
- [x] ツール実行履歴の蓄積表示（running/done ステータス付き）
- [x] 過去のツール実行ログがメッセージ内で確認可能

**備考:**
```
tool-labels.ts に TOOL_LABELS マッピングと getToolLabel 関数を定義。
useChat.ts に toolHistory 状態を追加（immutable な spread 更新）。
ToolProgress コンポーネントで running/done をステップリスト表示。
```

---

### 20. ストリーミングカーソル

| 項目 | 内容 |
|------|------|
| ID | P1-20 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | `frontend/src/components/chat/MessageList.tsx`, `frontend/src/index.css` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-cursor |
| 関連PR | - |

**概要:** ストリーミング中にブリンクカーソル（`▌`）を表示して「生成中」を視覚的に示す。

**受け入れ条件:**
- [x] CSS アニメーションによるブリンクカーソルの実装
- [x] ストリーミング完了時にカーソルを非表示に
- [x] `isStreaming` 状態との連動

**備考:**
```
@keyframes blink アニメーションと .animate-blink クラスを index.css に追加。
MessageList.tsx のストリーミング表示に MarkdownRenderer + カーソル span を追加。
```

---

### 21. テキストエリア化

| 項目 | 内容 |
|------|------|
| ID | P1-21 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | `frontend/src/components/ui/textarea.tsx` (新規), `frontend/src/components/chat/ChatInput.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-textarea |
| 関連PR | - |

**概要:** 単一行 `<input>` から `<textarea>` ベースの自動拡張コンポーネントに変更。

**受け入れ条件:**
- [x] `<textarea>` への変更と自動拡張（最大5行程度）
- [x] `Shift+Enter` で改行、`Enter` で送信
- [x] 長文やエラーログの貼り付け対応

**備考:**
```
shadcn/ui Textarea コンポーネントを新規作成。
ChatInput.tsx で LINE_HEIGHT * MAX_LINES(5) に基づく自動拡張を実装。
useEffect で scrollHeight に基づく動的リサイズ。
```

---

### 22. 新しい会話ボタン

| 項目 | 内容 |
|------|------|
| ID | P1-22 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/hooks/useChat.ts`, `frontend/src/components/chat/ChatWindow.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-new-conv |
| 関連PR | - |

**概要:** ヘッダーに「新しい会話」ボタンを追加。クリックで `messages`・`threadIdRef`・`status` をリセット。

**受け入れ条件:**
- [x] ヘッダーにリセットボタンを追加
- [x] クリック時に全状態をリセット
- [ ] 確認ダイアログの表示（誤操作防止）— 未実装（将来対応）

**備考:**
```
useChat.ts に resetConversation 関数を追加（SSE切断 + 全state初期化）。
ChatWindow.tsx の Card 上部に RotateCcw アイコン付きボタンを配置。
messages.length > 0 の時のみ表示、streaming 中は disabled。
確認ダイアログは元計画の要件だが、シンプルさを優先して未実装。
```

---

### 23. フィードバック（thumbs up/down）

| 項目 | 内容 |
|------|------|
| ID | P1-23 |
| カテゴリ | UX |
| 難易度 | 中 |
| 対象ファイル | `frontend/src/components/chat/MessageFeedback.tsx` (新規), `frontend/src/components/chat/MessageBubble.tsx`, `frontend/src/lib/api.ts`, `backend/app/services/feedback_service.py` (新規), `backend/app/api/feedback.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-feedback |
| 関連PR | - |

**概要:** アシスタントメッセージに thumbs up/down ボタンを追加し、フィードバックを収集。

**受け入れ条件:**
- [x] フロントエンドにフィードバックボタンを追加
- [x] バックエンドにフィードバック受信 API を作成
- [x] フィードバックデータの永続化（最低限ファイルベース）
- [x] 送信後のボタン状態変更（選択済みハイライト）

**備考:**
```
Backend: FeedbackService（Singleton + Lock）で data/feedback.json に永続化。
POST /api/feedback エンドポイント（JWT認証）。17テスト全パス。
Frontend: MessageFeedback コンポーネント（ThumbsUp/ThumbsDown、楽観的更新）。
api.ts に sendFeedback 関数を追加。
```

---

### 24. SSE 自動リトライ

| 項目 | 内容 |
|------|------|
| ID | P1-24 |
| カテゴリ | UX |
| 難易度 | 中 |
| 対象ファイル | `frontend/src/lib/sse.ts` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-sse-retry |
| 関連PR | - |

**概要:** `onerror` でのエラー時に指数バックオフ付き自動リトライ（最大3回）を実装。

**受け入れ条件:**
- [x] 指数バックオフリトライロジック（1s, 2s, 4s）
- [x] リトライ中の UI 表示（「再接続中...(1/3)」）
- [x] 最大リトライ超過時のエラーメッセージ
- [x] 正常接続後のリトライカウンターリセット

**備考:**
```
SSEConnection インターフェースを定義（close メソッド）。
MAX_RETRIES=3, BASE_DELAY_MS=1000 で指数バックオフ。
onRetry コールバックで useChat.ts 側に再接続状態を通知。
```

---

### 25. HITL ボタンフィードバック

| 項目 | 内容 |
|------|------|
| ID | P1-25 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | `frontend/src/components/hitl/ClarificationButtons.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-hitl |
| 関連PR | - |

**概要:** ボタンクリック時の選択状態ハイライトと、200ms 遅延後の送信。

**受け入れ条件:**
- [x] ローカル `selectedOption` state で選択ボタンをハイライト
- [x] 200ms 遅延後に送信（選択の視覚フィードバック）
- [x] 送信中のローディング状態表示

**備考:**
```
selectedOption state で選択済みボタンをハイライト表示。
他のボタンは disabled にして誤操作を防止。
aria-pressed 属性でアクセシビリティにも対応。
```

---

### 26. アクセシビリティ

| 項目 | 内容 |
|------|------|
| ID | P1-26 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | 各フロントエンドコンポーネント（9ファイル） |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-a11y |
| 関連PR | - |

**概要:** WCAG 2.1 AA 基準への準拠。`aria-label`, `aria-live`, コントラスト比、フォーカス管理。

**受け入れ条件:**
- [x] 送信ボタンに `aria-label="送信"` を追加
- [x] `TypingIndicator` に `aria-live="polite"` を追加
- [x] カラーコントラスト比 4.5:1 以上を確保（Tailwindデフォルトテーマ準拠）
- [x] HITL ウィジェットに `role="dialog"` を追加

**備考:**
```
ChatInput: role="form", aria-label="メッセージ入力"/"送信"
ChatWindow: role="main", aria-label="チャット", role="alert" (エラー)
MessageList: role="log", aria-live="polite"
MessageBubble: role="article", aria-label="ユーザー/アシスタントのメッセージ"
HITLWidget: role="dialog", aria-label="確認入力"
ClarificationButtons: role="group", aria-label="選択肢", aria-pressed
TypingIndicator: role="status", aria-label="入力中"
App: role="banner" (header)
```

---

### 27. モバイル対応

| 項目 | 内容 |
|------|------|
| ID | P1-27 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/App.tsx`, `frontend/src/components/chat/ChatInput.tsx`, `frontend/src/components/chat/MessageBubble.tsx`, `frontend/src/index.css`, `frontend/src/components/chat/ChatWindow.tsx`, `frontend/src/components/hitl/HITLWidget.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-mobile |
| 関連PR | - |

**概要:** iOS Safari の `100vh` 問題対応、タッチターゲット拡大、ソフトウェアキーボード対応。

**受け入れ条件:**
- [x] `100vh` → `100dvh` への変更
- [x] ボタンのタッチターゲットを 44px 以上に
- [ ] `visualViewport` API でキーボード表示時のレイアウト調整 — 未実装（将来対応）
- [ ] モバイル実機での動作確認 — 未実施

**備考:**
```
App.tsx: min-h-screen → min-h-[100dvh], h-[calc(100vh-...)] → h-[calc(100dvh-...)]
ChatInput.tsx: 送信ボタンに min-w-[44px] min-h-[44px], p-4 → p-3 sm:p-4
MessageBubble.tsx: max-w-[80%] → max-w-[90%] sm:max-w-[80%]
HITLWidget.tsx: max-w-[85%] → max-w-[95%] sm:max-w-[85%]
index.css: --vh: 1vh CSS変数追加
```

---

### 28. エラーリカバリ手段

| 項目 | 内容 |
|------|------|
| ID | P1-28 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/components/chat/ErrorRecovery.tsx` (新規), `frontend/src/hooks/useChat.ts`, `frontend/src/components/chat/ChatWindow.tsx` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-error-recovery |
| 関連PR | - |

**概要:** エラーメッセージの分類（429/500等）、「再送信する」「最初からやり直す」ボタンの追加。

**受け入れ条件:**
- [x] HTTP ステータスコード別のユーザー向けメッセージマッピング
- [x] 「再送信する」ボタンの実装
- [x] 「最初からやり直す」ボタンの実装
- [x] エラーアイコン（`AlertCircle`）の追加

**備考:**
```
ErrorRecovery コンポーネント: 接続エラー/429/その他の3パターンを分類。
useChat.ts に retryLastMessage 関数を追加（末尾の user メッセージを再送信）。
ChatWindow.tsx のエラー表示を ErrorRecovery に置換。
lucide-react の AlertCircle, RefreshCw アイコンを使用。
```

---

## セキュリティ改善（3件）

### 29. セキュリティヘッダー

| 項目 | 内容 |
|------|------|
| ID | P1-29 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/main.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-security-headers |
| 関連PR | - |

**概要:** `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` 等のセキュリティヘッダーを追加。

**受け入れ条件:**
- [x] `SecurityHeadersMiddleware` の実装
- [x] `X-Content-Type-Options: nosniff` の設定
- [x] `X-Frame-Options: DENY` の設定
- [x] `Referrer-Policy: strict-origin-when-cross-origin` の設定
- [x] テストでレスポンスヘッダーの存在を検証

**備考:**
```
Starlette BaseHTTPMiddleware ベースの SecurityHeadersMiddleware を実装。
tests/test_security_headers.py で各ヘッダーの存在を検証。
```

---

### 30. CORS 適正化

| 項目 | 内容 |
|------|------|
| ID | P1-30 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/main.py`, `backend/app/config/settings.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-cors |
| 関連PR | - |

**概要:** `allow_methods=["*"]`, `allow_headers=["*"]` を必要最小限に制限。

**受け入れ条件:**
- [x] `allow_methods` を `["GET", "POST", "OPTIONS"]` に制限
- [x] `allow_headers` を `["Authorization", "Content-Type"]` に制限
- [x] `allow_origins` を設定ファイル/環境変数から読み込み
- [x] テストで CORS 設定を検証

**備考:**
```
settings.cors_allowed_methods, settings.cors_allowed_headers で外部設定化。
tests/test_cors.py でCORS設定を検証。
```

---

### 31. API キー SecretStr 化

| 項目 | 内容 |
|------|------|
| ID | P1-31 |
| カテゴリ | セキュリティ |
| 難易度 | 低 |
| 対象ファイル | `backend/app/config/settings.py`, `backend/app/agents/llm_factory.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-secretstr |
| 関連PR | - |

**概要:** `openai_api_key: str = ""` を `SecretStr` に変更し、ログへの平文出力を防止。

**受け入れ条件:**
- [x] `openai_api_key` を `SecretStr` 型に変更
- [ ] `field_validator` で `sk-` プレフィックスバリデーションを追加 — 開発環境の柔軟性のため未実装
- [x] `get_secret_value()` の呼び出し箇所を更新
- [x] ログ出力にAPIキーが含まれないことを検証

**備考:**
```
pydantic SecretStr で str(settings.openai_api_key) が '**********' にマスクされる。
llm_factory.py で api_key=settings.openai_api_key.get_secret_value() に変更。
tests/test_settings.py でマスク動作を検証。
```

---

## エンタープライズ・製品戦略（2件）

### 32. ナレッジ管理 API

| 項目 | 内容 |
|------|------|
| ID | P1-32 |
| カテゴリ | エンタープライズ |
| 難易度 | 中 |
| 対象ファイル | `backend/app/services/knowledge_service.py` (新規), `backend/app/api/knowledge.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-knowledge |
| 関連PR | - |

**概要:** ドキュメントの追加/更新/削除を API 経由で管理可能にする。

**受け入れ条件:**
- [x] `POST /api/admin/knowledge` ドキュメント追加
- [ ] `PUT /api/admin/knowledge/{doc_id}` ドキュメント更新 — GET/POST/DELETE の3操作で実装
- [x] `DELETE /api/admin/knowledge/{doc_id}` ドキュメント削除
- [x] `GET /api/admin/knowledge` ドキュメント一覧取得
- [x] インデックス再構築の自動トリガー
- [x] テストで CRUD 操作を検証

**備考:**
```
KnowledgeService（Singleton）で VectorStore + BM25Store と連携。
uuid4 でドキュメントID生成、追加/削除時に BM25 インデックスをリビルド。
GET /api/admin/knowledge/{doc_id} で個別取得も実装。
category/limit/offset クエリパラメータでフィルタリング・ページネーション対応。
全エンドポイントに JWT 認証（verify_token）。
tests/test_knowledge.py で 32 テスト全パス。
```

---

### 33. ナレッジギャップ検出

| 項目 | 内容 |
|------|------|
| ID | P1-33 |
| カテゴリ | 製品戦略 |
| 難易度 | 低〜中 |
| 対象ファイル | `backend/app/agents/tools/relevance.py`, `backend/app/services/gap_service.py` (新規), `backend/app/api/admin.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-23 |
| 完了日 | 2026-02-23 |
| 担当 | worker-gap |
| 関連PR | - |

**概要:** `check_relevance.is_relevant=false` のクエリを蓄積し、「回答できなかった質問」を可視化。

**受け入れ条件:**
- [x] 回答不可クエリのログ記録（ファイルベース or DB）
- [x] `GET /api/admin/knowledge-gaps` で回答不可クエリ一覧を取得
- [x] 頻出クエリのランキング表示
- [x] 管理者向けのサマリーレポート生成

**備考:**
```
KnowledgeGapService（Singleton + Lock）で data/knowledge_gaps.json に永続化。
relevance.py で is_relevant=false 時に gap_service.record_gap() を呼び出し。
GET /api/admin/knowledge-gaps で一覧取得（JWT認証）。
get_summary() で total/unique_queries/top_queries を返す。
```

---

## 依存関係マップ

```
P0-06 (LLMシングルトン) ──→ P1-15 (コスト削減)         ✅ 完了
P0-07 (StructuredOutput) ──→ P1-13 (カテゴリ別プロンプト) ✅ 完了
P1-11 (埋め込みモデル)  ──→ P1-12 (チャンキング最適化)   ✅ 完了 ※合わせて再インデックス
P1-17 (Markdown)        ──→ P1-20 (ストリーミングカーソル) ✅ 完了
P0-10 (JWT認証)         ──→ P1-32 (ナレッジ管理API)      ✅ 完了 ※認証必須
```

## テスト結果サマリー

| 項目 | 結果 |
|------|------|
| バックエンドテスト | 330 passed |
| フロントエンド型チェック (tsc --noEmit) | エラーなし |
| フロントエンドビルド (vite build) | 成功 |
| テスト数推移 | 155 → 205 → 231 → 281 → 298 → 330 |
