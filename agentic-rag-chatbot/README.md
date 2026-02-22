# Agentic RAG チャットボット

製品サポート向けの Agentic RAG (Retrieval-Augmented Generation) チャットボット。
LangGraph の ReAct エージェントが自律的にナレッジベース検索・回答生成・品質チェックを行い、
必要に応じてユーザーに確認（HITL: Human-in-the-Loop）を挟みながら最適な回答を提供します。

## 機能

- RAG ベースの質問応答（ChromaDB + OpenAI）
- SSE によるリアルタイムストリーミング
- HITL（Human-in-the-Loop）による曖昧さの解消
- 自動的な質問分類・クエリリライト・品質チェック
- 会話履歴の保持（LangGraph Checkpointer）

## アーキテクチャ

**バックエンド**
- FastAPI + Python 3.11+
- LangGraph ReAct Agent（7つのツール）
- ChromaDB（ベクトルストア）
- OpenAI GPT-4o-mini / GPT-4o

**フロントエンド**
- React 19 + TypeScript
- Vite
- shadcn/ui + Tailwind CSS v4
- SSE (EventSource)

## セットアップ

### 前提条件
- Python 3.11+
- Node.js 18+
- uv (Python パッケージマネージャー)
- OpenAI API キー

### Backend

```bash
cd backend
cp .env.example .env
# .env に OPENAI_API_KEY を設定

# 依存関係インストール
uv sync --extra dev

# サーバー起動
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 でアクセス

## 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| OPENAI_API_KEY | OpenAI API キー | (必須) |
| OPENAI_MODEL | 使用するモデル | gpt-4o-mini |
| CHROMA_PERSIST_DIR | ChromaDB 保存先 | ./data/chroma_db |
| CHROMA_COLLECTION_NAME | コレクション名 | product_support |

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | /api/health | ヘルスチェック |
| POST | /api/chat | チャット開始/メッセージ送信 |
| GET | /api/chat/stream/{thread_id} | SSE ストリーム |
| POST | /api/chat/resume/{thread_id} | HITL 再開 |

## テスト

```bash
cd backend
uv run pytest tests/ -v --cov=app --cov-report=term-missing
```

## 使い方

1. 通常の質問: 「製品Aの初期設定方法を教えてください」→ ストリーミングで回答
2. 曖昧な質問: 「使い方を教えて」→ カテゴリ選択ボタンが表示 → 選択後に回答
3. サポート外: 「明日の天気は？」→ サポート範囲外メッセージ
4. 会話継続: 「もっと詳しく」→ 前のコンテキストを考慮した回答
