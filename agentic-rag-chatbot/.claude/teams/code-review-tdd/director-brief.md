# Director Mission Brief: Code Review TDD Implementation

## プロジェクト目標
コードレビューレポート `/workspace/agentic-rag-chatbot/tasks/code-review-2026-02-28.md` の残り指摘事項に TDD アプローチで対応する。

## 技術スタック
- Backend: Python (FastAPI, LangGraph)
- Frontend: TypeScript (React, Vite)

## ブランチ
- `fix/code-review-tdd-2026-02-28` (既に作成済み)

## 対応項目一覧

### Medium Priority Issues (5件)

**#4 MessageFeedback Silent Failure** (MEDIUM)
- 場所: `frontend/src/components/chat/MessageFeedback.tsx:25-32`
- 対応: エラー状態表示、「送信失敗」メッセージ、リトライボタン追加
- テスト: エラー発生時のUI表示を確認するテスト

**#5 FAQSuggestions Error Swallowing** (MEDIUM)
- 場所: `frontend/src/components/chat/FAQSuggestions.tsx:19-57`
- 対応: 構造化ロギング追加、`logger` import使用
- テスト: 不要（ロギング追加のみ）

**#6 Invalid Status Filter Silently Ignored** (MEDIUM)
- 場所: `backend/app/api/experiments.py:71-74`
- 対応: 警告ログ追加、有効値をログに含める
- テスト: 不要（ロギング追加のみ）

**#7 LLM Cost Recording Error Details Missing** (MEDIUM)
- 場所: `backend/app/agents/llm_factory.py:167-171`
- 対応: エラー詳細（str(e), type(e).__name__）をログに追加
- テスト: 不要（ロギング追加のみ）

**#8 ErrorBoundary Missing Error Tracking** (MEDIUM)
- 場所: `frontend/src/components/ErrorBoundary.tsx:25`
- 対応: 構造化ロガー使用、Sentry連携準備（コメント）
- テスト: 不要（ロギング追加のみ）

### Code Simplification (6件)

**S1. Split get_recommended_faqs Method**
- 場所: `backend/app/services/faq_service.py`
- 対応: プライベートメソッドに分割（_add_page_based_faqs, _add_user_interest_faqs, _fill_with_top_faqs）
- テスト: 既存テストがパスすることを確認

**S2. Extract RRF Score Calculation**
- 場所: `backend/app/rag/retriever.py`
- 対応: `_calculate_rrf_scores()` ヘルパー関数を抽出
- テスト: 既存テストがパスすることを確認

**S3. Extract Error Handling in useChat**
- 場所: `frontend/src/hooks/useChat.ts`
- 対応: `getErrorMessage()` ヘルパー関数を抽出
- テスト: ユニットテスト追加

**S4. Create API Client Wrapper**
- 場所: `frontend/src/lib/api.ts`
- 対応: `apiRequest()` 汎用ラッパー関数を作成
- テスト: ユニットテスト追加

**S5. Introduce StreamState Dataclass**
- 場所: `backend/app/services/chat_service.py`
- 対応: リスト代わりに `@dataclass StreamState` を使用
- テスト: 既存テストがパスすることを確認

**S6. Add Caching to prompts.py**
- 場所: `backend/app/agents/prompts.py`
- 対応: `_get_prompt_service()` に `@lru_cache` 追加
- テスト: 既存テストがパスすることを確認

**S7. AgentManager Class** - スキップ（大規模リファクタリングのため）

### Documentation Updates (3件)

**D1. Update retriever.py "hybrid" Strategy Docstring**
- 場所: `backend/app/rag/retriever.py:278-281`
- 変更: `"将来的に BM25 と組み合わせ可能"` → `"hybrid": hybrid_retrieve を使用した BM25 + Vector + RRF 統合検索`

**D2. Clarify Tool Count in README**
- 場所: `README.md:59`
- 変更: `"11ツール: 8コアツール + ..."` → `"8コアツール（エージェント内）+ 3スタンドアロンツール（API/ミドルウェアレベル）"`

**D3. Update Frontend README**
- 場所: `frontend/README.md`
- 対応: プロジェクト固有のドキュメント追加

## TDD手順

各修正に対して（テストが必要な場合）:
1. **RED**: 修正内容を検証するテストを先に書く
2. **GREEN**: テストを通す最小限の実装
3. **REFACTOR**: コード品質を改善
4. テストを実行して確認

※ ドキュメント更新（D1-D3）と単純なロギング追加（#5, #6, #7, #8）はテスト不要

## 優先順位

1. Medium Priority Issues (#4-#8) - 機能品質向上
2. Code Simplification (S1-S6) - コード保守性向上
3. Documentation (D1-D3) - ドキュメント整合性

## 完了条件
- 全ての指摘に対応
- テストが全てパス
- 変更をコミット（amend ではなく新規コミット）

## 既存ファイル構造

### Backend
- `/workspace/agentic-rag-chatbot/backend/app/api/experiments.py` - 実験管理API
- `/workspace/agentic-rag-chatbot/backend/app/agents/llm_factory.py` - LLMファクトリ
- `/workspace/agentic-rag-chatbot/backend/app/services/faq_service.py` - FAQサービス
- `/workspace/agentic-rag-chatbot/backend/app/services/chat_service.py` - チャットサービス
- `/workspace/agentic-rag-chatbot/backend/app/rag/retriever.py` - RAGリトリーバー
- `/workspace/agentic-rag-chatbot/backend/app/agents/prompts.py` - プロンプト管理

### Frontend
- `/workspace/agentic-rag-chatbot/frontend/src/components/chat/MessageFeedback.tsx` - フィードバックコンポーネント
- `/workspace/agentic-rag-chatbot/frontend/src/components/chat/FAQSuggestions.tsx` - FAQ提案コンポーネント
- `/workspace/agentic-rag-chatbot/frontend/src/components/ErrorBoundary.tsx` - エラーバウンダリ
- `/workspace/agentic-rag-chatbot/frontend/src/hooks/useChat.ts` - チャットフック
- `/workspace/agentic-rag-chatbot/frontend/src/lib/api.ts` - APIクライアント
- `/workspace/agentic-rag-chatbot/frontend/src/lib/logger.ts` - ロガー

### Documentation
- `/workspace/agentic-rag-chatbot/README.md` - メインREADME
- `/workspace/agentic-rag-chatbot/frontend/README.md` - フロントエンドREADME
