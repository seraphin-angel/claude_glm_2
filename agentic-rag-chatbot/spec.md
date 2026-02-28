# Agentic RAG チャットボット — システム仕様書

> バージョン: 0.4.0
> 作成日: 2026-02-22
> 最終更新: 2026-02-28 (P3完了反映)

---

## 目次

1. [概要](#1-概要)
2. [システムアーキテクチャ](#2-システムアーキテクチャ)
3. [バックエンド仕様](#3-バックエンド仕様)
4. [フロントエンド仕様](#4-フロントエンド仕様)
5. [データフロー](#5-データフロー)
6. [設定・環境変数](#6-設定環境変数)
7. [テスト戦略](#7-テスト戦略)
8. [サンプルデータ](#8-サンプルデータ)
9. [制限事項・今後の課題](#9-制限事項今後の課題)

---

## 1. 概要

### プロジェクトの目的と背景

本プロジェクトは、製品サポート業務を自動化するための **Agentic RAG チャットボット**である。従来の単純な FAQ 検索ではなく、LangGraph による ReAct エージェントループと RAG（Retrieval-Augmented Generation）を組み合わせることで、高品質かつ根拠に基づいた回答を自動生成する。

エージェントはユーザーの質問を分類・最適化し、ナレッジベースを検索して回答を生成する。情報が不足している場合は HITL（Human-in-the-Loop）機能によりユーザーへの確認を挟む仕組みを持つ。

### 主要機能の要約

| 機能 | 説明 |
|------|------|
| 製品サポート Q&A | 製品の操作方法・障害対応・契約料金に関する質問に回答 |
| RAG 検索 | ChromaDB によるベクトル類似検索でナレッジベースから根拠を取得 |
| クエリ最適化 | 代名詞解決・曖昧表現の具体化によるクエリリライト |
| 品質チェック | ハルシネーション評価・充足性評価による回答品質保証 |
| HITL 対話 | 曖昧な質問に対してボタン選択またはテキスト入力で確認を求める |
| SSE ストリーミング | Server-Sent Events によるリアルタイムトークン配信 |
| スレッド管理 | 会話スレッドの継続・MemorySaver による状態保持 |
| エスカレーション | 解決不能な問題の有人サポートへのエスカレーション（チケット管理） |
| コスト可視化 | トークン消費量の記録とモデル別コスト集計 |
| 構造化ロギング | structlog による JSON 形式の構造化ログとリクエストトレーシング |
| プロアクティブ FAQ | ページ URL に基づく FAQ 推薦とトップ質問表示 |
| マルチテナント | テナントごとの設定分離・ミドルウェアによるテナント識別 (P3) |
| GDPR/データ保持 | テナント別保持ポリシー・ユーザーデータ削除・監査ログ (P3) |
| CRM 連携 | Zendesk アダプターによるチケット連携 (P3) |
| 画像添付 | Vision API によるスクリーンショット解析 (P3) |
| 多言語対応 | i18next による日本語/英語 UI 切り替え (P3) |
| マルチチャネル | LINE/Slack/Email Webhook アダプター (P3) |
| パーソナライゼーション | ユーザープロファイル・推薦 (P3) |
| A/B テスト | 実験管理・バリアント割り当て・メトリクス (P3) |
| ガードレール | ジェイルブレイク対策・PII 検出・入出力安全性チェック (P3) |

### 技術スタック一覧

#### バックエンド

| カテゴリ | 技術 | バージョン |
|----------|------|-----------|
| Webフレームワーク | FastAPI | >=0.115.0 |
| ASGIサーバー | Uvicorn | >=0.32.0 |
| エージェントフレームワーク | LangGraph | >=0.2.0 |
| LLM ライブラリ | LangChain | >=0.3.0 |
| LLM プロバイダー | langchain-openai | >=0.3.0 |
| ベクトルDB | ChromaDB | >=0.5.0 |
| データバリデーション | Pydantic v2 | >=2.9.0 |
| 設定管理 | pydantic-settings | >=2.6.0 |
| テキスト分割 | langchain-text-splitters | >=0.3.0 |
| レート制限 | slowapi | >=0.1.9 |
| JWT 認証 | python-jose[cryptography] | >=3.3.0 |
| 埋め込みモデル | sentence-transformers | >=3.0.0 |
| BM25検索 | rank_bm25 | >=0.2.2 |
| 日本語トークナイザー | fugashi | >=1.3.0 |
| Python | Python | >=3.11 |
| 構造化ロギング | structlog | >=24.0.0 |
| システムメトリクス | psutil | 最新 |
| PostgreSQL ドライバ | asyncpg | 最新 |
| チェックポインタ | langgraph-checkpoint-postgres | 最新 |
| Cross-Encoder | sentence-transformers (CrossEncoder) | >=3.0.0 |

#### フロントエンド

| カテゴリ | 技術 | バージョン |
|----------|------|-----------|
| UI フレームワーク | React | ^19.2.0 |
| ビルドツール | Vite | ^7.3.1 |
| 言語 | TypeScript | ~5.9.3 |
| スタイリング | Tailwind CSS | ^4.2.0 |
| UI コンポーネント | Radix UI (scroll-area, slot) | 最新 |
| アイコン | lucide-react | ^0.575.0 |
| Markdownレンダリング | react-markdown | ^10.1.0 |
| GFM対応 | remark-gfm | ^4.0.1 |
| タイポグラフィ | @tailwindcss/typography | ^0.5.16" |
| 多言語対応 | i18next | ^25.8.13 |
| 多言語対応 | react-i18next | ^16.5.4 |
| 画像アップロード | react-dropzone | ^15.0.0 |
| Markdown サニタイズ | rehype-sanitize | ^6.0.0 |

---

## 2. システムアーキテクチャ

### 全体構成図

```mermaid
graph LR
    subgraph Frontend["フロントエンド (React + Vite :5173)"]
        UI[Chat UI]
        SSEClient[SSE Client]
        HITLWidget[HITL Widget]
    end

    subgraph Backend["バックエンド (FastAPI :8000)"]
        API[API Router]
        ChatService[Chat Service]
        Agent["Deep Agent<br/>LangGraph ReAct"]
    end

    subgraph RAG["RAG パイプライン"]
        Retriever[Retriever]
        VectorStore["ChromaDB<br/>Vector Store"]
        Docs[("sample_docs<br/>*.md")]
    end

    subgraph LLM["外部サービス"]
        OpenAI["OpenAI API<br/>gpt-4o-mini"]
    end

    UI -->|POST /api/chat| API
    UI -->|GET /api/chat/stream/:id| SSEClient
    HITLWidget -->|POST /api/chat/resume/:id| API
    API --> ChatService
    ChatService -->|astream_events| Agent
    Agent -->|ツール呼び出し| Retriever
    Retriever --> VectorStore
    VectorStore -->|起動時ロード| Docs
    Agent -->|LLM推論| OpenAI
    ChatService -->|SSE イベント| SSEClient
```

### レイヤー構成図

```mermaid
graph TB
    subgraph L1["プレゼンテーション層 (Frontend)"]
        direction LR
        A1[App.tsx]
        A2[ChatWindow]
        A3[MessageList / ChatInput]
        A4[HITLWidget]
    end

    subgraph L2["API 層 (FastAPI Router)"]
        direction LR
        B1["POST /api/chat"]
        B2["GET /api/chat/stream/:id"]
        B3["POST /api/chat/resume/:id"]
        B4["GET /api/health"]
    end

    subgraph L3["サービス層"]
        direction LR
        C1[ChatService]
        C2[asyncio.Queue]
        C3[asyncio.Task]
    end

    subgraph L4["エージェント層 (LangGraph)"]
        direction LR
        D1["Deep Agent<br/>ReAct Loop"]
        D2["MemorySaver<br/>Checkpointer"]
        D3[7 Tools]
    end

    subgraph L5["データ層"]
        direction LR
        E1["VectorStore<br/>ChromaDB"]
        E2[Retriever]
        E3[DocumentLoader]
        E4[(Markdown Docs)]
    end

    L1 -->|HTTP / SSE| L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
```

### ディレクトリ構成

```
agentic-rag-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI アプリ本体・ライフサイクル管理
│   │   ├── core/
│   │   │   └── logging.py           # 構造化ロギング・ミドルウェア (P2)
│   │   ├── api/
│   │   │   ├── __init__.py          # ルーター集約
│   │   │   ├── chat.py              # チャット API エンドポイント
│   │   │   ├── health.py            # ヘルスチェック
│   │   │   ├── feedback.py          # フィードバック API (P1)
│   │   │   ├── knowledge.py         # ナレッジ管理 API (P1)
│   │   │   ├── admin.py             # 管理者 API - ナレッジギャップ (P1)
│   │   │   ├── faq.py               # FAQ API エンドポイント (P2)
│   │   │   ├── gdpr.py              # GDPR API (P3)
│   │   │   ├── tenant.py            # テナント API (P3)
│   │   │   ├── channels.py          # チャネル API (P3)
│   │   │   ├── experiments.py       # 実験 API (P3)
│   │   │   ├── guardrails.py        # ガードレール API (P3)
│   │   │   ├── user.py              # ユーザー API (P3)
│   │   │   └── integrations.py      # インテグレーション API (P3)
│   │   ├── auth/
│   │   │   ├── __init__.py          # 公開関数エクスポート
│   │   │   └── jwt_handler.py       # JWT トークン生成・検証
│   │   ├── agents/
│   │   │   ├── agent.py             # Deep Agent 構築・シングルトン管理
│   │   │   ├── llm_factory.py       # @lru_cache LLM ファクトリ
│   │   │   ├── output_models.py     # StructuredOutput 用 Pydantic モデル
│   │   │   ├── prompts.py           # システムプロンプト定義 (カテゴリ別Few-shot含む)
│   │   │   ├── state.py             # AgentState TypedDict
│   │   │   └── tools/
│   │   │       ├── __init__.py      # ツールのエクスポート
│   │   │       ├── classify.py      # クエリ分類ツール
│   │   │       ├── rewrite.py       # クエリリライトツール
│   │   │       ├── search.py        # ナレッジ検索ツール
│   │   │       ├── relevance.py     # 関連性評価ツール (ギャップ記録含む)
│   │   │       ├── generate.py      # 回答生成ツール (カテゴリ別プロンプト)
│   │   │       ├── quality.py       # 品質チェックツール
│   │   │       ├── ask_human.py     # HITL ツール
│   │   │       ├── escalation.py    # エスカレーションツール (P2)
│   │   │       ├── content_safety.py # コンテンツ安全性ツール (P3)
│   │   │       └── image_analysis.py # 画像解析ツール (P3)
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py            # テナント識別ミドルウェア (P3)
│   │   │   ├── guardrails.py        # ガードレールミドルウェア (P3)
│   │   │   └── user_context.py      # ユーザーコンテキストミドルウェア (P3)
│   │   ├── channels/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # チャネルアダプター基底クラス (P3)
│   │   │   ├── models.py            # チャネルモデル (P3)
│   │   │   ├── line_adapter.py      # LINE アダプター (P3)
│   │   │   ├── slack_adapter.py     # Slack アダプター (P3)
│   │   │   ├── email_adapter.py     # Email アダプター (P3)
│   │   │   └── mock_adapter.py      # テスト用モックアダプター (P3)
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # 連携基底クラス (P3)
│   │   │   ├── zendesk.py           # Zendesk 連携 (P3)
│   │   │   └── mock_adapter.py      # テスト用モック (P3)
│   │   ├── config/
│   │   │   └── settings.py          # 設定管理 (pydantic-settings)
│   │   ├── rate_limit.py              # slowapi Limiter インスタンス
│   │   ├── models/
│   │   │   ├── chat.py              # ChatRequest / ChatStartResponse
│   │   │   ├── messages.py          # StreamEvent / StreamEventType
│   │   │   ├── hitl.py              # HITLRequest / HITLResponse / ResumeRequest
│   │   │   ├── tenant.py            # テナントモデル (P3)
│   │   │   ├── user.py              # ユーザーモデル (P3)
│   │   │   ├── experiment.py        # 実験モデル (P3)
│   │   │   ├── guardrails.py        # ガードレールモデル (P3)
│   │   │   └── retention.py         # 保持ポリシーモデル (P3)
│   │   ├── rag/
│   │   │   ├── vector_store.py      # ChromaDB ラッパー (multilingual-e5-base)
│   │   │   ├── bm25_store.py        # BM25 インデックス (P1)
│   │   │   ├── retriever.py         # ハイブリッド検索 (BM25 + Vector + RRF)
│   │   │   ├── document_loader.py   # Markdown ローダー・チャンク分割
│   │   │   └── rewrite.py           # Multi-Query / HyDE クエリリライト (P2)
│   │   └── services/
│   │       ├── chat_service.py      # ChatService・イベントキュー管理
│   │       ├── feedback_service.py  # フィードバック永続化 (P1)
│   │       ├── knowledge_service.py # ナレッジ CRUD (P1)
│   │       ├── gap_service.py       # ナレッジギャップ検出 (P1)
│   │       ├── cost_service.py      # LLM コスト可視化 (P2)
│   │       ├── escalation_service.py # エスカレーション管理 (P2)
│   │       ├── faq_service.py       # FAQ サービス (P2)
│   │       ├── prompt_service.py    # プロンプト管理 (P2)
│   │       ├── tenant_service.py    # テナントサービス (P3)
│   │       ├── user_service.py      # ユーザーサービス (P3)
│   │       ├── experiment_service.py # 実験サービス (P3)
│   │       ├── guardrails_service.py # ガードレールサービス (P3)
│   │       ├── retention_service.py # データ保持サービス (P3)
│   │       ├── channel_service.py   # チャネルサービス (P3)
│   │       ├── integration_service.py # 連携サービス (P3)
│   │       ├── statistics_service.py # 統計サービス (P3)
│   │       ├── metrics_service.py   # メトリクスサービス (P3)
│   │       └── language_service.py  # 言語サービス (P3)
│   ├── data/
│   │   ├── chroma_db/               # ChromaDB 永続化ディレクトリ
│   │   ├── feedback.json            # フィードバックデータ (P1)
│   │   ├── knowledge_gaps.json      # ナレッジギャップデータ (P1)
│   │   ├── faqs.json                # FAQ データ (P2)
│   │   ├── prompts.json             # プロンプトデータ (P2)
│   │   ├── token_usage.json         # トークン使用量データ (P2)
│   │   ├── escalations.json         # エスカレーションデータ (P2)
│   │   └── sample_docs/
│   │       ├── product_guide.md     # 操作方法 FAQドキュメント
│   │       ├── troubleshooting.md   # 障害・トラブル FAQドキュメント
│   │       └── contracts.md         # 契約・料金 FAQドキュメント
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_auth.py             # JWT 認証テスト
│   │   ├── test_integration.py
│   │   ├── test_llm_factory.py      # LLM ファクトリテスト
│   │   ├── test_models.py
│   │   ├── test_output_models.py    # StructuredOutput モデルテスト
│   │   ├── test_rag.py
│   │   ├── test_tools.py
│   │   ├── test_bm25.py             # BM25検索テスト (P1)
│   │   ├── test_cors.py             # CORS設定テスト (P1)
│   │   ├── test_feedback.py         # フィードバックテスト (P1)
│   │   ├── test_gap_service.py      # ナレッジギャップテスト (P1)
│   │   ├── test_golden.py           # ゴールデンデータセットテスト (P1)
│   │   ├── test_knowledge.py        # ナレッジ管理テスト (P1)
│   │   ├── test_prompts.py          # カテゴリ別プロンプトテスト (P1)
│   │   ├── test_security_headers.py # セキュリティヘッダーテスト (P1)
│   │   ├── test_escalation_service.py # エスカレーション機能テスト (P2)
│   │   ├── test_faq_api.py          # FAQ API テスト (P2)
│   │   ├── test_prompt_service.py   # プロンプト管理テスト (P2)
│   │   ├── test_settings.py         # 設定値テスト（P2項目含む）(P2)
│   │   ├── test_channels.py         # チャネルアダプターテスト (P3)
│   │   ├── test_content_safety.py   # コンテンツ安全性テスト (P3)
│   │   ├── test_crm_integration.py  # CRM連携テスト (P3)
│   │   ├── test_experiment_api.py   # 実験APIテスト (P3)
│   │   ├── test_experiment_models.py # 実験モデルテスト (P3)
│   │   ├── test_experiment_service.py # 実験サービステスト (P3)
│   │   ├── test_guardrails.py       # ガードレールテスト (P3)
│   │   ├── test_guardrails_api.py   # ガードレールAPIテスト (P3)
│   │   ├── test_guardrails_middleware.py # ガードレールミドルウェアテスト (P3)
│   │   ├── test_guardrails_models.py # ガードレールモデルテスト (P3)
│   │   ├── test_guardrails_service.py # ガードレールサービステスト (P3)
│   │   ├── test_image_analysis.py   # 画像解析テスト (P3)
│   │   ├── test_image_api.py        # 画像APIテスト (P3)
│   │   ├── test_language_service.py # 言語サービステスト (P3)
│   │   ├── test_metrics_service.py  # メトリクスサービステスト (P3)
│   │   ├── test_statistics_service.py # 統計サービステスト (P3)
│   │   ├── test_tenant.py           # テナントテスト (P3)
│   │   ├── test_user.py             # ユーザーテスト (P3)
│   │   ├── test_user_context_middleware.py # ユーザーコンテキストミドルウェアテスト (P3)
│   │   ├── evaluation/              # RAGAS 評価フレームワーク (P2)
│   │   │   └── pipeline.py          # 評価パイプライン
│   │   └── golden/
│   │       ├── __init__.py
│   │       └── questions.json       # ゴールデンQ&Aデータセット (P1)
│   └── pyproject.toml
├── docker-compose.yml               # Docker 構成 (P2)
└── frontend/
    ├── src/
    │   ├── App.tsx                  # ルートコンポーネント
    │   ├── i18n/
    │   │   ├── index.ts             # i18n 設定 (P3)
    │   │   └── locales/
    │   │       ├── ja.json          # 日本語翻訳 (P3)
    │   │       └── en.json          # 英語翻訳 (P3)
    │   ├── components/
    │   │   ├── LanguageSwitcher.tsx # 言語切替コンポーネント (P3)
    │   │   ├── chat/
    │   │   │   ├── ChatWindow.tsx   # チャットメイン UI
    │   │   │   ├── MessageList.tsx  # メッセージ一覧
    │   │   │   ├── MessageBubble.tsx # 吹き出し
    │   │   │   ├── ChatInput.tsx    # テキスト入力 (textarea)
    │   │   │   ├── TypingIndicator.tsx # タイピングアニメーション
    │   │   │   ├── MarkdownRenderer.tsx # Markdownレンダリング (P1)
    │   │   │   ├── SuggestChips.tsx # サジェストチップ (P1)
    │   │   │   ├── ToolProgress.tsx # ツール実行可視化 (P1)
    │   │   │   ├── MessageFeedback.tsx # フィードバックボタン (P1)
    │   │   │   ├── ErrorRecovery.tsx # エラーリカバリ (P1)
    │   │   │   ├── CopyButton.tsx       # コピーボタン (P2)
    │   │   │   ├── ScrollToBottomButton.tsx # スクロールボタン (P2)
    │   │   │   ├── WaitNotification.tsx # 長時間待機通知 (P2)
    │   │   │   ├── SourceCitations.tsx  # 根拠可視化 (P2)
    │   │   │   └── FAQSuggestions.tsx   # プロアクティブ FAQ (P2)
    │   │   ├── hitl/
    │   │   │   ├── HITLWidget.tsx   # HITL コンテナ
    │   │   │   ├── ClarificationButtons.tsx # ボタン選択UI
    │   │   │   └── ClarificationInput.tsx   # テキスト入力UI
    │   │   ├── ui/
    │   │   │   └── textarea.tsx     # shadcn/ui Textarea (P1)
    │   │   └── ErrorBoundary.tsx    # エラーバウンダリ
    │   ├── hooks/
    │   │   ├── useChat.ts           # チャット状態管理フック
    │   │   ├── useAutoScroll.ts     # 自動スクロールフック
    │   │   ├── useWaitTimer.ts      # 待機タイマーフック (P2)
    │   │   └── useLanguage.ts       # 言語管理フック (P3)
    │   ├── lib/
    │   │   ├── api.ts               # REST API クライアント
    │   │   ├── sse.ts               # SSE 接続管理 (自動リトライ付き)
    │   │   └── tool-labels.ts       # ツール名日本語ラベル (P1)
    │   └── types/
    │       ├── message.ts           # Message / ChatEvent / ChatStatus 型
    │       └── api.ts               # ApiResponse / ChatStartData 型
    ├── package.json
    └── vite.config.ts
```

---

## 3. バックエンド仕様

### 3.1 API エンドポイント

#### エンドポイント一覧

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | `/api/health` | 不要 | ヘルスチェック |
| POST | `/api/chat` | JWT 必須 | チャット開始・メッセージ送信 |
| GET | `/api/chat/stream/{thread_id}` | JWT 必須 | SSE ストリーム接続 |
| POST | `/api/chat/resume/{thread_id}` | JWT 必須 | HITL 中断からの再開 |
| POST | `/api/feedback` | JWT 必須 | フィードバック送信 (P1) |
| GET | `/api/admin/knowledge` | JWT 必須 | ドキュメント一覧取得 (P1) |
| POST | `/api/admin/knowledge` | JWT 必須 | ドキュメント追加 (P1) |
| GET | `/api/admin/knowledge/{doc_id}` | JWT 必須 | 個別ドキュメント取得 (P1) |
| DELETE | `/api/admin/knowledge/{doc_id}` | JWT 必須 | ドキュメント削除 (P1) |
| GET | `/api/admin/knowledge-gaps` | JWT 必須 | ナレッジギャップ一覧 (P1) |
| GET | `/api/health/detailed` | 不要 | 詳細ヘルスチェック (P2) |
| GET | `/api/faq/suggestions` | JWT 必須 | ページ URL に基づく FAQ 推薦 (P2) |
| GET | `/api/faq/top` | JWT 必須 | トップ質問取得 (P2) |
| GET | `/api/faq/search` | JWT 必須 | FAQ キーワード検索 (P2) |
| GET | `/api/faq/categories` | JWT 必須 | FAQ カテゴリ一覧 (P2) |
| POST | `/api/faq/click` | JWT 必須 | FAQ 閲覧数記録 (P2) |
| GET | `/api/admin/escalations` | JWT 必須 | エスカレーションチケット一覧 (P2) |
| GET | `/api/admin/escalations/{ticket_id}` | JWT 必須 | チケット詳細取得 (P2) |
| GET | `/api/admin/costs` | JWT 必須 | コスト情報取得 (P2) |
| GET | `/api/admin/costs/check-limit` | JWT 必須 | コスト上限チェック (P2) |
| GET | `/api/admin/prompts` | JWT 必須 | 全プロンプト一覧 (P2) |
| GET | `/api/admin/prompts/{prompt_id}` | JWT 必須 | プロンプト詳細 (P2) |
| PUT | `/api/admin/prompts/{prompt_id}` | JWT 必須 | プロンプト更新 (P2) |
| POST | `/api/admin/prompts/{prompt_id}/rollback/{version}` | JWT 必須 | プロンプトロールバック (P2) |
| GET | `/api/admin/prompts/{prompt_id}/history` | JWT 必須 | プロンプト変更履歴 (P2) |
| POST | `/api/tenants` | JWT 必須 | テナント作成 (P3) |
| GET | `/api/tenants` | JWT 必須 | テナント一覧取得 (P3) |
| GET | `/api/tenants/{tenant_id}` | JWT 必須 | テナント詳細取得 (P3) |
| PUT | `/api/tenants/{tenant_id}/config` | JWT 必須 | テナント設定更新 (P3) |
| DELETE | `/api/tenants/{tenant_id}` | JWT 必須 | テナント無効化 (P3) |
| GET | `/api/users/me` | JWT 必須 | 現在のユーザー情報取得 (P3) |
| GET | `/api/users/me/history` | JWT 必須 | 会話履歴取得 (P3) |
| PATCH | `/api/users/me/plan` | JWT 必須 | ユーザープラン更新（管理者のみ）(P3) |
| GET | `/api/users/me/recommendations` | JWT 必須 | パーソナライズ推薦取得 (P3) |
| POST | `/api/gdpr/policies` | JWT 必須 | データ保持ポリシー作成 (P3) |
| GET | `/api/gdpr/policies` | JWT 必須 | 保持ポリシー一覧取得 (P3) |
| GET | `/api/gdpr/policies/{tenant_id}/{data_type}` | JWT 必須 | 保持ポリシー取得 (P3) |
| POST | `/api/gdpr/delete-user-data` | JWT 必須 | ユーザーデータ削除（GDPR Article 17）(P3) |
| GET | `/api/gdpr/audit-logs` | JWT 必須 | 監査ログ取得 (P3) |
| POST | `/api/gdpr/cleanup` | JWT 必須 | 期限切れデータクリーンアップ (P3) |
| POST | `/api/integrations/register` | JWT 必須 | CRMアダプター登録 (P3) |
| GET | `/api/integrations` | JWT 必須 | 登録済み連携一覧取得 (P3) |
| DELETE | `/api/integrations/{tenant_id}` | JWT 必須 | CRMアダプター登録解除 (P3) |
| POST | `/api/integrations/tickets` | JWT 必須 | CRMチケット作成 (P3) |
| GET | `/api/integrations/tickets/{tenant_id}/{ticket_id}` | JWT 必須 | CRMチケット取得 (P3) |
| POST | `/api/chat/image` | JWT 必須 | 画像アップロード (P3) |
| POST | `/api/experiments` | JWT 必須 | 実験作成 (P3) |
| GET | `/api/experiments` | JWT 必須 | 実験一覧取得 (P3) |
| GET | `/api/experiments/{experiment_id}` | JWT 必須 | 実験詳細取得 (P3) |
| PUT | `/api/experiments/{experiment_id}/status` | JWT 必須 | 実験ステータス更新 (P3) |
| POST | `/api/experiments/{experiment_id}/assign` | JWT 必須 | バリアント割り当て (P3) |
| POST | `/api/experiments/{experiment_id}/metrics` | JWT 必須 | メトリクス記録 (P3) |
| GET | `/api/experiments/{experiment_id}/results` | JWT 必須 | 実験結果取得 (P3) |
| POST | `/api/v1/guardrails/check-input` | 不要 | 入力安全性チェック (P3) |
| POST | `/api/v1/guardrails/check-output` | 不要 | 出力安全性チェック (P3) |
| POST | `/api/v1/guardrails/red-team` | 不要 | レッドチーミングテスト実行 (P3) |
| POST | `/api/channels/{tenant_id}/slack/webhook` | 不要 | Slack Webhook 受信 (P3) |
| POST | `/api/channels/{tenant_id}/line/webhook` | 不要 | LINE Webhook 受信 (P3) |
| POST | `/api/channels/{tenant_id}/email/webhook` | 不要 | Email Webhook 受信 (P3) |
| POST | `/api/channels/register` | JWT 必須 | チャネルアダプター登録 (P3) |
| GET | `/api/channels/list` | JWT 必須 | 登録チャネル一覧取得 (P3) |

> **認証:** `/api/health`・ガードレール・チャネル Webhook を除く全エンドポイントに JWT Bearer トークンが必要。`Authorization: Bearer <token>` ヘッダーで送信する。
> **レート制限:** チャット系エンドポイントは `slowapi` によるレート制限あり（デフォルト: チャット `20/minute`、ストリーム `30/minute`）。

#### GET /api/health

ヘルスチェック用エンドポイント。

**レスポンス例:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

#### POST /api/chat

新規チャットを開始、または既存スレッドにメッセージを送信する。

**リクエスト:**
```json
{
  "message": "製品Aの初期設定方法を教えてください",
  "thread_id": null
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `message` | string | 必須 | ユーザーメッセージ（1〜2000文字） |
| `thread_id` | UUID \| null | 任意 | 既存スレッドID（UUID 形式）。null の場合は新規作成 |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "streaming"
  }
}
```

#### GET /api/chat/stream/{thread_id}

SSE（Server-Sent Events）ストリームを開始する。120秒間イベントがない場合は ping を送信し接続を維持する。

**レスポンスヘッダー:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**イベントフォーマット:**
```
data: {"type":"token","content":"製品A"}\n\n
data: {"type":"tool_start","tool_name":"search_knowledge"}\n\n
data: {"type":"done"}\n\n
```

#### POST /api/chat/resume/{thread_id}

HITL によって中断されたエージェントを再開する。

**リクエスト:**
```json
{
  "request_id": "req-uuid",
  "response": "操作方法"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `request_id` | string | 必須 | HITL リクエストID |
| `response` | string | 必須 | ユーザーの回答（1文字以上） |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "streaming"
  }
}
```

#### POST /api/feedback

アシスタントメッセージに対するフィードバックを送信する。

**リクエスト:**
```json
{
  "message_id": "msg-uuid",
  "rating": "positive",
  "comment": "参考になりました"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `message_id` | string | 必須 | メッセージID |
| `rating` | string | 必須 | 評価 (`positive` / `negative`) |
| `comment` | string \| null | 任意 | コメント（任意） |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "id": "feedback-uuid",
    "created_at": "2026-02-24T12:00:00Z"
  }
}
```

#### GET /api/admin/knowledge

ドキュメント一覧を取得する。

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `category` | string \| null | null | カテゴリフィルタ |
| `limit` | int | 100 | 取得件数 |
| `offset` | int | 0 | オフセット |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "id": "doc-uuid",
        "content": "...",
        "metadata": {"category": "操作方法", "source": "product_guide.md"},
        "created_at": "2026-02-24T12:00:00Z"
      }
    ],
    "total": 150
  }
}
```

#### POST /api/admin/knowledge

ドキュメントを追加する。追加時にBM25インデックスとベクトルストアの両方が更新される。

**リクエスト:**
```json
{
  "content": "新しいドキュメントの内容...",
  "metadata": {
    "category": "操作方法",
    "source": "custom"
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `content` | string | 必須 | ドキュメント内容 |
| `metadata` | object | 任意 | メタデータ（category, source 等） |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "id": "new-doc-uuid",
    "created_at": "2026-02-24T12:00:00Z"
  }
}
```

#### GET /api/admin/knowledge/{doc_id}

個別ドキュメントを取得する。

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "id": "doc-uuid",
    "content": "...",
    "metadata": {"category": "操作方法", "source": "product_guide.md"},
    "created_at": "2026-02-24T12:00:00Z"
  }
}
```

#### DELETE /api/admin/knowledge/{doc_id}

ドキュメントを削除する。削除時にBM25インデックスが再構築される。

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "deleted_id": "doc-uuid"
  }
}
```

#### GET /api/admin/knowledge-gaps

回答できなかった質問（ナレッジギャップ）の一覧を取得する。

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `limit` | int | 100 | 取得件数 |

**レスポンス:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "total": 45,
      "unique_queries": 32,
      "top_queries": [
        {"query": "XXXの使い方", "count": 5},
        {"query": "YYYが動かない", "count": 3}
      ]
    },
    "gaps": [
      {
        "id": "gap-uuid",
        "query": "XXXの使い方",
        "category": "操作方法",
        "created_at": "2026-02-24T12:00:00Z"
      }
    ]
  }
}
```

#### API フロー図

```mermaid
sequenceDiagram
    participant C as クライアント
    participant API as FastAPI
    participant SVC as ChatService
    participant AGT as Deep Agent

    C->>API: POST /api/chat {message, thread_id}
    API->>SVC: start_chat(message, thread_id)
    SVC->>SVC: asyncio.create_task(_run_agent)
    SVC-->>API: thread_id
    API-->>C: {success:true, data:{thread_id, status:"streaming"}}

    C->>API: GET /api/chat/stream/{thread_id}
    API->>SVC: get_or_create_queue(thread_id)
    API-->>C: text/event-stream (接続確立)

    loop エージェント実行中
        AGT->>SVC: queue.put(StreamEvent TOKEN)
        SVC-->>C: data: {type:"token", content:"..."}
    end

    AGT->>SVC: queue.put(StreamEvent TOOL_START)
    SVC-->>C: data: {type:"tool_start", tool_name:"..."}

    AGT->>SVC: queue.put(StreamEvent TOOL_END)
    SVC-->>C: data: {type:"tool_end", tool_name:"..."}

    AGT->>SVC: queue.put(StreamEvent MESSAGE_COMPLETE)
    SVC-->>C: data: {type:"message_complete", content:"完全な回答"}

    AGT->>SVC: queue.put(StreamEvent DONE)
    SVC-->>C: data: {type:"done"}
    Note over C,API: SSE 接続自動切断
```

---

### 3.2 データモデル

#### Pydantic モデル一覧

**ChatRequest** (`app/models/chat.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `message` | str | 必須 | ユーザーメッセージ (1〜2000文字) |
| `thread_id` | UUID \| None | None | 既存スレッドID（UUID 形式のみ受付。不正形式は 422 エラー） |

**ChatStartResponse** (`app/models/chat.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `thread_id` | str | 必須 | スレッドID |
| `status` | str | "streaming" | 現在のステータス |

**StreamEvent** (`app/models/messages.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `type` | StreamEventType | 必須 | イベントタイプ |
| `content` | str \| None | None | テキストコンテンツ |
| `request_id` | str \| None | None | HITL リクエストID |
| `question` | str \| None | None | HITL 質問文 |
| `options` | list[str] \| None | None | HITL 選択肢リスト |
| `input_type` | str \| None | None | HITL 入力タイプ ("buttons" \| "text") |
| `tool_name` | str \| None | None | ツール名 |
| `documents` | list[SourceDocument] \| None | None | ソースドキュメント（sourceイベント用）(P2) |
| `is_relevant` | bool \| None | None | 関連性（qualityイベント用）(P2) |
| `confidence` | float \| None | None | 信頼度（qualityイベント用）(P2) |
| `reasoning` | str \| None | None | 評価理由（qualityイベント用）(P2) |

**HITLRequest** (`app/models/hitl.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `request_id` | str | 必須 | リクエストID |
| `question` | str | 必須 | ユーザーへの質問 |
| `options` | list[str] \| None | None | 選択肢（ボタン表示用） |
| `input_type` | str | "buttons" | 入力タイプ: buttons \| text |

**HITLResponse** (`app/models/hitl.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `request_id` | str | 必須 | 対応するリクエストID |
| `response` | str | 必須 | ユーザーの回答（1文字以上） |

**ResumeRequest** (`app/models/hitl.py`)

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `request_id` | str | 必須 | HITL リクエストID |
| `response` | str | 必須 | ユーザーの回答（1文字以上） |

#### StreamEventType 列挙値

| 値 | 説明 |
|----|------|
| `token` | LLM からのトークン（ストリーミング中） |
| `tool_start` | ツール実行開始 |
| `tool_end` | ツール実行終了 |
| `hitl_request` | HITL による中断・ユーザーへの確認要求 |
| `message_complete` | 完全な回答テキストの確定 |
| `error` | エラー発生 |
| `done` | エージェント処理完了 |
| `source` | ソースドキュメント情報（根拠可視化用）(P2) |
| `quality` | 品質スコア情報（根拠可視化用）(P2) |

#### AgentState の状態フィールド

`AgentState` は LangGraph の `TypedDict` として定義される (`app/agents/state.py`)。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `messages` | Annotated[list[BaseMessage], add_messages] | 会話履歴（add_messages アノテーション付き） |
| `thread_id` | str | スレッドID |
| `query_category` | str | 分類されたクエリカテゴリ |
| `rewritten_query` | str | リライト後のクエリ |
| `search_results` | list[dict] | 検索結果リスト |
| `relevance_score` | float | 関連性スコア |
| `generated_answer` | str | 生成された回答 |
| `quality_check_passed` | bool | 品質チェック合否 |

---

### 3.3 Deep Agent

#### エージェントの構成

Deep Agent は `langgraph.prebuilt.create_react_agent` で構築された ReAct エージェントである。LLM モデルに `gpt-4o-mini`（temperature=0.1、streaming=True）を使用し、8 つのツールを持つ。状態は `PostgresSaver`（フォールバック: MemorySaver）チェックポインタによりスレッド単位で永続化される。

#### ReAct エージェントループ図

```mermaid
flowchart TD
    START([ユーザーメッセージ受信]) --> CLASSIFY

    CLASSIFY["classify_query<br/>クエリ分類"] -->|unclear / confidence &lt; 0.6| HITL_Q1["interrupt<br/>カテゴリ確認"]
    HITL_Q1 -->|ユーザー回答| CLASSIFY_RESUME[分類結果確定]

    CLASSIFY -->|out_of_scope| OOS[スコープ外メッセージ返却]
    CLASSIFY -->|分類成功| REWRITE

    CLASSIFY_RESUME --> REWRITE

    REWRITE["rewrite_query<br/>クエリ最適化"] --> SEARCH

    SEARCH["search_knowledge<br/>ナレッジ検索"] --> RELEVANCE

    RELEVANCE["check_relevance<br/>関連性評価"] -->|is_relevant=false| HITL_Q2["ask_human<br/>追加情報確認"]
    HITL_Q2 -->|ユーザー回答| SEARCH

    RELEVANCE -->|is_relevant=true| GENERATE

    GENERATE["generate_answer<br/>回答生成"] --> QUALITY

    QUALITY["check_quality<br/>品質チェック"] -->|passed=false| RETRY{再試行 or HITL}
    RETRY -->|検索条件変更| SEARCH
    RETRY -->|HITL| HITL_Q2

    QUALITY -->|passed=true| END([回答を返す])

    OOS --> END
```

#### システムプロンプトの要約

`PRODUCT_SUPPORT_SYSTEM_PROMPT`（`app/agents/prompts.py`）は以下の内容を定義する。

- **役割**: 製品サポート AI アシスタント
- **対応カテゴリ**: 操作方法 / 障害・トラブル / 契約・料金 / その他
- **ワークフロー**: classify_query → rewrite_query → search_knowledge → check_relevance → generate_answer / ask_human → check_quality
- **重要ルール**: ナレッジベースの検索結果に基づいた回答のみ行う。範囲外（天気・ニュース等）には対応しない
- **回答フォーマット**: 簡潔・番号付きリスト・「ご不明な点がございましたら、お気軽にお問い合わせください。」で締める

#### カテゴリ別プロンプトとFew-shot（P1）

`CATEGORY_PROMPTS`（`app/agents/prompts.py`）はカテゴリごとの専用プロンプトと模範回答例を定義する。

| カテゴリ | プロンプトの特徴 | Few-shot例 |
|----------|-----------------|-----------|
| **操作方法** | 手順をステップごとに明確に説明 | 「初期設定の方法を教えて」→ 番号付きリストで手順回答 |
| **障害・トラブル** | 原因切り分け→対処法の順で説明 | 「ログインできない」→ 原因候補→解決手順 |
| **契約・料金** | 料金表・プラン比較を明確に | 「プランの違いは？」→ 比較表形式で回答 |

**引用フォーマット指示:**
回答には以下の形式で参照元を明記する。
```
【参考: {source} > {section}】
```

#### ツール一覧

| ツール名 | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `classify_query` | `query: str` | `dict` (category, confidence, reason) | クエリをカテゴリに分類。unclear / confidence < 0.6 の場合は HITL で確認 |
| `rewrite_query` | `query: str`, `conversation_context: str = ""` | `str` | 検索最適化のためクエリをリライト（代名詞解決・曖昧表現の具体化） |
| `search_knowledge` | `query: str`, `category: str \| None = None`, `n_results: int = 5` | `list[dict]` | ハイブリッド検索（BM25 + Vector）で関連ドキュメントを返す |
| `check_relevance` | `query: str`, `search_results: list[dict]` | `dict` (is_relevant, score, relevant_doc_indices, reason) | 検索結果とクエリの関連性を LLM で評価（高スコア時はスキップ可能） |
| `generate_answer` | `query: str`, `relevant_documents: list[dict]`, `category: str = ""` | `str` | 関連ドキュメントに基づいて回答を生成（カテゴリ別プロンプト使用） |
| `check_quality` | `query: str`, `answer: str`, `source_documents: list[dict]` | `dict` (passed, hallucination_score, sufficiency_score, issues) | ハルシネーション（偽情報）と充足性を評価。両スコア 0.6 以上で合格 |
| `ask_human` | `question: str`, `options: list[str] \| None = None`, `input_type: str = "text"` | `str` | LangGraph `interrupt()` でエージェントを中断しユーザーに質問 |
| `escalate_to_human` | `reason: str`, `urgency: str`, `summary: str = ""` | `str` | 解決不能な問題を有人サポートにエスカレーション。チケット作成・会話サマリー自動生成 |

#### スタンドアロンツール（P3）

エージェントの `tools` リストには含まれず、API レベル・ミドルウェアレベルで直接使用されるツール。

| ツール名 | 用途 | 使用箇所 |
|----------|------|----------|
| `check_input_safety` | 入力のジェイルブレイク検出・PII検出 | ガードレール API / ミドルウェア (P3) |
| `check_output_safety` | 出力の安全性チェック | ガードレール API / ミドルウェア (P3) |
| `analyze_image` | Vision API による画像解析 | チャット API 画像エンドポイント (P3) |

#### ツール詳細仕様

**classify_query**
- LLM（temperature=0）でカテゴリを判定
- カテゴリ: 操作方法 / 障害・トラブル / 契約・料金 / その他 / out_of_scope / unclear
- `unclear` または confidence < 0.6 の場合: `interrupt()` でボタン形式の HITL を起動
- 戻り値: `{"category": str, "confidence": float, "reason": str}`

**rewrite_query**
- LLM（temperature=0）でクエリを最適化
- 規則: 代名詞の具体化・敬語除去・会話コンテキスト考慮
- リライト結果が 3 文字未満の場合は元のクエリをそのまま返す

**search_knowledge**
- `retrieve_documents()` を呼び出しハイブリッド検索（BM25 + Vector + RRF）を実行
- `category` 指定時はフィルタでカテゴリを絞り込む
- 結果が空の場合は「関連するドキュメントが見つかりませんでした。」を返す
- 各結果: `{content, metadata, relevance_score, id}` の形式

**check_relevance**
- LLM（temperature=0）で関連性を総合評価
- **高スコア時スキップ**: 検索結果の平均スコアが `relevance_skip_threshold`（0.85）以上の場合、LLM呼び出しをスキップして `is_relevant=true` を返す（コスト削減）
- LLM パース失敗時: 検索スコアの平均値でフォールバック
- **ナレッジギャップ記録**: `is_relevant=false` の場合、`KnowledgeGapService` にクエリを記録
- 戻り値: `{"is_relevant": bool, "score": float, "relevant_doc_indices": list, "reason": str}`

**generate_answer**
- LLM（temperature=0.3）で回答生成
- **カテゴリ別プロンプト**: `CATEGORY_PROMPTS[category]` でカテゴリ固有の指示とFew-shot例を使用
- 参考情報に基づかない内容は「確認が必要です」と案内するよう指示
- **引用フォーマット**: 回答に `【参考: {source} > {section}】` 形式で参照元を明記

**check_quality**
- LLM（temperature=0）で 2 軸評価
  - `hallucination_score`: ソースドキュメントへの根拠度（1.0 が最良）
  - `sufficiency_score`: 質問への回答充足度（1.0 が最良）
- 両スコアが 0.6 以上で `passed = True`
- パース失敗時: 安全方向のデフォルト値（0.0/0.0）で `passed = False` を返し、issues に「品質チェックのレスポンスが解析できませんでした」を含める

**ask_human**
- `options` 指定時は `input_type = "buttons"`（強制）
- `options` なし時は `input_type = "text"`（強制）
- `langgraph.types.interrupt()` でエージェントを中断し、`ChatService._handle_interrupt()` で SSE へ `HITL_REQUEST` イベントを送出

**escalate_to_human** (P2)
- `EscalationInput` スキーマ: reason（理由）, urgency（"low"/"medium"/"high"）, summary（空の場合は自動生成）
- `EscalationService.create_ticket()` でチケットを作成
- チケットID: `ESC-{uuid8}` 形式
- 戻り値: 「エスカレーションを受け付けました。チケットID: ESC-XXXXXXXX 担当者より折り返しご連絡いたします。」
- エスカレーション判断基準: 明示的有人対応希望、技術的解決不可能、法的金銭的重要事項、3回以上同一質問

---

### 3.4 RAG パイプライン

#### RAG 処理フロー図

```mermaid
flowchart LR
    subgraph Startup["アプリ起動時"]
        MD[("*.md ファイル<br/>sample_docs/")]
        LOAD["load_all_documents<br/>MarkdownLoader"]
        SPLIT["MarkdownHeaderTextSplitter<br/>#, ##, ### で分割"]
        CHUNK["RecursiveCharacterTextSplitter<br/>chunk_size=800, overlap=100"]
        PREFIX["ヘッダー階層プレフィックス付与<br/>_build_header_prefix()"]
        META["メタデータ付与<br/>category / source"]
        EMBED["ChromaDB<br/>multilingual-e5-base"]
        STORE[("ChromaDB<br/>PersistentClient")]
        BM25[("BM25Store<br/>fugashiトークナイザー")]
    end

    subgraph Query["クエリ時"]
        Q[検索クエリ]
        FILTER{"category<br/>フィルタ?"}
        HYBRID["ハイブリッド検索<br/>BM25 + Vector"]
        RRF["Reciprocal Rank Fusion<br/>K=60, alpha=0.7"]
        RESULT["検索結果整形<br/>content / metadata /<br/>relevance_score / id"]
    end

    MD --> LOAD --> SPLIT --> CHUNK --> PREFIX --> META --> EMBED --> STORE
    META --> BM25
    Q --> FILTER
    FILTER -->|あり| HYBRID
    FILTER -->|なし| HYBRID
    STORE --> HYBRID
    BM25 --> HYBRID
    HYBRID --> RRF --> RESULT
```

#### VectorStore の仕様

`VectorStore` クラス (`app/rag/vector_store.py`) は ChromaDB の `PersistentClient` をラップするシングルトンである。

| 項目 | 値 |
|------|-----|
| クライアント | `chromadb.PersistentClient` |
| 永続化ディレクトリ | `./data/chroma_db`（Settings で変更可能） |
| コレクション名 | `product_support_v2`（Settings で変更可能） |
| 距離メトリクス | cosine (`hnsw:space: cosine`) |
| 埋め込みモデル | `intfloat/multilingual-e5-base`（SentenceTransformerEmbeddingFunction） |

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `get_instance()` | なし | VectorStore | シングルトン取得 |
| `reset_instance()` | なし | None | インスタンスをリセット（テスト用） |
| `add_documents()` | documents, metadatas, ids | None | ドキュメントを追加 |
| `query()` | query_text, n_results, where | dict | 類似検索 |
| `count` (property) | なし | int | 格納済みドキュメント数 |

#### BM25Store の仕様

`BM25Store` クラス (`app/rag/bm25_store.py`) は BM25 キーワード検索を提供するシングルトンである。

| 項目 | 値 |
|------|-----|
| アルゴリズム | `rank_bm25.BM25Okapi` |
| トークナイザー | `fugashi`（日本語形態素解析） |
| top_k | 10（Settings で変更可能） |

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `get_instance()` | なし | BM25Store | シングルトン取得 |
| `reset_instance()` | なし | None | インスタンスをリセット（テスト用） |
| `index_documents()` | documents | None | ドキュメントをインデックス |
| `search()` | query, n_results | list[dict] | BM25検索 |

#### ハイブリッド検索（BM25 + Vector + RRF）

`retrieve_documents()` (`app/rag/retriever.py`) は BM25 キーワード検索とベクトル類似検索を組み合わせたハイブリッド検索を実行する。

**Reciprocal Rank Fusion (RRF) アルゴリズム:**

```
RRF_score(d) = alpha * (1 / (K + rank_vector(d))) + (1 - alpha) * (1 / (K + rank_bm25(d)))
```

- K = 60（RRF 定数）
- alpha = 0.7（ベクトル検索の重み、Settings で変更可能）
- alpha = 1.0 でベクトル検索のみモードに切り替え可能

**検索パラメータ:**

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `hybrid_search_alpha` | 0.7 | ベクトル:BM25 の重み付け（0.0〜1.0） |
| `bm25_top_k` | 10 | BM25検索の取得件数 |

#### ドキュメントローダーの処理フロー

`load_all_documents()` (`app/rag/document_loader.py`) はアプリ起動時に `lifespan` イベントで呼び出される。

1. `data/sample_docs/*.md` を glob で列挙
2. 各ファイルを `load_markdown_file()` で処理
3. `MarkdownHeaderTextSplitter` でヘッダー（`#`, `##`, `###`）単位に分割
4. `RecursiveCharacterTextSplitter` でさらに細かく分割
5. **ヘッダー階層情報をプレフィックスとして付与**（`_build_header_prefix()`）
6. メタデータを付与: `source`（ファイル名）、`category`（ファイル名から推定）
7. ドキュメント ID は `md5(source:content[:100])` で生成
8. `VectorStore.add_documents()` で一括格納
9. アプリ起動時にベクトルストアが空（`count == 0`）の場合のみロードする

#### チャンク分割パラメータ

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `chunk_size` | 800 | チャンクの最大文字数 |
| `chunk_overlap` | 100 | チャンク間のオーバーラップ文字数（約12.5%） |
| `separators` | `["\n\n", "\n", "。", "、", " "]` | 優先分割文字（順位あり） |

#### ヘッダー階層プレフィックス

チャンクの冒頭にヘッダー階層情報を付与することで、コンテキストを保持する。

**例:**
```
【操作方法 > 初期設定 > ステップ1】
1. 電源ボタンを長押しします...
```

#### カテゴリ推定マッピング

| ファイル名（stem） | カテゴリ |
|-------------------|---------|
| `product_guide` | 操作方法 |
| `troubleshooting` | 障害・トラブル |
| `contracts` | 契約・料金 |
| その他 | その他 |

**検索結果の整形:**

`retrieve_documents()` (`app/rag/retriever.py`) はハイブリッド検索の結果を以下の形式に整形する。

```python
{
    "content": str,           # ドキュメントテキスト
    "metadata": dict,         # ChromaDB メタデータ（category, source 等）
    "relevance_score": float, # RRF スコア（0〜1正規化）
    "id": str,                # ドキュメントID
}
```

#### Cross-Encoder リランキング (P2)

`CrossEncoderReranker` クラス (`app/rag/retriever.py`) はハイブリッド検索結果に対して Cross-Encoder によるリランキングを実行する。

| 項目 | 値 |
|------|-----|
| モデル | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| パターン | シングルトン（遅延ロード） |
| 入力 | query + documents (list[dict]) |
| 出力 | リランキング済みドキュメント（rerank_score 追加） |
| 設定 | `reranker_enabled`, `reranker_model`, `reranker_top_k` |

#### 検索戦略 (P2)

`retrieve_with_strategy()` (`app/rag/rewrite.py`) は設定に基づいて検索戦略を選択する。

| 戦略 | 設定値 | 説明 |
|------|--------|------|
| 標準 | `"standard"` | 通常のハイブリッド検索 |
| Multi-Query | `"multi_query"` | 3つのクエリバリエーションで並列検索、RRF で統合 |
| HyDE | `"hyde"` | 仮説的回答文書を生成して検索精度を向上 |
| ハイブリッド | `"hybrid"` | Multi-Query + HyDE の組み合わせ |

---

### 3.5 HITL (Human-in-the-Loop)

#### HITL フロー図

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant FE as フロントエンド
    participant API as FastAPI
    participant SVC as ChatService
    participant AGT as Deep Agent

    AGT->>AGT: interrupt({question, options, input_type})
    Note over AGT: LangGraph GraphInterrupt 例外発生
    AGT-->>SVC: GraphInterrupt
    SVC->>SVC: _handle_interrupt(thread_id, queue, config)
    SVC->>SVC: agent.get_state(config) で interrupt データを取得
    SVC->>SVC: queue.put(StreamEvent HITL_REQUEST)
    SVC->>SVC: queue.put(StreamEvent DONE)

    SVC-->>FE: SSE: {type:"hitl_request", request_id, question, options, input_type}
    SVC-->>FE: SSE: {type:"done"}
    FE->>FE: SSE 接続切断
    FE->>FE: status = "hitl_pending"
    FE->>FE: HITLWidget 表示

    U->>FE: ボタン選択 or テキスト入力
    FE->>API: POST /api/chat/resume/{thread_id} {request_id, response}
    API->>SVC: resume_chat(thread_id, response)
    SVC->>SVC: asyncio.create_task(_resume_agent)

    FE->>API: GET /api/chat/stream/{thread_id}
    API-->>FE: SSE 再接続

    SVC->>AGT: agent.astream_events(Command(resume=response), config)
    Note over AGT: エージェント再開
    AGT->>SVC: queue.put(StreamEvent TOKEN/TOOL_START/...)
    SVC-->>FE: SSE イベント配信（再開後の処理）
```

#### interrupt/resume メカニズムの説明

1. **interrupt 発生**: `ask_human` ツールまたは `classify_query` ツール内で `langgraph.types.interrupt(data: dict)` が呼び出される
2. **GraphInterrupt 例外**: LangGraph は `GraphInterrupt` 例外を発生させエージェント実行を中断する
3. **状態保存**: `MemorySaver` チェックポインタがその時点のエージェント状態を保存する
4. **interrupt データ取得**: `ChatService._handle_interrupt()` が `agent.get_state(config).tasks` を走査し `interrupt.value` から質問・選択肢を取得する
5. **SSE 通知**: `HITL_REQUEST` イベントをキューに入れ、フロントエンドに通知する
6. **resume**: フロントエンドから `POST /api/chat/resume` が届くと、`Command(resume=response)` を用いてエージェントを再開する

#### HITLリクエスト/レスポンスのデータフロー

| フェーズ | データ | 方向 |
|---------|--------|------|
| interrupt 発生時のデータ | `{question: str, options: list \| None, input_type: str}` | Agent → ChatService |
| SSE イベント | `StreamEvent(type=HITL_REQUEST, request_id, question, options, input_type)` | ChatService → Frontend |
| ユーザー回答（resume） | `ResumeRequest(request_id, response)` | Frontend → API |
| エージェント再開コマンド | `Command(resume=response_str)` | ChatService → Agent |

---

## 4. フロントエンド仕様

### 4.1 コンポーネント構成

#### コンポーネントツリー図

```mermaid
graph TD
    APP[App.tsx] --> EB[ErrorBoundary]
    EB --> CW[ChatWindow]
    CW --> ML[MessageList]
    CW --> CI[ChatInput]
    CW --> HW[HITLWidget]
    CW --> WN[WaitNotification]
    CW --> FS[FAQSuggestions]
    CW --> SB[ScrollToBottomButton]
    ML --> MB[MessageBubble]
    ML --> TI[TypingIndicator]
    MB --> CPB[CopyButton]
    MB --> SC[SourceCitations]
    HW --> CB[ClarificationButtons]
    HW --> CIN[ClarificationInput]
    CW -->|useChat hook| UC{useChat}
    UC -->|useAutoScroll| UAS{useAutoScroll}
    UC -->|useWaitTimer| UWT{useWaitTimer}
    UC -->|api.ts| API[sendMessage / resumeChat]
    UC -->|sse.ts| SSE[createSSEConnection]
```

#### 各コンポーネントの Props 一覧

**App.tsx** - Props なし

**ErrorBoundary**

| Prop | 型 | 説明 |
|------|-----|------|
| `children` | ReactNode | 子コンポーネント |

**ChatWindow** - Props なし（`useChat` フックで状態取得）

**MessageList**

| Prop | 型 | 説明 |
|------|-----|------|
| `messages` | `readonly Message[]` | メッセージ一覧 |
| `streamingContent` | string | ストリーミング中の部分テキスト |
| `isStreaming` | boolean | ストリーミング中フラグ |

**MessageBubble**

| Prop | 型 | 説明 |
|------|-----|------|
| `message` | `Message` | 表示するメッセージ |

**ChatInput**

| Prop | 型 | 説明 |
|------|-----|------|
| `onSend` | `(message: string) => void` | 送信コールバック |
| `disabled` | boolean | 入力無効フラグ |

**TypingIndicator** - Props なし

**HITLWidget**

| Prop | 型 | 説明 |
|------|-----|------|
| `request` | `HITLRequest` | HITL リクエスト情報 |
| `onRespond` | `(response: string) => void` | 回答コールバック |
| `disabled` | boolean | 操作無効フラグ |

**ClarificationButtons**

| Prop | 型 | 説明 |
|------|-----|------|
| `options` | `readonly string[]` | 選択肢リスト |
| `onSelect` | `(option: string) => void` | 選択コールバック |
| `disabled` | boolean | ボタン無効フラグ |

**ClarificationInput**

| Prop | 型 | 説明 |
|------|-----|------|
| `onSubmit` | `(text: string) => void` | 送信コールバック |
| `disabled` | boolean | 入力無効フラグ |
| `placeholder` | string? | プレースホルダーテキスト |

**CopyButton** (P2)

| Prop | 型 | 説明 |
|------|-----|------|
| `text` | string | コピー対象テキスト |

**ScrollToBottomButton** (P2)

| Prop | 型 | 説明 |
|------|-----|------|
| `isVisible` | boolean | 表示フラグ |
| `onClick` | `() => void` | クリックコールバック |

**WaitNotification** (P2)

| Prop | 型 | 説明 |
|------|-----|------|
| `showWarning` | boolean | 30秒超過警告表示 |
| `showError` | boolean | 60秒超過エラー表示 |
| `onCancel` | `() => void` | キャンセルコールバック |

**SourceCitations** (P2)

| Prop | 型 | 説明 |
|------|-----|------|
| `sources` | `readonly SourceDocument[]` | ソースドキュメント一覧 |
| `qualityScore` | `QualityScore?` | 品質スコア |

**FAQSuggestions** (P2)

| Prop | 型 | 説明 |
|------|-----|------|
| `onPageSelect` | `((question: string) => void)?` | FAQ 選択コールバック |

---

### 4.2 状態管理

#### useChat フック

`useChat` フック (`src/hooks/useChat.ts`) がチャット機能の全状態を管理する。

**返却値インターフェース:**

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| `messages` | `readonly Message[]` | 会話履歴（確定済みメッセージ） |
| `status` | `ChatStatus` | 現在の状態 |
| `streamingContent` | string | ストリーミング中の未確定テキスト |
| `currentHITL` | `HITLRequest \| null` | 現在の HITL リクエスト |
| `activeTool` | `string \| null` | 実行中ツール名 |
| `error` | `string \| null` | エラーメッセージ |
| `send` | `(message: string) => Promise<void>` | メッセージ送信関数 |
| `respondToHITL` | `(response: string) => Promise<void>` | HITL 回答関数 |
| `cancelRequest` | `() => void` | リクエストキャンセル関数（SSE切断+状態リセット）(P2) |
| `sources` | `readonly SourceDocument[]` | ソースドキュメント (P2) |
| `qualityScore` | `QualityScore \| null` | 品質スコア (P2) |

#### useChat 状態遷移図

```mermaid
stateDiagram-v2
    [*] --> idle: 初期状態

    idle --> streaming: send() 呼び出し
    streaming --> idle: done イベント受信
    streaming --> hitl_pending: hitl_request イベント受信
    streaming --> error: error イベント受信

    hitl_pending --> streaming: respondToHITL() 呼び出し（resume 後 SSE 再接続）
    hitl_pending --> error: resume API エラー

    error --> idle: 手動リセット（再試行）
    error --> streaming: send() 再呼び出し

    idle --> [*]
```

**各状態の説明:**

| 状態 | 説明 | UI の挙動 |
|------|------|----------|
| `idle` | 待機中 | チャット入力が有効 |
| `streaming` | エージェント処理中 | チャット入力が無効、TypingIndicator または streamingContent を表示 |
| `hitl_pending` | HITL 確認待ち | HITLWidget を表示、チャット入力が無効 |
| `error` | エラー発生 | エラーメッセージを表示 |

#### 内部 Ref の役割

| Ref | 型 | 目的 |
|-----|----|------|
| `threadIdRef` | `string \| null` | スレッド ID の保持（再レンダリングを避けるため） |
| `eventSourceRef` | `EventSource \| null` | SSE 接続インスタンスの保持 |
| `streamingContentRef` | `string` | ストリーミングテキスト（イベントハンドラ内での累積用） |
| `statusRef` | `ChatStatus` | 非同期コールバック内でのステータス参照用 |

---

### 4.3 SSE 通信

#### SSE イベントフロー図

```mermaid
sequenceDiagram
    participant UC as useChat
    participant SSE as sse.ts
    participant ES as EventSource
    participant BE as Backend SSE

    UC->>SSE: createSSEConnection(threadId, handleEvent, onError)
    SSE->>ES: new EventSource("/api/chat/stream/{threadId}")
    ES->>BE: HTTP GET (接続確立)
    BE-->>ES: text/event-stream

    loop トークン配信
        BE-->>ES: data: {type:"token", content:"..."}
        ES->>SSE: onmessage
        SSE->>UC: handleEvent({type:"token"})
        UC->>UC: streamingContent += content
    end

    BE-->>ES: data: {type:"tool_start", tool_name:"search_knowledge"}
    ES->>SSE: onmessage
    SSE->>UC: handleEvent({type:"tool_start"})
    UC->>UC: activeTool = "search_knowledge"

    BE-->>ES: data: {type:"tool_end", tool_name:"search_knowledge"}
    SSE->>UC: handleEvent({type:"tool_end"})
    UC->>UC: activeTool = null

    BE-->>ES: data: {type:"message_complete", content:"全文"}
    SSE->>UC: handleEvent({type:"message_complete"})
    UC->>UC: messages に追加, streamingContent = ""

    BE-->>ES: data: {type:"done"}
    SSE->>SSE: eventSource.close()
    SSE->>UC: handleEvent({type:"done"})
    UC->>UC: status = "idle"

    opt 120秒タイムアウト
        BE-->>ES: data: {"type":"ping"}
        SSE->>SSE: JSON.parse エラー or type=ping → 無視
    end

    opt エラー発生
        BE-->>ES: data: {type:"error", content:"..."}
        SSE->>SSE: eventSource.close()
        SSE->>UC: handleEvent({type:"error"})
        UC->>UC: status = "error"
    end
```

#### EventSource ライフサイクル

| イベント | 処理 |
|---------|------|
| `onmessage` | JSON パースして `handleEvent()` を呼び出す。`done` または `error` を受信したら `eventSource.close()` |
| `onerror` | `onError` コールバックを呼び出して `eventSource.close()` |
| ping 受信 | `type: "ping"` は `useChat` で無視する |
| HITL_REQUEST 受信 | `closeSSEConnection()` で明示的に接続を切断し、`status = "hitl_pending"` に遷移 |

**`closeSSEConnection()`:** `EventSource.readyState !== CLOSED` の場合のみ `close()` を呼び出す（二重切断を防止）。

---

### 4.4 HITL UI

#### HITL UI のフロー

```mermaid
flowchart TD
    A[hitl_request イベント受信] --> B[SSE 接続切断]
    B --> C[currentHITL 状態を設定]
    C --> D[status = hitl_pending]
    D --> E{HITLWidget 表示}

    E --> F{input_type?}
    F -->|buttons + options あり| G["ClarificationButtons<br/>ボタン選択 UI"]
    F -->|text| H["ClarificationInput<br/>テキスト入力 UI"]

    G --> I[ボタンクリック]
    H --> J[テキスト入力 → Enter or 送信ボタン]

    I --> K[respondToHITL 呼び出し]
    J --> K

    K --> L[ユーザー回答をメッセージ追加]
    K --> M[currentHITL = null]
    K --> N[POST /api/chat/resume]
    N --> O[SSE 再接続]
    O --> P[status = streaming]
```

#### コンポーネントの切り替えロジック

`HITLWidget` は `request.input_type === 'buttons' && request.options` の条件で表示コンポーネントを切り替える。

| 条件 | 表示コンポーネント | 説明 |
|------|-----------------|------|
| `input_type === 'buttons'` かつ `options` が存在 | `ClarificationButtons` | 選択肢をボタンで表示（例: カテゴリ選択） |
| それ以外（`input_type === 'text'` または `options` なし） | `ClarificationInput` | フリーテキスト入力（例: 追加情報の入力） |

HITL カードはアンバー（amber）系のスタイルで装飾され「確認」バッジが表示される。

---

## 5. データフロー

### 正常系フロー

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant FE as フロントエンド
    participant API as FastAPI
    participant SVC as ChatService
    participant AGT as Deep Agent
    participant LLM as OpenAI API
    participant DB as ChromaDB

    U->>FE: メッセージ入力・送信
    FE->>FE: ユーザーメッセージを messages に追加
    FE->>API: POST /api/chat {message, thread_id}
    API->>SVC: start_chat(message, thread_id)
    SVC->>SVC: asyncio.create_task(_run_agent)
    SVC-->>API: thread_id
    API-->>FE: {thread_id, status:"streaming"}
    FE->>API: GET /api/chat/stream/{thread_id}
    API-->>FE: SSE 接続確立

    AGT->>LLM: classify_query
    LLM-->>AGT: カテゴリ判定結果
    SVC-->>FE: SSE: tool_start(classify_query)
    SVC-->>FE: SSE: tool_end(classify_query)

    AGT->>LLM: rewrite_query
    LLM-->>AGT: 最適化クエリ
    SVC-->>FE: SSE: tool_start(rewrite_query)
    SVC-->>FE: SSE: tool_end(rewrite_query)

    AGT->>DB: search_knowledge
    DB-->>AGT: 関連ドキュメント
    SVC-->>FE: SSE: tool_start(search_knowledge)
    SVC-->>FE: SSE: tool_end(search_knowledge)

    AGT->>LLM: check_relevance
    LLM-->>AGT: 関連性評価
    AGT->>LLM: generate_answer
    LLM-->>AGT: 回答テキスト
    AGT->>LLM: check_quality
    LLM-->>AGT: 品質チェック結果

    loop 回答トークン配信
        AGT->>SVC: queue.put(TOKEN)
        SVC-->>FE: SSE: token
        FE->>FE: streamingContent に追記
    end

    AGT->>SVC: queue.put(MESSAGE_COMPLETE)
    SVC-->>FE: SSE: message_complete
    FE->>FE: messages に assistant メッセージ追加
    FE->>FE: streamingContent = ""

    AGT->>SVC: queue.put(DONE)
    SVC-->>FE: SSE: done
    FE->>FE: status = "idle"
    U->>U: 回答を確認
```

### HITL フロー

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant FE as フロントエンド
    participant API as FastAPI
    participant SVC as ChatService
    participant AGT as Deep Agent

    Note over AGT: classify_query で unclear 判定
    AGT->>AGT: interrupt({question, options, input_type:"buttons"})
    Note over AGT: GraphInterrupt 例外→中断
    SVC->>SVC: _handle_interrupt で interrupt データを取得
    SVC->>SVC: queue.put(HITL_REQUEST)
    SVC->>SVC: queue.put(DONE)
    SVC-->>FE: SSE: hitl_request
    FE->>FE: SSE 切断, status = "hitl_pending"
    FE->>FE: HITLWidget 表示
    SVC-->>FE: SSE: done

    U->>FE: ボタン「操作方法」をクリック
    FE->>FE: respondToHITL("操作方法")
    FE->>API: POST /api/chat/resume/{thread_id} {request_id, response: 操作方法}
    API->>SVC: resume_chat(thread_id, "操作方法")
    SVC->>SVC: asyncio.create_task(_resume_agent)
    SVC-->>API: 202
    API-->>FE: {success:true, data:{thread_id, status:"streaming"}}

    FE->>API: GET /api/chat/stream/{thread_id}
    API-->>FE: SSE 再接続

    SVC->>AGT: astream_events(Command(resume="操作方法"))
    Note over AGT: エージェント再開・処理継続

    loop 残りの処理
        AGT->>SVC: queue.put(TOKEN/TOOL_START/...)
        SVC-->>FE: SSE イベント
    end

    SVC-->>FE: SSE: message_complete + done
    FE->>FE: status = "idle"
```

### エラーフロー

```mermaid
flowchart TD
    START([エラー発生]) --> WHERE{エラー発生箇所}

    WHERE -->|React レンダリング| EB[ErrorBoundary.getDerivedStateFromError]
    EB --> EBUI["エラーカード表示<br/>再試行ボタン"]
    EBUI -->|再試行ボタン| RESET["hasError: false<br/>再レンダリング"]

    WHERE -->|POST /api/chat APIエラー| FE_ERR["useChat: error 状態<br/>error メッセージ設定"]
    FE_ERR --> ESHOW[エラーバナー表示]

    WHERE -->|SSE 接続エラー| SSE_ERR{status?}
    SSE_ERR -->|hitl_pending 以外| CONN_ERR["error: 接続が切断されました<br/>status: error"]
    SSE_ERR -->|hitl_pending| IGNORE[無視（HITL 待ち中）]

    WHERE -->|エージェント実行エラー| AGT_ERR{例外種別}
    AGT_ERR -->|GraphInterrupt| HITL_FLOW["_handle_interrupt<br/>HITL_REQUEST 送出"]
    AGT_ERR -->|その他| ERR_EVT["StreamEvent ERROR<br/>queue.put"]
    ERR_EVT --> SSE_SEND[SSE: error イベント送信]
    SSE_SEND --> FE_ERR

    WHERE -->|品質チェック失敗| QF[check_quality: passed=false]
    QF --> RETRY{再試行 or HITL}
    RETRY -->|検索条件変更| RESEARCH[search_knowledge 再実行]
    RETRY -->|HITL| HITL_FLOW
```

---

## 6. 設定・環境変数

### 環境変数一覧

| 環境変数 | 型 | デフォルト | 説明 |
|---------|-----|-----------|------|
| `OPENAI_API_KEY` | SecretStr | `""` | OpenAI API キー（必須、SecretStr型でマスク） |
| `OPENAI_MODEL` | str | `"gpt-4o-mini"` | 使用する OpenAI モデル名 |
| `CORS_ORIGINS` | list[str] | `["http://localhost:5173", "http://localhost:3000"]` | CORS 許可オリジン一覧 |
| `CORS_ALLOWED_METHODS` | list[str] | `["GET", "POST", "OPTIONS"]` | CORS 許可メソッド一覧 (P1) |
| `CORS_ALLOWED_HEADERS` | list[str] | `["Authorization", "Content-Type"]` | CORS 許可ヘッダー一覧 (P1) |
| `CHROMA_PERSIST_DIR` | str | `"./data/chroma_db"` | ChromaDB 永続化ディレクトリパス |
| `CHROMA_COLLECTION_NAME` | str | `"product_support_v2"` | ChromaDB コレクション名 |
| `EMBEDDING_MODEL` | str | `"intfloat/multilingual-e5-base"` | 埋め込みモデル名 (P1) |
| `CHUNK_SIZE` | int | `800` | チャンクサイズ (P1) |
| `CHUNK_OVERLAP` | int | `100` | チャンクオーバーラップ (P1) |
| `HYBRID_SEARCH_ALPHA` | float | `0.7` | ハイブリッド検索の重み付け (P1) |
| `RELEVANCE_SKIP_THRESHOLD` | float | `0.85` | 高スコア時の関連性チェックスキップ閾値 (P1) |
| `JWT_SECRET_KEY` | str | `"dev-secret-key-change-in-production"` | JWT 署名用シークレットキー（本番では必ず変更） |
| `JWT_ALGORITHM` | str | `"HS256"` | JWT 署名アルゴリズム |
| `JWT_EXPIRE_MINUTES` | int | `60` | JWT トークンの有効期限（分） |
| `RATE_LIMIT_CHAT` | str | `"20/minute"` | チャットエンドポイントのレート制限 |
| `RATE_LIMIT_STREAM` | str | `"30/minute"` | ストリームエンドポイントのレート制限 |
| `DEBUG_MODE` | bool | `false` | デバッグモード（true の場合、エラーレスポンスにスタックトレースを含める） |
| `RETRIEVAL_STRATEGY` | str | `"standard"` | 検索戦略（"standard"\|"multi_query"\|"hyde"\|"hybrid"）(P2) |
| `MULTI_QUERY_COUNT` | int | `3` | Multi-Query 生成数 (P2) |
| `RERANKER_MODEL` | str | `"cross-encoder/ms-marco-MiniLM-L-6-v2"` | リランカーモデル名 (P2) |
| `RERANKER_ENABLED` | bool | `true` | リランカー有効化 (P2) |
| `RERANKER_TOP_K` | int | `5` | リランカー出力数 (P2) |
| `DATABASE_URL` | str | `"postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db"` | PostgreSQL 接続文字列 (P2) |
| `DATABASE_POOL_SIZE` | int | `5` | コネクションプールサイズ (P2) |
| `DATABASE_MAX_OVERFLOW` | int | `10` | オーバーフロー許容数 (P2) |

### Settings クラスのフィールド定義

`Settings` クラス (`app/config/settings.py`) は `pydantic_settings.BaseSettings` を継承する。

```python
class Settings(BaseSettings):
    app_version: str = "0.4.0"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allowed_methods: list[str] = ["GET", "POST", "OPTIONS"]
    cors_allowed_headers: list[str] = ["Authorization", "Content-Type"]
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "product_support_v2"
    embedding_model: str = "intfloat/multilingual-e5-base"
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    rate_limit_chat: str = "20/minute"
    rate_limit_stream: str = "30/minute"
    debug_mode: bool = False
    chunk_size: int = 800
    chunk_overlap: int = 100
    hybrid_search_alpha: float = 0.7
    bm25_top_k: int = 10
    relevance_skip_threshold: float = 0.85

    # P2 追加
    retrieval_strategy: str = "standard"
    multi_query_count: int = 3
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_enabled: bool = True
    reranker_top_k: int = 5
    database_url: str = "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

> **P3 注記:** P3 固有の環境変数は `settings.py` に追加されていない。各サービス（テナント、実験、ガードレール等）はデフォルト値をサービス内部で管理している。

- `.env` ファイルまたは環境変数から設定を読み込む
- `@lru_cache` 付きの `get_settings()` 関数でシングルトンとして提供される
- `openai_api_key` は `SecretStr` 型で、ログ出力時に `**********` にマスクされる

### Vite プロキシ設定

フロントエンド開発サーバー（`:5173`）は `/api` へのリクエストをバックエンド（`http://localhost:8000`）にプロキシする。

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

---

## 7. テスト戦略

### テストファイル一覧と対象

| ファイル | テスト対象 |
|---------|-----------|
| `tests/conftest.py` | pytest フィクスチャ定義（AsyncClient, JWT auth_headers） |
| `tests/test_models.py` | Pydantic モデル（ChatRequest, StreamEvent, HITLRequest 等） |
| `tests/test_api.py` | API エンドポイント（認証・レート制限・UUID バリデーション含む） |
| `tests/test_auth.py` | JWT 認証（トークン生成・検証・期限切れ・不正トークン） |
| `tests/test_tools.py` | 全 7 ツール（StructuredOutput + ChatPromptTemplate ベース） |
| `tests/test_llm_factory.py` | LLM ファクトリ（シングルトン・temperature 別インスタンス） |
| `tests/test_output_models.py` | StructuredOutput Pydantic モデルバリデーション |
| `tests/test_rag.py` | RAG パイプライン（VectorStore, DocumentLoader, Retriever） |
| `tests/test_integration.py` | エンドツーエンド統合テスト（認証付き） |
| `tests/test_bm25.py` | BM25検索（インデックス作成・検索・日本語トークナイズ） (P1) |
| `tests/test_cors.py` | CORS設定（許可メソッド・ヘッダー・オリジン） (P1) |
| `tests/test_feedback.py` | フィードバック機能（送信・永続化・バリデーション） (P1) |
| `tests/test_gap_service.py` | ナレッジギャップ検出（記録・集計・サマリー） (P1) |
| `tests/test_golden.py` | ゴールデンデータセット（parametrize品質評価） (P1) |
| `tests/test_knowledge.py` | ナレッジ管理API（CRUD・インデックス再構築） (P1) |
| `tests/test_prompts.py` | カテゴリ別プロンプト（Few-shot・引用フォーマット） (P1) |
| `tests/test_security_headers.py` | セキュリティヘッダー（X-Frame-Options等） (P1) |
| `tests/test_settings.py` | 設定値（SecretStrマスク・環境変数読み込み） (P1) |
| `tests/test_escalation_service.py` | エスカレーション機能（チケット作成・取得・サマリー生成）(P2) |
| `tests/test_faq_api.py` | FAQ API（推薦・検索・閲覧数記録）(P2) |
| `tests/test_prompt_service.py` | プロンプト管理（CRUD・バージョン管理・ロールバック）(P2) |
| `tests/test_settings.py` (更新) | 設定値（新規P2項目含む）(P2) |
| `tests/test_tools.py` (更新) | 全 8 ツール（StructuredOutput + ChatPromptTemplate ベース）(P2) |
| `tests/evaluation/pipeline.py` | RAGAS 評価パイプライン（4指標評価・レポート生成）(P2) |
| `tests/test_channels.py` | チャネルアダプター（LINE/Slack/Email Webhook 処理）(P3) |
| `tests/test_content_safety.py` | コンテンツ安全性（入力/出力チェック）(P3) |
| `tests/test_crm_integration.py` | CRM連携（Zendesk アダプター・チケット操作）(P3) |
| `tests/test_experiment_api.py` | 実験 API（CRUD・バリアント割り当て・メトリクス）(P3) |
| `tests/test_experiment_models.py` | 実験モデル（Pydantic バリデーション）(P3) |
| `tests/test_experiment_service.py` | 実験サービス（作成・ステータス管理）(P3) |
| `tests/test_guardrails.py` | ガードレール（ジェイルブレイク・PII 検出）(P3) |
| `tests/test_guardrails_api.py` | ガードレール API（入力/出力/レッドチーム）(P3) |
| `tests/test_guardrails_middleware.py` | ガードレールミドルウェア（リクエスト検査）(P3) |
| `tests/test_guardrails_models.py` | ガードレールモデル（Pydantic バリデーション）(P3) |
| `tests/test_guardrails_service.py` | ガードレールサービス（チェックロジック）(P3) |
| `tests/test_image_analysis.py` | 画像解析（Vision API モック）(P3) |
| `tests/test_image_api.py` | 画像 API（アップロードエンドポイント）(P3) |
| `tests/test_language_service.py` | 言語サービス（言語切替・翻訳）(P3) |
| `tests/test_metrics_service.py` | メトリクスサービス（A/B テスト指標記録）(P3) |
| `tests/test_statistics_service.py` | 統計サービス（実験結果分析）(P3) |
| `tests/test_tenant.py` | テナント（作成・設定更新・無効化）(P3) |
| `tests/test_retention.py` | データ保持ポリシー（保持期間・削除リクエスト・監査ログ）(P3) |
| `tests/test_user.py` | ユーザー（プロファイル・履歴・推薦）(P3) |
| `tests/test_user_context_middleware.py` | ユーザーコンテキストミドルウェア（コンテキスト注入）(P3) |

### フロントエンドテスト

| ファイル | テスト対象 |
|---------|-----------|
| `src/__tests__/ChatInput.test.tsx` | チャット入力（画像添付含む）(P3) |
| `src/__tests__/MarkdownRenderer.test.tsx` | Markdown レンダリング (P3) |
| `src/__tests__/useAutoScroll.test.ts` | 自動スクロールフック (P3) |
| `src/__tests__/useChat.test.ts` | チャット状態管理フック (P3) |
| `src/__tests__/useLanguage.test.tsx` | 言語管理フック (P3) |
| `src/__tests__/api.test.ts` | REST API クライアント (P3) |
| `src/__tests__/logger.test.ts` | ロガー (P3) |
| `src/__tests__/sse.test.ts` | SSE 接続管理 (P3) |

### テスト設定

| 項目 | 値 |
|------|----|
| テストフレームワーク | pytest >= 8.0.0 |
| 非同期サポート | pytest-asyncio >= 0.24.0（asyncio_mode = "auto"） |
| カバレッジ | pytest-cov >= 5.0.0 |
| HTTP クライアント | httpx >= 0.27.0 |
| テストディレクトリ | `tests/` |

### テストカバレッジ

目標カバレッジ: 80% 以上。

テスト合計数: P3完了時点 **1,121 テスト**。テストファイルは 66 ファイル（バックエンド 58 ファイル + フロントエンド 8 ファイル）。

各レイヤーのテスト戦略:
- **モデルテスト**: バリデーションルール、フィールドのデフォルト値、enum 値の検証
- **APIテスト**: 正常系・異常系のレスポンス、SSE ストリームの挙動
- **ツールテスト**: LLM 呼び出しのモック、各ツールの入出力検証、HITL interrupt の動作
- **RAGテスト**: VectorStore のシングルトン、ドキュメントのロード・チャンク分割・検索
- **統合テスト**: フルフローのエンドツーエンド検証、HITL フローの再現

---

## 8. サンプルデータ

### 製品サポートFAQの構成

`data/sample_docs/` ディレクトリに 3 つの Markdown ファイルが格納されている。

| ファイル名 | カテゴリ | 行数 | 内容 |
|-----------|---------|------|------|
| `product_guide.md` | 操作方法 | 272 行 | 製品A・B・C の操作ガイド |
| `troubleshooting.md` | 障害・トラブル | 257 行 | ログイン問題・エラー対応 |
| `contracts.md` | 契約・料金 | 281 行 | プラン・料金・契約 FAQ |

### カテゴリ一覧

| カテゴリ名 | 対応ファイル | 内容例 |
|----------|-------------|-------|
| 操作方法 | `product_guide.md` | 初期設定手順・ログイン方法・機能説明 |
| 障害・トラブル | `troubleshooting.md` | パスワードリセット・アカウントロック解除・エラー対処 |
| 契約・料金 | `contracts.md` | ベーシック/スタンダード/エンタープライズプラン・解約手順 |
| その他 | （ファイル名が上記以外の場合） | 製品関連のその他の質問 |

### データ量の概要

| 指標 | 値 |
|------|----|
| ソースファイル数 | 3 ファイル |
| 総行数 | 約 810 行 |
| 想定チャンク数 | 数十〜百チャンク程度（chunk_size=800, overlap=100） |
| ChromaDB コレクション | `product_support_v2` |

---

## 9. 制限事項・今後の課題

### 現時点の制限事項

| 項目 | 内容 |
|------|------|
| **インメモリ状態管理** | `PostgresSaver` 導入済み（P2-40）。接続エラー時は `MemorySaver` にフォールバック |
| **インメモリキュー** | `ChatService._queues` / `_tasks` はプロセスメモリに保持されるため、マルチプロセス・水平スケーリング不可 |
| **スレッドクリーンアップ** | SSE 終了時に `finally` で `cleanup()` を呼び出すが、SSE 未接続のまま放置されたキューは LRU eviction（上限 1000）に依存する |
| **ドキュメント更新** | ドキュメント追加・削除はAPIで可能だが、更新（PUT）は未実装。更新時は削除→追加で対応 |
| **LLM 呼び出しの多さ** | 1 回の回答生成で最大 6〜7 回（classify, rewrite, relevance, generate, quality, escalation + HITL）LLM API を呼び出す |
| **エラーリカバリ** | 品質チェック失敗時の再試行ロジックはシステムプロンプトの指示に依存しており、実装上の制限がある |
| **シングルトン** | `VectorStore`, `ChatService`, `Deep Agent` はいずれもプロセスシングルトンのためテスト間の分離に注意が必要 |
| **確認ダイアログ未実装** | 「新しい会話」ボタンに確認ダイアログが未実装（誤操作防止） |
| **visualViewport未対応** | モバイルでのソフトウェアキーボード表示時のレイアウト調整が未実装 |

### P1で完了した項目

| 項目 | 内容 |
|------|------|
| ~~**CORS設定**~~ | ~~デフォルトで `localhost:5173` と `localhost:3000` のみ許可~~ → **P1-30 で適正化済み**（メソッド・ヘッダー制限） |
| ~~**ドキュメント管理 API**~~ | ~~ドキュメントの追加・削除・更新を行う管理用 API エンドポイントの追加~~ → **P1-32 で実装済み**（GET/POST/DELETE） |
| ~~**埋め込みモデルのカスタマイズ**~~ | ~~`VectorStore` の埋め込み関数を変更~~ → **P1-11 で実装済み**（multilingual-e5-base） |
| ~~**ハイブリッド検索**~~ | ~~BM25 + ベクトル検索の統合~~ → **P1-16 で実装済み**（RRF統合） |
| ~~**セキュリティヘッダー**~~ | ~~X-Frame-Options等のセキュリティヘッダー追加~~ → **P1-29 で実装済み** |
| ~~**APIキー保護**~~ | ~~設定ファイルでのAPIキー平文保存~~ → **P1-31 でSecretStr化済み** |
| ~~**フィードバック機能**~~ | ~~回答へのフィードバック収集~~ → **P1-23 で実装済み**（thumbs up/down） |
| ~~**ナレッジギャップ検出**~~ | ~~回答できなかった質問の可視化~~ → **P1-33 で実装済み** |

### P2で完了した項目

| 項目 | 内容 |
|------|------|
| ~~**インメモリ状態管理**~~ | ~~`MemorySaver` はプロセス再起動で会話履歴が消失する~~ → **P2-40 で PostgresSaver 移行済み**（フォールバック付き） |
| ~~**構造化ロギング**~~ | ~~ログフォーマットの統一~~ → **P2-41 で structlog 導入済み**（JSON形式・リクエストID相関） |
| ~~**コスト可視化**~~ | ~~LLM呼び出しのコスト管理~~ → **P2-42 で実装済み**（トークン記録・モデル別集計・上限アラート） |
| ~~**ヘルスチェック詳細化**~~ | ~~外部サービスの疎通確認~~ → **P2-43 で実装済み**（ChromaDB・OpenAI・メモリ使用量） |

### P3で完了した項目

| 項目 | 内容 |
|------|------|
| ~~**マルチテナント対応**~~ | → **P3 で実装済み**（TenantMiddleware + テナント管理 API） |
| ~~**GDPR/データ保持ポリシー**~~ | → **P3 で実装済み**（ポリシー管理・自動削除・監査ログ） |
| ~~**CRM/チケットシステム連携**~~ | → **P3 で実装済み**（Zendesk アダプター） |
| ~~**画像添付**~~ | → **P3 で実装済み**（Vision API + react-dropzone） |
| ~~**多言語対応**~~ | → **P3 で実装済み**（i18next 日本語/英語、LanguageSwitcher コンポーネント） |
| ~~**マルチチャネル**~~ | → **P3 で実装済み**（LINE/Slack/Email Webhook アダプター） |
| ~~**パーソナライゼーション**~~ | → **P3 で実装済み**（UserContextMiddleware・ユーザープロファイル） |
| ~~**A/B テスト基盤**~~ | → **P3 で実装済み**（実験作成・バリアント割り当て・メトリクス記録） |
| ~~**ガードレール/ジェイルブレイク対策**~~ | → **P3 で実装済み**（入出力チェック・PII 検出・レッドチーミング） |

> **注記:** `LanguageSwitcher` コンポーネントは実装済みだが、`App.tsx` / `ChatWindow.tsx` への UI 統合は未完了（P3制限事項）。

### 拡張ポイント

| 項目 | 概要 |
|------|------|
| ~~**永続化チェックポインタ**~~ | ~~MemorySaver を PostgresSaver / RedisSaver に~~ → **P2-40 で PostgresSaver 移行済み** |
| **Redis キュー** | `asyncio.Queue` を Redis Pub/Sub または Redis Streams に置き換えることで水平スケーリングに対応 |
| **ドキュメント更新API** | `PUT /api/admin/knowledge/{doc_id}` の実装 |
| **ユーザー登録・ロール管理** | JWT 認証・UserContextMiddleware は実装済みだが、ユーザー登録フローとロールベースアクセス制御は未実装 |
| **会話履歴の永続化** | データベースへの会話履歴の保存と検索 |
| ~~**マルチモーダル対応**~~ | ~~画像・PDF のアップロード~~ → **P3 で画像解析（Vision API）対応済み**。PDF 取り込みは未実装 |
| **LanguageSwitcher UI 統合** | `LanguageSwitcher` コンポーネントを `App.tsx` / `ChatWindow.tsx` に組み込む |
| **ストリーミング検索** | RAG 検索の段階的なストリーミング配信によるレイテンシ改善 |
| **エージェントグラフの可視化** | LangGraph Studio との連携によるデバッグ・モニタリング |
| ~~**レート制限**~~ | ~~API エンドポイントへのレート制限とスロットリング機能の追加~~ → **P0-02 で実装済み**（slowapi） |
| ~~**埋め込みモデルのカスタマイズ**~~ | ~~`VectorStore` の埋め込み関数を変更~~ → **P1-11 で実装済み** |
| ~~**ドキュメント管理 API**~~ | ~~ドキュメントの追加・削除・更新~~ → **P1-32 で実装済み** |
