# Agentic RAG チャットボット 実装計画

## Context

製品サポート向けの Agentic RAG チャットボットを構築する。ユーザーが Web 画面から問い合わせを入力すると、バックエンドが Deep Agents を中心に自律的に判断しながら、曖昧さの解消（HITL）、クエリリライト、RAG検索、関連性チェック、回答生成、品質チェックを経て最終回答を返す。

**技術選定の決定事項:**
- LLM: OpenAI (gpt-4o-mini デフォルト、gpt-4o 切替可能)
- ドメイン: 製品サポート（カテゴリ: 操作方法、障害・トラブル、契約・料金、その他）
- Deep Agents: メインフレームワークとして使用。RAGワークフローをツールとして組み込む

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│              Frontend (React + Vite + shadcn/ui)             │
│  ┌────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│  │ ChatWindow │ │ MessageList  │ │ HITLWidget             │ │
│  │            │ │ (auto-scroll)│ │ (buttons / text input) │ │
│  └────────────┘ └──────────────┘ └────────────────────────┘ │
│           useChat() hook — SSE consumer + POST sender        │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────┴──────────────────────────────────┐
│              Backend (FastAPI + Python/uv)                    │
│                                                              │
│  POST /api/chat ─────► ChatService ─► Deep Agent             │
│  GET  /api/chat/stream/{thread_id} ─► SSE streaming          │
│  POST /api/chat/resume/{thread_id} ─► Command(resume=...)    │
│                                                              │
│  ┌─── Deep Agent (create_deep_agent) ──────────────────────┐│
│  │  System Prompt: 製品サポートエージェント                   ││
│  │  Tools:                                                  ││
│  │   • classify_query   — 質問分類 + HITL interrupt         ││
│  │   • rewrite_query    — クエリリライト                     ││
│  │   • search_knowledge — RAG検索 (ChromaDB)               ││
│  │   • check_relevance  — 検索結果の関連性チェック           ││
│  │   • generate_answer  — 回答生成                          ││
│  │   • check_quality    — 品質チェック (ハルシネーション等)   ││
│  │   • ask_human        — HITL (汎用的な聞き返し)           ││
│  │                                                          ││
│  │  LangGraph StateGraph + MemorySaver (checkpoint)         ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ChromaDB (ローカル永続化) ← 製品サポートFAQサンプルデータ     │
└──────────────────────────────────────────────────────────────┘
```

**Deep Agents メイン構成の利点:**
- エージェントが自律的にどのツールをいつ呼ぶか判断（固定ノード順序ではなく、状況に応じた柔軟な処理）
- `write_todos` による内部計画で複雑なクエリを段階的に処理
- `interrupt()` によるネイティブ HITL サポート
- LangGraph の checkpointer で会話状態を永続化

---

## プロジェクト構成

```
/workspace/agentic-rag-chatbot/
├── frontend/                           # React + Vite + shadcn/ui
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx      # ルートコンテナ
│   │   │   │   ├── MessageList.tsx     # メッセージ一覧 (auto-scroll)
│   │   │   │   ├── MessageBubble.tsx   # 個別メッセージ表示
│   │   │   │   ├── ChatInput.tsx       # ユーザー入力
│   │   │   │   └── TypingIndicator.tsx # ストリーミング中表示
│   │   │   └── hitl/
│   │   │       ├── HITLWidget.tsx      # HITL ディスパッチャー
│   │   │       ├── ClarificationButtons.tsx  # 選択肢ボタン
│   │   │       └── ClarificationInput.tsx    # フリーテキスト入力
│   │   ├── hooks/
│   │   │   ├── useChat.ts             # SSE + 状態管理の中核
│   │   │   └── useAutoScroll.ts       # 自動スクロール
│   │   ├── lib/
│   │   │   ├── api.ts                 # API呼び出しラッパー
│   │   │   └── sse.ts                 # EventSource管理
│   │   ├── types/
│   │   │   ├── message.ts             # Message, HITLRequest型
│   │   │   └── api.ts                 # ApiResponse<T>
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts                 # /api → backend proxy
│   ├── package.json
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app + CORS + lifespan
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                # POST /chat, GET /stream, POST /resume
│   │   │   └── health.py              # GET /health
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Deep Agent (create_deep_agent) 定義
│   │   │   ├── state.py               # AgentState TypedDict
│   │   │   ├── prompts.py             # システムプロンプト定義
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── classify.py        # classify_query ツール
│   │   │       ├── rewrite.py         # rewrite_query ツール
│   │   │       ├── search.py          # search_knowledge ツール
│   │   │       ├── relevance.py       # check_relevance ツール
│   │   │       ├── generate.py        # generate_answer ツール
│   │   │       ├── quality.py         # check_quality ツール
│   │   │       └── ask_human.py       # ask_human ツール (汎用HITL)
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py        # ChromaDB ラッパー
│   │   │   ├── retriever.py           # LangChain retriever
│   │   │   └── document_loader.py     # ドキュメント読込・チャンク化
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                # ChatRequest, ChatStartResponse
│   │   │   ├── messages.py            # StreamEvent
│   │   │   └── hitl.py                # HITLRequest, HITLResponse
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py            # Pydantic BaseSettings
│   │   └── services/
│   │       ├── __init__.py
│   │       └── chat_service.py        # Graph実行 + SSEキュー管理
│   ├── data/
│   │   └── sample_docs/               # 製品サポートFAQサンプル
│   │       ├── product_guide.md       # 操作方法
│   │       ├── troubleshooting.md     # 障害・トラブル対応
│   │       └── contracts.md           # 契約・料金
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_models.py
│   │   ├── test_tools.py
│   │   └── test_api.py
│   ├── pyproject.toml
│   └── .env.example
│
├── .gitignore
└── README.md
```

---

## API コントラクト

### POST /api/chat
新規会話開始 or 既存スレッドへのメッセージ送信。

```json
// Request
{ "message": "製品Aの返品方法を教えてください", "thread_id": null }

// Response (202 Accepted)
{ "success": true, "data": { "thread_id": "uuid", "status": "streaming" } }
```

### GET /api/chat/stream/{thread_id}
SSE ストリーム。トークン単位の応答 + HITL リクエストを配信。

```
data: {"type":"token","content":"返品"}
data: {"type":"token","content":"について"}
data: {"type":"hitl_request","request_id":"uuid","question":"どの製品ですか？","options":["製品A","製品B","製品C"],"input_type":"buttons"}
data: {"type":"message_complete","content":"返品手続きは..."}
data: {"type":"done"}
```

### POST /api/chat/resume/{thread_id}
HITL 中断から再開。

```json
// Request
{ "request_id": "uuid", "response": "製品A" }

// Response (202 Accepted)
{ "success": true, "data": { "thread_id": "uuid", "status": "streaming" } }
```

### GET /api/health
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## タスク分割（11タスク・順次実行）

### Task 1: プロジェクトスキャフォールド（Backend + Frontend）
**内容**: uv で Python プロジェクト初期化、Vite で React プロジェクト生成、ディレクトリ構造作成
**作成ファイル**:
- `backend/pyproject.toml` — 依存関係 (fastapi, uvicorn, langgraph, langchain, langchain-openai, chromadb, deepagents, pydantic-settings)
- `backend/app/__init__.py`, `backend/app/main.py` (最小限のFastAPIアプリ + CORS)
- `backend/app/config/settings.py` (Pydantic BaseSettings)
- `backend/.env.example`
- `frontend/` — Vite React TypeScript テンプレート生成
- `frontend/vite.config.ts` — `/api` → `localhost:8000` プロキシ
- `.gitignore`, `README.md`
**完了条件**: `uv run uvicorn app.main:app` が起動し `/api/health` が200返却、`npm run dev` が起動

### Task 2: Backend データモデル（Pydantic + State）
**内容**: API・エージェント間で共有するすべてのデータモデル定義
**作成ファイル**:
- `backend/app/models/chat.py` — ChatRequest, ChatStartResponse
- `backend/app/models/messages.py` — StreamEvent
- `backend/app/models/hitl.py` — HITLRequest, HITLResponse
- `backend/app/agents/state.py` — AgentState TypedDict
- `backend/tests/test_models.py`
**依存**: Task 1

### Task 3: RAG ベクトルストアセットアップ
**内容**: ChromaDB 統合、ドキュメントローダー、サンプル製品サポートデータ作成
**作成ファイル**:
- `backend/app/rag/vector_store.py` — ChromaDB シングルトン
- `backend/app/rag/retriever.py` — LangChain retriever
- `backend/app/rag/document_loader.py` — Markdown読込 + チャンク分割
- `backend/data/sample_docs/product_guide.md` — 操作ガイド
- `backend/data/sample_docs/troubleshooting.md` — トラブルシューティング
- `backend/data/sample_docs/contracts.md` — 契約・料金FAQ
- `backend/tests/test_rag.py` (ChromaDBモック)
**依存**: Task 1, Task 2

### Task 4: Deep Agent ツール実装（classify, rewrite, search）
**内容**: Deep Agent に登録する前半3ツールの実装
**作成ファイル**:
- `backend/app/agents/tools/classify.py` — 質問分類 (valid/ambiguous/out_of_scope/unclear_category) + HITL interrupt
- `backend/app/agents/tools/rewrite.py` — 会話履歴を考慮したクエリリライト
- `backend/app/agents/tools/search.py` — ChromaDB からの RAG 検索
- `backend/app/agents/tools/__init__.py`
**依存**: Task 2, Task 3

### Task 5: Deep Agent ツール実装（relevance, generate, quality, ask_human）
**内容**: Deep Agent に登録する後半4ツールの実装
**作成ファイル**:
- `backend/app/agents/tools/relevance.py` — 検索結果の関連性チェック
- `backend/app/agents/tools/generate.py` — RAG ベースの回答生成
- `backend/app/agents/tools/quality.py` — ハルシネーション + 充足性チェック
- `backend/app/agents/tools/ask_human.py` — 汎用HITL (interrupt)
- `backend/tests/test_tools.py`
**依存**: Task 4

### Task 6: Deep Agent 定義 + システムプロンプト
**内容**: `create_deep_agent` でエージェント構築。全ツールをバインドし、製品サポート向けシステムプロンプトを定義
**作成ファイル**:
- `backend/app/agents/agent.py` — Deep Agent 構築 (create_deep_agent + tools + checkpointer)
- `backend/app/agents/prompts.py` — システムプロンプト（製品カテゴリ定義、HITL判断基準、応答フォーマット）
**依存**: Task 4, Task 5
**重要な実装ポイント**:
- MemorySaver で会話状態を永続化
- ツール一覧を `tools` パラメータで渡す
- システムプロンプトに「曖昧な場合は ask_human で聞き返す」「スコープ外は即座に応答」等の指示を含める

### Task 7: FastAPI エンドポイント + ChatService
**内容**: REST API 3エンドポイント + SSEストリーミング基盤 + Deep Agent実行サービス
**作成ファイル**:
- `backend/app/api/chat.py` — POST /chat, GET /stream/{thread_id}, POST /resume/{thread_id}
- `backend/app/api/health.py` — GET /health
- `backend/app/services/chat_service.py` — asyncio.Queue でSSEイベント配信、graph.astream でトークンストリーミング
- `backend/app/api/__init__.py`
- `backend/app/services/__init__.py`
- `backend/tests/test_api.py`
**依存**: Task 2, Task 6
**重要な実装ポイント**:
- `asyncio.create_task` でグラフ実行をバックグラウンド化
- `interrupt()` 発生時は `hitl_request` イベントとしてSSEに送出
- `Command(resume=...)` で中断再開
- スレッド別の asyncio.Queue でイベントを管理

### Task 8: Frontend セットアップ + shadcn/ui 導入
**内容**: shadcn/ui インストール、Tailwind 設定、型定義、基本レイアウト
**作成ファイル**:
- `frontend/src/types/message.ts` — Message, HITLRequest, ChatEvent 型
- `frontend/src/types/api.ts` — ApiResponse<T>
- `frontend/src/lib/api.ts` — sendMessage, resumeChat fetch ラッパー
- `frontend/src/lib/sse.ts` — EventSource 管理
- `frontend/src/App.tsx` — 基本レイアウト
- shadcn/ui コンポーネント追加 (button, input, scroll-area, card)
**依存**: Task 1

### Task 9: チャットUIコンポーネント
**内容**: チャット画面のReactコンポーネント群
**作成ファイル**:
- `frontend/src/components/chat/ChatWindow.tsx` — ルートコンテナ
- `frontend/src/components/chat/MessageList.tsx` — メッセージ一覧
- `frontend/src/components/chat/MessageBubble.tsx` — 個別メッセージ（user/assistant 切替）
- `frontend/src/components/chat/ChatInput.tsx` — テキスト入力 + 送信ボタン
- `frontend/src/components/chat/TypingIndicator.tsx` — ストリーミング中アニメーション
- `frontend/src/hooks/useAutoScroll.ts`
**依存**: Task 8

### Task 10: SSE統合 + HITLコンポーネント + useChat Hook
**内容**: フロントエンドの中核ロジック。SSEストリーミング消費、HITL UI、状態管理
**作成ファイル**:
- `frontend/src/hooks/useChat.ts` — SSE接続、メッセージ蓄積、HITL状態遷移、resume API呼び出し
- `frontend/src/components/hitl/HITLWidget.tsx` — HITL種別に応じたUIディスパッチ
- `frontend/src/components/hitl/ClarificationButtons.tsx` — 選択肢ボタン表示
- `frontend/src/components/hitl/ClarificationInput.tsx` — フリーテキスト入力
**依存**: Task 8, Task 9
**重要な実装ポイント**:
- 不変性パターン: `setState(prev => ({...prev, messages: [...prev.messages, newMsg]}))`
- EventSource の `onmessage` で `ChatEvent` をパース
- `hitl_request` 受信時にSSE切断し、HITL UIを表示
- ユーザー応答後に POST /resume → 新規SSE接続

### Task 11: 結合テスト + 最終検証
**内容**: Frontend-Backend 結合確認、エラーハンドリング補強、README 完成
**作成・修正ファイル**:
- `backend/tests/test_api.py` (結合テスト拡充)
- `frontend/src/components/ErrorBoundary.tsx`
- `README.md` (セットアップ手順、起動方法、環境変数一覧)
**依存**: 全タスク
**検証項目**:
- 正常フロー: 質問 → ストリーミング回答
- HITL フロー: 曖昧質問 → ボタン表示 → 選択 → 回答再開
- スコープ外: 「天気を教えて」→ サポート外メッセージ
- エラー: API未到達時のフロントエンド表示

---

## 主要依存パッケージ

### Backend (pyproject.toml)
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langgraph>=1.0.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.3.0",
    "langchain-community>=0.3.0",
    "deepagents>=0.1.0",
    "chromadb>=0.5.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "python-dotenv>=1.0.0",
    "langchain-text-splitters>=0.3.0",
]
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^19",
    "react-dom": "^19",
    "uuid": "^11",
    "zod": "^3"
  }
}
```
+ shadcn/ui (button, input, scroll-area, card, badge)

---

## タスク分割と実行戦略（必ず従うこと）

リーダー（自分自身）は以下のワークフローに厳密に従う：

### 実行フロー
1. まず全体を独立した小タスクに分割し、**TaskCreate** で全11タスクを登録する
2. タスクは **1つずつ順番** に処理する
3. 各タスクの処理フロー：
   a. 新しいサブエージェントを **Task ツール** (`subagent_type: "general-purpose"`, `model: "sonnet"`) で起動する
   b. そのサブエージェントに「タスクの内容」「関連ファイルパス」「前のタスクの成果物の情報」を **詳細にプロンプトで渡す**
   c. サブエージェントの **完了報告を待つ**
   d. 完了したらタスクに対応するサブエージェントは自動的に終了する
   e. **TaskUpdate** でタスクを `completed` にする
4. 次のタスクで **新しいサブエージェント** を起動する（前のものは再利用しない）
5. 全タスク完了後、最終確認を行う

### 重要なルール
- サブエージェントは **1タスクにつき1インスタンス**（使い回さない）
- タスク完了後は必ずサブエージェントを終了させる
- 次のサブエージェントには、前タスクの結果として必要な情報（作成されたファイルパス、API 仕様など）を **必ずプロンプトに含める**
- リーダー自身は **コードを書かない**。指示と管理に専念する
- サブエージェントへのプロンプトには以下を必ず含める:
  - 作業対象の具体的なファイルパス
  - 実装の詳細仕様（型定義、関数シグネチャ、依存関係）
  - 前タスクで作成済みのファイル一覧
  - 「ユーザーへの報告・質問・確認は必ず日本語で行うこと」

### タスク依存関係
```
Task 1 (Scaffold)
    ├── Task 2 (Models) ──┬── Task 4 (Tools前半) ── Task 5 (Tools後半) ── Task 6 (Agent定義)
    │                     └── Task 3 (RAG) ──────────────────────────────────────┘
    │                                                                            │
    │                                                                     Task 7 (API)
    └── Task 8 (Frontend Setup)
            └── Task 9 (Chat UI)
                    └── Task 10 (SSE + HITL)
                                └── Task 11 (結合テスト)
```

---

## 検証方法

1. **Backend 単体**: `uv run pytest --cov=app --cov-report=term-missing` → 80%+
2. **Backend 起動**: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
3. **Frontend 起動**: `cd frontend && npm run dev` → `http://localhost:5173`
4. **手動テスト**:
   - 通常質問: 「製品Aの初期設定方法を教えてください」→ ストリーミング回答
   - 曖昧質問: 「使い方」→ HITL 聞き返し → カテゴリ選択 → 回答
   - スコープ外: 「明日の天気は？」→ サポート外メッセージ
   - 会話継続: 「もっと詳しく」→ 前ターンを考慮したリライト → 回答
5. **TypeScript**: `cd frontend && npx tsc --noEmit`
6. **Lint**: `cd backend && uv run ruff check .`
