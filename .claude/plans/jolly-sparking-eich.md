# Next.js + Prisma + PostgreSQL ToDo アプリ構築プラン

## Context

`/workspace/sample3/` に Next.js App Router + Prisma ORM + PostgreSQL による ToDo アプリの雛形を構築する。CRUD API（GET/POST/PUT/DELETE）、フロントエンド（一覧・追加・完了切替・削除）、Prisma スキーマ・マイグレーション、基本テストを含む。Agent Teams による並列作業で効率的に実装する。

---

## プロジェクト構成

```
/workspace/sample3/
├── docker-compose.yml
├── .env / .env.example
├── package.json
├── tsconfig.json
├── next.config.ts
├── jest.config.ts / jest.setup.ts
├── playwright.config.ts
├── prisma/
│   └── schema.prisma
├── src/
│   ├── lib/
│   │   ├── prisma.ts          # Prisma クライアント（シングルトン）
│   │   └── errors.ts          # ApiError + handleApiError
│   ├── types/
│   │   ├── api.ts             # ApiResponse<T> インターフェース
│   │   └── todo.ts            # Todo 型定義 + DTO
│   ├── schemas/
│   │   └── todo.ts            # Zod バリデーションスキーマ
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── api/todos/
│   │       ├── route.ts       # GET + POST
│   │       └── [id]/
│   │           └── route.ts   # PUT + DELETE
│   └── components/
│       ├── todos/
│       │   ├── TodoPage.tsx   # メインコンテナ（状態管理）
│       │   ├── TodoList.tsx   # 一覧表示
│       │   ├── TodoItem.tsx   # 個別アイテム（トグル+削除）
│       │   └── TodoForm.tsx   # 追加フォーム
│       └── ui/
│           ├── Button.tsx
│           ├── Input.tsx
│           ├── Spinner.tsx
│           └── ErrorMessage.tsx
└── e2e/
    └── todos.spec.ts          # E2E テスト
```

---

## データベーススキーマ

```prisma
model Todo {
  id          String   @id @default(cuid())
  title       String
  completed   Boolean  @default(false)
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt @map("updated_at")
  @@map("todos")
}
```

---

## API 設計

全エンドポイントは `ApiResponse<T>` 形式で返す:

```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: { total: number; page: number; limit: number }
}
```

| Method | Path | 説明 | バリデーション |
|--------|------|------|------------|
| GET | `/api/todos` | 一覧取得（ページネーション対応） | `page`, `limit`, `completed` クエリパラメータ |
| POST | `/api/todos` | 新規作成 | `title`: 1〜500文字、trim |
| PUT | `/api/todos/[id]` | 更新（タイトル or 完了状態） | `title` or `completed` の少なくとも1つ必須 |
| DELETE | `/api/todos/[id]` | 削除 | ID存在チェック → 404 |

---

## Agent Teams 作業分担

### フェーズ 0: 共通セットアップ（ワーカーA が担当）

1. `sample3/` ディレクトリ作成 + Next.js プロジェクト初期化（`create-next-app`）
2. `docker-compose.yml` 作成（PostgreSQL × 2: 開発用 + テスト用）
3. `.env` / `.env.example` 作成
4. Prisma 初期化 + スキーマ定義 + マイグレーション実行
5. 共有型定義: `src/types/api.ts`, `src/types/todo.ts`
6. Zod スキーマ: `src/schemas/todo.ts`
7. ユーティリティ: `src/lib/prisma.ts`, `src/lib/errors.ts`
8. Zod, テスト関連の依存パッケージインストール

### フェーズ 1: 並列実装

#### ワーカーA（API）— `general-purpose` / `sonnet`
- `src/app/api/todos/route.ts` — GET（ページネーション+フィルタ）+ POST
- `src/app/api/todos/[id]/route.ts` — PUT + DELETE
- API の基本テスト

#### ワーカーB（フロントエンド）— `general-purpose` / `sonnet`
- UI コンポーネント: `Button`, `Input`, `Spinner`, `ErrorMessage`
- ToDo コンポーネント: `TodoPage`, `TodoList`, `TodoItem`, `TodoForm`
- `page.tsx` / `layout.tsx` の更新
- コンポーネントの基本テスト

### フェーズ 2: レビュー + E2E テスト

#### レビュワー — `code-reviewer` / `sonnet`
- Playwright セットアップ + E2E テスト作成・実行
- コード品質チェック（イミュータビリティ、console.log、ハードコード値、ネスト深度）
- `npm run lint` + `npm run build` による最終確認

---

## 主要な設計方針

- **イミュータビリティ**: 全状態更新は `setTodos(prev => [...prev])` パターン
- **Zod バリデーション**: 全入力を `createTodoSchema` / `updateTodoSchema` で検証
- **エラーハンドリング**: `ApiError` クラス + `handleApiError` で統一的なエラーレスポンス
- **ファイルサイズ**: 各ファイル 200〜400 行、最大 800 行
- **console.log 禁止**: 構造化ロガーを使用

---

## 検証手順

1. **インフラ**: `docker compose up -d` → PostgreSQL ヘルスチェック
2. **DB**: `npx prisma migrate status` → スキーマ反映確認
3. **API**: curl で CRUD 操作 + バリデーションエラー + 404 を確認
4. **テスト**: `npm test` → 全テスト PASS、カバレッジ 80%+
5. **E2E**: `npm run test:e2e` → 全シナリオ PASS
6. **ビルド**: `npm run build` → エラー 0
7. **ブラウザ**: `http://localhost:3000` で手動操作確認

---

## 修正対象ファイル一覧

全て新規作成（`/workspace/sample3/` は存在しない）:

- `docker-compose.yml` — PostgreSQL コンテナ定義
- `prisma/schema.prisma` — Todo モデル定義
- `src/lib/prisma.ts` — Prisma クライアントシングルトン
- `src/lib/errors.ts` — エラーハンドリングユーティリティ
- `src/types/api.ts` — ApiResponse<T> 型定義
- `src/types/todo.ts` — Todo 型 + DTO 定義
- `src/schemas/todo.ts` — Zod バリデーションスキーマ
- `src/app/api/todos/route.ts` — GET + POST ハンドラ
- `src/app/api/todos/[id]/route.ts` — PUT + DELETE ハンドラ
- `src/components/todos/TodoPage.tsx` — メインコンテナ
- `src/components/todos/TodoList.tsx` — 一覧コンポーネント
- `src/components/todos/TodoItem.tsx` — アイテムコンポーネント
- `src/components/todos/TodoForm.tsx` — フォームコンポーネント
- `src/components/ui/Button.tsx` — 汎用ボタン
- `src/components/ui/Input.tsx` — 汎用入力
- `src/components/ui/Spinner.tsx` — ローディング表示
- `src/components/ui/ErrorMessage.tsx` — エラー表示
- `e2e/todos.spec.ts` — E2E テスト
