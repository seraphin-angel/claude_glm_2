# Agentic RAG チャットボット

> バージョン: 0.4.0 (P3完了)
> 最終更新: 2026-02-28

製品サポート向けの Agentic RAG (Retrieval-Augmented Generation) チャットボット。
LangGraph の ReAct エージェントが自律的にナレッジベース検索・回答生成・品質チェックを行い、
必要に応じてユーザーに確認（HITL: Human-in-the-Loop）を挟みながら最適な回答を提供します。

## 機能

### 基本機能
- RAG ベースの質問応答（ChromaDB + OpenAI）
- SSE によるリアルタイムストリーミング
- HITL（Human-in-the-Loop）による曖昧さの解消
- 自動的な質問分類・クエリリライト・品質チェック
- 会話履歴の保持（LangGraph Checkpointer）

### 検索・RAG機能
- ハイブリッド検索（ベクトル検索 + BM25 キーワード検索）
- Cross-Encoder によるリランキング
- Multi-Query / HyDE による検索精度向上
- 関連性評価・スキップ閾値による効率化

### UX機能
- Markdown レンダリング（コードブロック・テーブル対応）
- サジェストチップ（よくある質問の提示）
- ツール実行進捗の可視化
- フィードバック送信（高評価/低評価）
- コピーボタン
- FAQ 管理・表示
- 多言語対応（i18next による日本語/英語対応 — UI統合準備中）
- 画像添付・Vision API によるスクリーンショット解析

### エンタープライズ機能（P3）
- マルチテナント対応 — テナント別コレクション分離・ミドルウェア
- GDPR/データ保持ポリシー — 保持期間設定・忘れられる権利・自動削除・監査ログ
- CRM/チケットシステム連携 — Zendesk アダプター
- マルチチャネル — LINE/Slack/Email Webhook アダプター
- パーソナライゼーション — ユーザープロファイル・推薦
- A/B テスト基盤 — 実験作成・バリアント割り当て・メトリクス

### セキュリティ
- JWT 認証・レート制限
- ガードレール/ジェイルブレイク対策 — 入出力安全性チェック
- PII（個人情報）検出
- セキュリティヘッダー・リクエスト ID 管理

### 運用
- 構造化ロギング・リクエストトレーシング
- コスト可視化
- ヘルスチェック
- PostgreSQL によるセッション永続化

## アーキテクチャ

**バックエンド**
- FastAPI + Python 3.11+
- LangGraph ReAct Agent（11ツール: 8コアツール + analyze_image, check_input_safety, check_output_safety）
- ChromaDB（ベクトルストア）
- OpenAI GPT-4o-mini / GPT-4o
- PostgreSQL（LangGraph Checkpointer）

**ミドルウェア（6個）**
- CORSMiddleware
- RequestLoggingMiddleware
- RequestIdMiddleware
- SecurityHeadersMiddleware
- TenantMiddleware（P3: マルチテナント）
- UserContextMiddleware（P3: ユーザーコンテキスト）

**フロントエンド**
- React 19 + TypeScript
- Vite
- shadcn/ui + Tailwind CSS v4
- SSE (EventSource)
- i18next（多言語対応）
- react-dropzone（画像アップロード）
- rehype-sanitize（Markdown サニタイズ）

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
| EMBEDDING_MODEL | 埋め込みモデル | intfloat/multilingual-e5-base |
| CHROMA_PERSIST_DIR | ChromaDB 保存先 | ./data/chroma_db |
| CHROMA_COLLECTION_NAME | コレクション名 | product_support_v2 |
| CHUNK_SIZE | チャンクサイズ | 800 |
| CHUNK_OVERLAP | チャンクオーバーラップ | 100 |
| RELEVANCE_SKIP_THRESHOLD | 関連性評価スキップ閾値 | 0.85 |
| HYBRID_SEARCH_ALPHA | ハイブリッド検索のベクトル重み | 0.7 |
| JWT_SECRET_KEY | JWT 署名用シークレットキー | (本番では必ず変更) |
| JWT_ALGORITHM | JWT 署名アルゴリズム | HS256 |
| JWT_EXPIRE_MINUTES | JWT トークン有効期限（分） | 60 |
| RATE_LIMIT_CHAT | チャット API レート制限 | 20/minute |
| RATE_LIMIT_STREAM | ストリーム API レート制限 | 30/minute |
| CORS_ALLOWED_METHODS | CORS 許可メソッド | GET,POST,OPTIONS |
| CORS_ALLOWED_HEADERS | CORS 許可ヘッダー | Authorization,Content-Type |
| DATABASE_URL | PostgreSQL 接続 URL | (本番では必ず変更) |
| DEBUG_MODE | デバッグモード（エラー詳細表示） | false |

## API エンドポイント

### 基本 API
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/health | 不要 | ヘルスチェック |
| POST | /api/chat | JWT | チャット開始/メッセージ送信 |
| POST | /api/chat/image | JWT | 画像付きチャット |
| GET | /api/chat/stream/{thread_id} | JWT | SSE ストリーム |
| POST | /api/chat/resume/{thread_id} | JWT | HITL 再開 |
| POST | /api/feedback | JWT | フィードバック送信 |

### 管理 API
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/admin/knowledge | JWT | ドキュメント一覧 |
| POST | /api/admin/knowledge | JWT | ドキュメント追加 |
| GET | /api/admin/knowledge/{id} | JWT | ドキュメント取得 |
| DELETE | /api/admin/knowledge/{id} | JWT | ドキュメント削除 |
| GET | /api/admin/knowledge-gaps | JWT | ギャップ一覧 |

### テナント API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/tenants | JWT | テナント一覧 |
| POST | /api/tenants | JWT | テナント作成 |
| GET | /api/tenants/{tenant_id} | JWT | テナント取得 |
| PUT | /api/tenants/{tenant_id}/config | JWT | テナント設定更新 |
| DELETE | /api/tenants/{tenant_id} | JWT | テナント無効化 |

### ユーザー API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/users/me | JWT | 現在のユーザー情報取得 |
| GET | /api/users/me/history | JWT | 会話履歴取得 |
| PATCH | /api/users/me/plan | JWT | ユーザープラン更新（管理者のみ）|
| GET | /api/users/me/recommendations | JWT | パーソナライズ推薦取得 |

### GDPR API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/gdpr/policies | JWT | データ保持ポリシー作成 |
| GET | /api/gdpr/policies | JWT | 保持ポリシー一覧取得 |
| POST | /api/gdpr/delete-user-data | JWT | ユーザーデータ削除（GDPR Article 17）|
| GET | /api/gdpr/audit-logs | JWT | 監査ログ取得 |
| POST | /api/gdpr/cleanup | JWT | 期限切れデータクリーンアップ |

### マルチチャネル API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/channels/{tenant_id}/line/webhook | 署名検証 | LINE Webhook |
| POST | /api/channels/{tenant_id}/slack/webhook | 署名検証 | Slack Webhook |
| POST | /api/channels/{tenant_id}/email/webhook | 署名検証 | Email Webhook |

### 実験 API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/experiments | JWT | 実験作成 |
| GET | /api/experiments/{id} | JWT | 実験取得 |
| POST | /api/experiments/{id}/assign | JWT | バリアント割り当て |
| POST | /api/experiments/{id}/metrics | JWT | メトリクス記録 |

### ガードレール API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/v1/guardrails/check-input | 不要 | 入力安全性チェック |
| POST | /api/v1/guardrails/check-output | 不要 | 出力安全性チェック |

### インテグレーション API（P3）
| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/integrations/register | JWT | CRM アダプター登録 |
| GET | /api/integrations | JWT | 登録済み連携一覧 |
| POST | /api/integrations/tickets | JWT | CRM チケット作成 |

> `/api/health` 以外の全エンドポイントは `Authorization: Bearer <token>` ヘッダーが必要です。

## テスト

```bash
cd backend
uv run pytest tests/ -v --cov=app --cov-report=term-missing
```

テストファイル: バックエンド 58 ファイル + フロントエンド 8 ファイル = 合計 **66 ファイル**

## 使い方

1. 通常の質問: 「製品Aの初期設定方法を教えてください」→ ストリーミングで回答
2. 曖昧な質問: 「使い方を教えて」→ カテゴリ選択ボタンが表示 → 選択後に回答
3. サポート外: 「明日の天気は？」→ サポート範囲外メッセージ
4. 会話継続: 「もっと詳しく」→ 前のコンテキストを考慮した回答
5. 画像添付: スクリーンショットをアップロード → Vision API による解析と回答
