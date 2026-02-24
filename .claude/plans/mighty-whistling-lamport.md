# P1 全23件 実装計画

## Context

P0タスク10件は全て完了済み（JWT認証、LLMシングルトン、StructuredOutput、レート制限等）。
P1では RAG パイプラインの品質改善、UX強化、セキュリティ適正化、エンタープライズ機能を実装する。
依存関係を考慮して6フェーズに分割し、各フェーズ内で並列実行可能なタスクをグループ化する。

---

## フェーズ1: セキュリティ基盤整備（P1-29, P1-30, P1-31）

破壊的変更ゼロ、テスト影響最小。基盤として先行実施。3件同時並列可。

### P1-31: APIキー SecretStr化
- **変更**: `backend/app/config/settings.py` — `openai_api_key: str` → `SecretStr`
- **変更**: `backend/app/agents/llm_factory.py` — `.get_secret_value()` 呼び出し追加
- **テスト**: `str(settings.openai_api_key)` が `**********` でマスクされることを確認

### P1-29: セキュリティヘッダー
- **変更**: `backend/app/main.py` — `SecurityHeadersMiddleware` 追加
- **ヘッダー**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
- **テスト**: 全エンドポイントでヘッダー存在確認

### P1-30: CORS適正化
- **変更**: `backend/app/config/settings.py` — `cors_allowed_methods`, `cors_allowed_headers` 追加
- **変更**: `backend/app/main.py` — `allow_methods=["GET","POST","OPTIONS"]`, `allow_headers=["Authorization","Content-Type"]`
- **テスト**: 許可外メソッド（PUT, DELETE）拒否確認

---

## フェーズ2: RAGパイプライン基盤強化（P1-11, P1-12, P1-16）

P1-11+P1-12 を同時実施（再インデックスを1回で済ませる）。P1-16 は並列可。

### P1-11: 日本語特化埋め込みモデル
- **追加パッケージ**: `sentence-transformers>=3.0.0`
- **変更**: `backend/app/config/settings.py` — `embedding_model: str = "intfloat/multilingual-e5-base"` 追加
- **変更**: `backend/app/rag/vector_store.py` — `SentenceTransformerEmbeddingFunction` 使用
- **再インデックス**: コレクション名を `product_support_v2` に変更してダウンタイムなし移行

### P1-12: チャンキング最適化
- **変更**: `backend/app/config/settings.py` — `chunk_size: int = 800`, `chunk_overlap: int = 100`
- **変更**: `backend/app/rag/document_loader.py` — 設定値を外部化、ヘッダー階層プレフィックス付与
- **テスト**: チャンクサイズ検証、手順リスト切断テスト

### P1-16: ハイブリッド検索（BM25+ベクトル）
- **追加パッケージ**: `rank-bm25>=0.2.2`, `fugashi>=1.3.0`, `unidic-lite>=1.0.8`
- **新規**: `backend/app/rag/bm25_store.py` — BM25インデックス（シングルトン、fugashi分かち書き）
- **変更**: `backend/app/rag/retriever.py` — `hybrid_retrieve()` + Reciprocal Rank Fusion
- **設定**: `alpha` パラメータでベクトル/BM25比率制御（`alpha=1.0` でベクトルのみ維持可）
- **起動時**: `main.py` lifespan で BM25Store も同時初期化

---

## フェーズ3: RAGエージェント品質改善（P1-13, P1-14, P1-15, P1-33）

4件同時並列可。フェーズ2の検索改善後にプロンプト・評価を最適化。

### P1-13: カテゴリ別プロンプト + Few-shot
- **変更**: `backend/app/agents/prompts.py` — `CATEGORY_PROMPTS` 辞書（操作方法/障害・トラブル/契約・料金）
- **変更**: `backend/app/agents/tools/generate.py` — `classify_query` 結果でプロンプト切替
- **追加**: 引用フォーマット指示（`【参考: {source} > {section}】`）

### P1-14: ゴールデンデータセット
- **新規**: `backend/tests/golden/questions.json` — 最低10件のQ&Aペア（カテゴリ各3件以上）
- **新規**: `backend/tests/test_golden.py` — `pytest.mark.parametrize` 自動評価テスト
- **評価**: `expected_keywords` によるキーワード含有チェック

### P1-15: ツール使用最適化（コスト削減）
- **変更**: `backend/app/config/settings.py` — `llm_cache_enabled: bool = True`
- **変更**: `backend/app/agents/llm_factory.py` — `InMemoryCache` 設定
- **変更**: `backend/app/agents/tools/relevance.py` — 高スコア時 `check_relevance` スキップ
- **目標**: LLM呼び出し20-30%削減

### P1-33: ナレッジギャップ検出
- **新規**: `backend/app/services/gap_service.py` — ギャップ記録・集計サービス（インメモリ→ファイル永続化）
- **新規**: `backend/app/api/admin.py` — `GET /api/admin/knowledge-gaps`（JWT認証）
- **連携**: `check_relevance` で `is_relevant=false` 時に自動記録

---

## フェーズ4: UX基盤強化（P1-17, P1-20, P1-21, P1-24, P1-25）

P1-17→P1-20 の依存あり。その他は並列可。

### P1-17: Markdownレンダリング
- **追加パッケージ**: `react-markdown@^9`, `remark-gfm@^4`
- **新規**: `frontend/src/components/chat/MarkdownRenderer.tsx` — ReactMarkdown + remarkGfm
- **変更**: `frontend/src/components/chat/MessageBubble.tsx` — アシスタントメッセージのみ Markdown適用
- **スタイル**: `prose prose-sm dark:prose-invert` クラス（Tailwind v4: `@plugin '@tailwindcss/typography'`）
- **XSS対策**: react-markdown はデフォルトで HTML をサニタイズ

### P1-20: ストリーミングカーソル（P1-17完了後）
- **変更**: `frontend/src/components/chat/MessageList.tsx` — ストリーミング中に `▌` ブリンクカーソル
- **CSS**: `@keyframes blink` アニメーション追加
- **連動**: `isStreaming` 状態で表示/非表示切替

### P1-21: テキストエリア化
- **新規**: `frontend/src/components/ui/textarea.tsx` — shadcn/ui Textarea コンポーネント
- **変更**: `frontend/src/components/chat/ChatInput.tsx` — `<Input>` → `<Textarea>` + auto-resize
- **操作**: `Shift+Enter` で改行、`Enter` で送信（最大5行）

### P1-24: SSE自動リトライ
- **変更**: `frontend/src/lib/sse.ts` — 指数バックオフリトライ（1s, 2s, 4s、最大3回）
- **変更**: `frontend/src/hooks/useChat.ts` — `eventSourceRef` 型変更（`{ eventSource, close }`）
- **UI**: リトライ中状態の表示

### P1-25: HITLボタンフィードバック
- **変更**: `frontend/src/components/hitl/ClarificationButtons.tsx` — `selectedOption` state追加
- **動作**: 選択時ハイライト → 他ボタン無効化 → 送信

---

## フェーズ5: UX拡張機能（P1-18, P1-19, P1-22, P1-23, P1-26, P1-27, P1-28）

7件同時並列可。フェーズ4の基盤上に構築。

### P1-18: サジェストチップ
- **新規**: `frontend/src/components/chat/SuggestChips.tsx` — 4つのサジェストカード
- **変更**: `frontend/src/components/chat/ChatWindow.tsx` — `messages.length === 0` 時に表示
- **動作**: クリックで質問テキスト自動送信

### P1-19: ツール実行可視化
- **新規**: `frontend/src/lib/tool-labels.ts` — `TOOL_LABELS` マッピング（内部名→日本語ラベル）
- **変更**: `frontend/src/components/chat/ChatWindow.tsx` — ツール実行履歴の蓄積表示
- **変更**: `frontend/src/hooks/useChat.ts` — `toolHistory` state 追加

### P1-22: 新しい会話ボタン
- **変更**: `frontend/src/hooks/useChat.ts` — `resetConversation` メソッド追加
- **変更**: `frontend/src/App.tsx` — ヘッダーに「新しい会話」ボタン
- **動作**: 確認ダイアログ → 全状態リセット（messages, threadId, status）

### P1-23: フィードバック（thumbs up/down）
- **新規**: `frontend/src/components/chat/MessageFeedback.tsx` — ThumbsUp/Down ボタン
- **新規**: `backend/app/api/feedback.py` — `POST /api/feedback` エンドポイント
- **新規**: `backend/app/services/feedback_service.py` — フィードバック記録サービス（ファイル永続化）
- **変更**: `frontend/src/components/chat/MessageBubble.tsx` — アシスタントメッセージにフィードバック組込

### P1-26: アクセシビリティ
- **変更**: `ChatInput.tsx` — `aria-label="メッセージを入力"`
- **変更**: `TypingIndicator.tsx` — `aria-live="polite"`, `role="status"`
- **変更**: `ClarificationButtons.tsx` — `role="group"`, `aria-pressed`
- **変更**: `MessageBubble.tsx` — `role="article"`, `aria-label`
- **確認**: カラーコントラスト比 4.5:1 以上

### P1-27: モバイル対応
- **変更**: `App.tsx` — `100vh` → `100dvh`
- **変更**: `ChatInput.tsx` — ボタンタッチターゲット 44px以上
- **変更**: `ChatWindow.tsx` — `visualViewport` API でキーボード対応

### P1-28: エラーリカバリ手段
- **変更**: `frontend/src/hooks/useChat.ts` — `lastUserMessageRef` + `retry` メソッド
- **変更**: `frontend/src/components/chat/ChatWindow.tsx` — HTTP別エラーメッセージ、「再送信」「最初からやり直す」ボタン

---

## フェーズ6: エンタープライズ機能（P1-32）

### P1-32: ナレッジ管理API
- **新規**: `backend/app/models/knowledge.py` — `DocumentUploadRequest`, `DocumentResponse`
- **新規**: `backend/app/api/knowledge.py` — CRUD エンドポイント（POST/GET/PUT/DELETE `/api/knowledge`）
- **新規**: `backend/app/services/knowledge_service.py` — ドキュメント管理・再インデックス
- **変更**: `backend/app/main.py` — knowledge router 登録
- **テスト**: CRUD操作、認証、バリデーション

---

## 追加パッケージまとめ

### Backend (pyproject.toml)
- `sentence-transformers>=3.0.0` — P1-11
- `rank-bm25>=0.2.2` — P1-16
- `fugashi>=1.3.0` — P1-16（日本語トークナイズ）
- `unidic-lite>=1.0.8` — P1-16（fugashi辞書）

### Frontend (package.json)
- `react-markdown@^9.0.0` — P1-17
- `remark-gfm@^4.0.0` — P1-17
- `@tailwindcss/typography@^0.5.0` — P1-17（Tailwind v4互換要確認）

---

## リスク評価

| タスク | リスク | 対策 |
|--------|--------|------|
| P1-11 埋め込みモデル | 中: 初回DL時間、テストモック必要 | コレクション名バージョニング |
| P1-16 BM25 | 中: fugashi依存、インメモリ揮発 | lifespan初期化、alpha=1.0フォールバック |
| P1-31 SecretStr | 低〜中: get_secret_value()漏れ | 既存テストで検出可 |
| P1-24 SSEリトライ | 中: useChat型変更 | 段階的リファクタ |
| P1-17 Markdown | 低: Tailwind v4互換 | proseスタイル手動定義可 |

---

## 検証方法

各フェーズ完了後:
1. `cd backend && python -m pytest tests/ -v --tb=short` — 全テストパス確認
2. `cd frontend && npx tsc --noEmit` — 型チェック
3. `cd frontend && npx vite build` — ビルド成功確認
4. `cd backend && ruff check app/` — リントパス
5. 手動: `uvicorn app.main:app --reload` + `npm run dev` で動作確認

---

## 実装順序（チームワークフロー）

各フェーズ内のタスクは `general-purpose` エージェント（model: sonnet）で並列実装し、
完了後に `code-reviewer` エージェント（model: sonnet）でレビュー。
フェーズ間は順次進行（依存関係のため）。
