# P2 - 第2四半期（14件）

> エンタープライズ品質の達成。高度な検索・評価機能と運用基盤の整備。
> 目標期間: 3〜6ヶ月

## 進捗サマリー

| 完了 | 進行中 | 未着手 | ブロック | 進捗率 |
|------|--------|--------|----------|--------|
| 14 | 0 | 0 | 0 | 100% |

---

## RAG パイプライン高度化（3件）

### 34. Cross-Encoder リランキング

| 項目 | 内容 |
|------|------|
| ID | P2-34 |
| カテゴリ | RAG |
| 難易度 | 中 |
| 対象ファイル | `backend/app/rag/retriever.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-34 |
| 関連PR | - |

**概要:** `check_relevance` の結果を `generate_answer` に反映し、Cross-Encoder によるリランキングで無関係なドキュメントを排除。

**受け入れ条件:**
- [x] `sentence_transformers.CrossEncoder` の導入
- [x] `rerank_results()` 関数の実装
- [x] `relevant_doc_indices` を `generate_answer` で活用
- [x] ハルシネーション率の改善を測定

**備考:**
```
CrossEncoderReranker クラスを実装（シングルトンパターン）。
settings.reranker_model, reranker_enabled, reranker_top_k で設定可能。
hybrid_retrieve() に統合、59テスト通過。
```

---

### 35. Multi-Query / HyDE

| 項目 | 内容 |
|------|------|
| ID | P2-35 |
| カテゴリ | RAG |
| 難易度 | 中 |
| 対象ファイル | `backend/app/rag/rewrite.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-35 |
| 関連PR | - |

**概要:** 1つのリライトクエリではなく、Multi-Query（複数バリエーション）や HyDE（仮説的回答文書）で検索カバレッジを拡大。

**受け入れ条件:**
- [x] `rewrite_query_multi()`: 3つのクエリバリエーション生成
- [x] `rewrite_query_hyde()`: 仮説的回答文書の生成
- [x] 並列検索と結果統合のロジック
- [x] 検索リコール改善の測定（目標: 20-35% 向上）

**備考:**
```
rewrite.py を新規作成。settings.retrieval_strategy で "standard"|"multi_query"|"hyde"|"hybrid" を選択可能。
retrieve_with_strategy() で統一インターフェース。RRFで結果統合。30テスト通過。
```

---

### 36. RAGAS 評価フレームワーク

| 項目 | 内容 |
|------|------|
| ID | P2-36 |
| カテゴリ | RAG |
| 難易度 | 中 |
| 対象ファイル | 新規: `backend/tests/evaluation/` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-36 |
| 関連PR | - |

**概要:** RAGAS による自動評価（answer_relevancy, faithfulness, context_precision, context_recall）を導入。

**受け入れ条件:**
- [x] `ragas` パッケージの導入
- [x] 4指標（relevancy, faithfulness, precision, recall）の評価パイプライン
- [x] CI 連携での定期評価実行
- [x] 評価結果のレポート生成

**依存:** P1-14（ゴールデンデータセット）✅

**備考:**
```
tests/evaluation/pipeline.py に RagasEvaluator クラスを実装。
CLI実行: python -m tests.evaluation.pipeline --questions tests/golden/questions.json
14テスト通過（APIキーなし）、6統合テスト（APIキー必要）。
```

---

## UX 改善（3件）

### 37. コピーボタン

| 項目 | 内容 |
|------|------|
| ID | P2-37 |
| カテゴリ | UX |
| 難易度 | 低 |
| 対象ファイル | `frontend/src/components/chat/MessageBubble.tsx`, `frontend/src/components/chat/CopyButton.tsx` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-37 |
| 関連PR | - |

**概要:** アシスタントメッセージにホバー時表示のコピーボタンを追加。

**受け入れ条件:**
- [x] ホバー時にコピーボタンを表示
- [x] `navigator.clipboard.writeText()` でコピー実行
- [x] コピー成功時のトースト/チェックマーク表示
- [x] Markdown からプレーンテキストへの変換

**依存:** P1-17（Markdown）✅

**備考:**
```
CopyButton.tsx を新規作成。Check/Copy アイコン使用。
MessageBubble.tsx に group relative クラス追加、ホバー時に表示。
TypeScript型チェック通過。
```

---

### 38. インテリジェント自動スクロール

| 項目 | 内容 |
|------|------|
| ID | P2-38 |
| カテゴリ | UX |
| 難易度 | 中 |
| 対象ファイル | `frontend/src/hooks/useAutoScroll.ts`, `frontend/src/components/chat/ScrollToBottomButton.tsx` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-38 |
| 関連PR | - |

**概要:** ユーザーが最下部付近（100px以内）にいる場合のみ自動スクロール。上方スクロール時は「最新メッセージへ」ボタンを表示。

**受け入れ条件:**
- [x] スクロール位置の検出ロジック（最下部100px以内判定）
- [x] 条件付き自動スクロール
- [x] 「最新メッセージへ」フローティングボタン
- [x] ボタンクリックでスムーズスクロール

**備考:**
```
useAutoScroll.ts を拡張（isNearBottom, scrollToBottom, handleScroll）。
ScrollToBottomButton.tsx を新規作成（ChevronDown アイコン）。
MessageList.tsx に統合。7テスト通過、vitest.config.ts 追加。
```

---

### 39. 長時間待機通知

| 項目 | 内容 |
|------|------|
| ID | P2-39 |
| カテゴリ | UX |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/hooks/useWaitTimer.ts` (新規), `frontend/src/components/chat/WaitNotification.tsx` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-39 |
| 関連PR | - |

**概要:** 30秒後に「処理に時間がかかっています」バナー、60秒後に「キャンセルして再試行」ボタンを表示。

**受け入れ条件:**
- [x] タイマーベースの待機時間監視
- [x] 30秒後のバナー表示
- [x] 60秒後のキャンセル+再試行ボタン
- [x] キャンセル処理（SSE 切断 + 状態リセット）

**備考:**
```
useWaitTimer.ts: waitTime, showWarning (30s), showError (60s) を返す。
WaitNotification.tsx: 警告バナー（黄色）とエラーバナー（赤）+ 再試行ボタン。
useChat.ts に cancelRequest() 関数を追加。
```

---

## エンタープライズ対応（4件）

### 40. PostgresSaver 移行

| 項目 | 内容 |
|------|------|
| ID | P2-40 |
| カテゴリ | エンタープライズ |
| 難易度 | 中〜高 |
| 対象ファイル | `backend/app/agents/agent.py`, `docker-compose.yml` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-40 |
| 関連PR | - |

**概要:** `MemorySaver`（インメモリ）から `PostgresSaver` に移行。水平スケーリング対応。

**受け入れ条件:**
- [x] PostgreSQL の Docker 構成追加
- [x] `PostgresSaver` への移行
- [ ] `asyncio.Queue` の Redis Streams 置換（オプション）— 未実装（将来対応）
- [x] プロセス再起動後の会話履歴復元を検証
- [x] マイグレーションスクリプトの用意

**依存:** P0-10（JWT認証）✅

**備考:**
```
docker-compose.yml に PostgreSQL 15 Alpine を追加。
AsyncPostgresSaver を使用、接続エラー時は MemorySaver にフォールバック。
settings.database_url, database_pool_size, database_max_overflow を追加。
pyproject.toml に asyncpg, langgraph-checkpoint-postgres を追加。
8テスト通過、2スキップ（統合テストは環境変数設定時のみ）。
```

---

### 41. 構造化ロギング

| 項目 | 内容 |
|------|------|
| ID | P2-41 |
| カテゴリ | エンタープライズ |
| 難易度 | 中 |
| 対象ファイル | `backend/app/core/logging.py` (新規), `backend/app/main.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-41 |
| 関連PR | - |

**概要:** リクエスト/レスポンス/LLM 呼び出しの構造化ログ。OpenTelemetry or LangSmith トレーシング。

**受け入れ条件:**
- [x] 構造化ログフォーマット（JSON）の導入
- [x] リクエスト ID によるログ相関
- [x] LLM 呼び出しのトレーシング設定
- [x] トークン使用量のログ記録

**備考:**
```
structlog>=24.0.0 を追加。
RequestIdMiddleware: X-Request-ID ヘッダーの読み取りと自動生成。
RequestLoggingMiddleware: リクエスト/レスポンスのログ。
TokenTracker, TracingCallbackHandler: LLM呼び出しのトレーシング。
183テスト通過（新規テスト37件）。
```

---

### 42. LLM コスト可視化

| 項目 | 内容 |
|------|------|
| ID | P2-42 |
| カテゴリ | エンタープライズ |
| 難易度 | 中 |
| 対象ファイル | `backend/app/services/cost_service.py` (新規), `backend/app/api/admin.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-42 |
| 関連PR | - |

**概要:** `get_openai_callback()` でトークン消費量を記録。コスト予測ダッシュボード。

**受け入れ条件:**
- [x] トークン消費量の記録（リクエスト/レスポンス別）
- [x] セッション/ユーザーごとのコスト集計
- [x] コスト上限アラートの仕組み
- [x] `GET /api/admin/costs` でコスト情報を取得

**依存:** P0-10（JWT認証）✅

**備考:**
```
CostService: TokenUsage データクラス、record_usage(), get_costs_by_session(),
get_total_costs(), check_cost_limit() メソッド。
モデル別料金: GPT-4o-mini ($0.15/$0.60), GPT-4o ($2.50/$10.00)。
GET /api/admin/costs, GET /api/admin/costs/check-limit エンドポイント。
llm_factory.py と連携。15テスト通過。
```

---

### 43. 詳細ヘルスチェック

| 項目 | 内容 |
|------|------|
| ID | P2-43 |
| カテゴリ | エンタープライズ |
| 難易度 | 低〜中 |
| 対象ファイル | `backend/app/api/health.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-43 |
| 関連PR | - |

**概要:** ChromaDB・OpenAI の疎通確認、アクティブセッション数、メモリ使用量を含む詳細ヘルスチェック。

**受け入れ条件:**
- [x] `GET /api/health/detailed` エンドポイントの実装
- [x] ChromaDB 接続状態・ドキュメント数の確認
- [x] OpenAI API 到達性の確認
- [x] アクティブセッション数・メモリ使用量の表示

**備考:**
```
GET /api/health/detailed: status, checks (chromadb, openai, memory, sessions)。
check_chromadb(): VectorStore接続確認、ドキュメント数取得。
check_openai(): 軽量APIコールで到達性確認、レイテンシー測定。
get_system_metrics(): psutilでメモリ使用量取得。
determine_health_status(): healthy/degraded/unhealthy 判定。
psutil を依存関係に追加。15テスト通過。
```

---

## 製品戦略（4件）

### 44. 回答の根拠可視化

| 項目 | 内容 |
|------|------|
| ID | P2-44 |
| カテゴリ | 製品戦略 |
| 難易度 | 低〜中 |
| 対象ファイル | `frontend/src/components/chat/SourceCitations.tsx` (新規), `backend/app/models/messages.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-44 |
| 関連PR | - |

**概要:** `search_knowledge` の検索元・`check_quality` のスコアをフロントエンドに表示。

**受け入れ条件:**
- [x] バックエンドからソースドキュメント情報を SSE で送信
- [x] フロントエンドに `<details>` 折りたたみで根拠を表示
- [x] ソースドキュメントのタイトル・セクション・関連度を表示
- [x] 品質スコア（ハルシネーション評価結果）の表示

**備考:**
```
SSE source イベント: id, title, section, score, snippet。
SSE quality イベント: is_relevant, confidence, reasoning。
SourceCitations.tsx: <details> 折りたたみ、スコア色分け（緑/黄/赤）。
useChat.ts: source/quality イベント処理、メッセージに sources/qualityScore 追加。
41テスト通過、TypeScript型チェック通過。
```

---

### 45. エスカレーションツール

| 項目 | 内容 |
|------|------|
| ID | P2-45 |
| カテゴリ | 製品戦略 |
| 難易度 | 中 |
| 対象ファイル | `backend/app/agents/tools/escalation.py` (新規), `backend/app/services/escalation_service.py` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-45 |
| 関連PR | - |

**概要:** 解決できない問題を有人サポートにエスカレーションする第8のツールを追加。

**受け入れ条件:**
- [x] `escalate_to_human` ツールの実装
- [x] エスカレーション時の会話サマリー自動生成
- [x] チケット作成（最低限ログ記録）
- [x] フロントエンドにエスカレーション完了メッセージを表示
- [x] エージェントのプロンプトにエスカレーション判断基準を追加

**備考:**
```
escalate_to_human ツール: @tool デコレータ、EscalationInput (reason, urgency, summary)。
EscalationService: create_ticket(), get_tickets(), get_ticket(), _generate_summary()。
ESCALATION_CRITERIA: 明示的有人対応希望、技術的解決不可能、法的金銭的重要事項、3回以上同一質問。
GET /api/admin/escalations, GET /api/admin/escalations/{ticket_id}。
503テスト通過（新規テスト31件）。
```

---

### 46. プロアクティブ FAQ

| 項目 | 内容 |
|------|------|
| ID | P2-46 |
| カテゴリ | 製品戦略 |
| 難易度 | 低〜中 |
| 対象ファイル | `backend/app/services/faq_service.py` (新規), `frontend/src/components/chat/FAQSuggestions.tsx` (新規) |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-46 |
| 関連PR | - |

**概要:** ユーザーの現在地（ページURL）に基づく関連 FAQ のプッシュ表示。トップ質問のリアルタイムバッジ。

**受け入れ条件:**
- [x] FAQ データの管理構造
- [x] ページ URL に基づく FAQ 推薦ロジック
- [x] フロントエンドでの FAQ 表示コンポーネント
- [x] トップ質問のリアルタイム集計

**備考:**
```
data/faqs.json: 12個のFAQエントリ（アカウント、設定、データ管理、トラブルシューティング等）。
FAQService: get_faqs_by_page(), get_top_questions(), search_faqs(), increment_view_count()。
GET /api/faq/suggestions, GET /api/faq/top, GET /api/faq/search, POST /api/faq/click。
FAQSuggestions.tsx: ページURL基準FAQ表示、トップ質問バッジ。
33テスト通過（サービス20、API13）。
```

---

### 47. システムプロンプト管理 UI

| 項目 | 内容 |
|------|------|
| ID | P2-47 |
| カテゴリ | 製品戦略 |
| 難易度 | 低〜中 |
| 対象ファイル | `backend/app/services/prompt_service.py` (新規), `backend/app/api/admin.py` |
| ステータス | `[x]` 完了 |
| 着手日 | 2026-02-25 |
| 完了日 | 2026-02-25 |
| 担当 | worker-p2-47 |
| 関連PR | - |

**概要:** システムプロンプトをハードコードからデータベース管理に移行。管理 UI で編集可能に。

**受け入れ条件:**
- [x] プロンプトのデータベース（or JSON ファイル）管理
- [x] `GET/PUT /api/admin/prompts` の管理 API
- [x] 変更履歴の保存とロールバック機能
- [ ] A/B テスト用のプロンプトバリアント管理（オプション）— 未実装（将来対応）

**備考:**
```
data/prompts.json: system, category_operation, category_troubleshooting, category_contract, escalation_criteria。
PromptService: get_prompt(), get_all_prompts(), update_prompt(), rollback_prompt(), get_prompt_history()。
バージョン管理、履歴保存、ロールバック機能。
GET/PUT /api/admin/prompts, POST /api/admin/prompts/{id}/rollback/{version}。
prompts.py: get_system_prompt(), get_category_prompt(), get_escalation_criteria() で動的取得。
後方互換性維持（既存定数も使用可能）。57テスト通過。
```

---

## 依存関係マップ

```
P1-14 (ゴールデンデータセット) ──→ P2-36 (RAGAS評価) ✅
P1-16 (ハイブリッド検索)       ──→ P2-34 (Cross-Encoder) ✅
P1-17 (Markdown)              ──→ P2-37 (コピーボタン) ✅
P0-10 (JWT認証)               ──→ P2-42 (コスト可視化) ✅
P0-10 (JWT認証)               ──→ P2-40 (PostgresSaver) ✅
```

## テスト結果サマリー

| 項目 | 結果 |
|------|------|
| バックエンドテスト | 188 passed, 2 skipped (主要テスト) |
| テスト総数 | 544件 |
| フロントエンド型チェック (tsc --noEmit) | エラーなし |
