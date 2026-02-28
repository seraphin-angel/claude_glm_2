# Agentic RAG Chatbot - Frontend

React + TypeScript + Vite で構築されたチャットボットフロントエンドアプリケーション。

## 機能

### チャット機能
- **リアルタイムストリーミング**: SSE (Server-Sent Events) によるストリーミングレスポンス
- **HITL (Human-in-the-Loop)**: エージェントからの質問に回答可能
- **ツール実行表示**: エージェントが使用するツールの実行状態をリアルタイム表示
- **会話履歴**: スレッドIDによる会話コンテキスト維持

### UI/UX
- **Markdownレンダリング**: コードブロックのシンタックスハイライト対応
- **FAQサジェスト**: ページコンテキストに基づくFAQ推奨
- **フィードバック機能**: メッセージごとの👍/👎フィードバック
- **多言語対応**: 日本語・英語切り替え（i18n）

### エラーハンドリング
- **フォールバックコピー**: Clipboard API失敗時の代替コピー機能
- **ErrorBoundary**: Reactエラーのキャッチとユーザー通知
- **リトライ機能**: 送信失敗時の再試行

## 技術スタック

- **React 19** - UIフレームワーク
- **TypeScript** - 型安全性
- **Vite** - ビルドツール
- **Tailwind CSS** - スタイリング
- **Vitest** - テストフレームワーク
- **React Testing Library** - コンポーネントテスト

## ディレクトリ構成

```
src/
├── components/          # Reactコンポーネント
│   ├── chat/           # チャット関連コンポーネント
│   │   ├── ChatContainer.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── CopyButton.tsx
│   │   ├── FAQSuggestions.tsx
│   │   ├── MarkdownRenderer.tsx
│   │   ├── MessageFeedback.tsx
│   │   └── ToolIndicator.tsx
│   └── ErrorBoundary.tsx
├── hooks/              # カスタムフック
│   └── useChat.ts      # チャット状態管理
├── lib/                # ユーティリティ
│   ├── api.ts          # APIクライアント
│   ├── logger.ts       # 構造化ロガー
│   └── sse.ts          # SSE接続管理
├── types/              # TypeScript型定義
│   └── message.ts      # メッセージ関連型
└── i18n/               # 国際化
    └── useLanguage.tsx # 言語切り替えフック
```

## セットアップ

```bash
# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev

# テスト実行
npm test

# ビルド
npm run build
```

## 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `VITE_API_BASE_URL` | バックエンドAPIのベースURL | `http://localhost:8000` |

## テスト

```bash
# 全テスト実行
npm test

# ウォッチモード
npm test -- --watch

# カバレッジ付き
npm test -- --coverage
```

### テストカバレッジ目標
- **80%以上** のコードカバレッジ
- 重要なコンポーネントは100%を目指す

## APIエンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/api/chat` | POST | チャットメッセージ送信 |
| `/api/chat/{thread_id}/resume` | POST | 会話再開 |
| `/api/faq/suggestions` | GET | FAQサジェスト取得 |
| `/api/feedback` | POST | フィードバック送信 |

## 関連ドキュメント

- [バックエンド README](../backend/README.md)
- [プロジェクト仕様書](../docs/spec.md)
