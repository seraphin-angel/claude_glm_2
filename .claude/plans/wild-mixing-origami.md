# sample3/ CRITICAL + HIGH 修正計画 (TDD)

## Context

PR Review Toolkit の6エージェントによるレビューで、CRITICAL 2件 + HIGH 8件の問題が検出された。
TDD アプローチ (RED → GREEN → REFACTOR) で全10件を修正する。

## 修正タスク一覧

### Task 1: `handleApiError` セキュリティ修正 + エラーハンドリング拡張
**対象:** `src/lib/errors.ts`
**新規テスト:** `src/lib/errors.test.ts` (新規作成)
**問題:** CRITICAL #1 + HIGH #3

**RED — 先にテストを書く:**
```
src/lib/errors.test.ts を新規作成:
- 本番環境で内部 Error.message が漏洩しないこと (500レスポンスが汎用メッセージ)
- 開発環境では Error.message が含まれること
- ZodError → 400 + 各 issue.message を結合
- ApiError → statusCode に従うこと
- Prisma P2025 → 404
- Prisma P2002 → 409
- Prisma 未知エラー → 500 (汎用メッセージ)
- 非 Error オブジェクト → 500 (汎用メッセージ)
- console.error が 500 エラー時に呼ばれること
```

**GREEN — 最小実装:**
- `handleApiError` に `console.error` を追加 (500系のみ)
- Prisma エラーの `switch(error.code)` ハンドリング拡張
- フォールバックで `error.message` の直接漏洩を防止 (環境判定)

**REFACTOR:**
- エラーメッセージ定数の抽出

**修正後のコード方針:**
```typescript
export function handleApiError(error: unknown): NextResponse<ApiResponse<never>> {
  // ZodError → 400 (変更なし)
  // ApiError → statusCode (変更なし)
  // PrismaClientKnownRequestError → switch で P2025/P2002 等をハンドリング
  // PrismaClientInitializationError → 503
  // その他 → console.error + 汎用メッセージで 500
}
```

---

### Task 2: E2E テストのハードコード認証情報
**対象:** `e2e/todos.spec.ts:4`
**問題:** CRITICAL #2

環境変数からの取得にフォールバック付きで変更:
```typescript
const TEST_DB_URL = process.env.TEST_DATABASE_URL
  ?? 'postgresql://todouser:todopass@host.docker.internal:5433/todos_test?schema=public'
```

テスト不要 (設定変更のみ)。

---

### Task 3: `ApiResponse<T>` Discriminated Union 化
**対象:** `src/types/api.ts`
**影響ファイル:** `src/components/todos/TodoPage.tsx`, APIルートファイル
**問題:** HIGH #7

**修正内容:**
```typescript
export type ApiResponse<T> =
  | { success: true; data: T; error?: never; meta?: { total: number; page: number; limit: number } }
  | { success: false; error: string; data?: never; meta?: never }
```

**影響確認:** TypeScriptコンパイラが型チェックで全消費箇所の正しさを保証。
`TodoPage.tsx` の `json.data!` (non-null assertion) が不要になる。

---

### Task 4: DTO 型を Zod スキーマから派生
**対象:** `src/types/todo.ts`, `src/schemas/todo.ts`
**問題:** HIGH #6

**修正内容:**
```typescript
// src/types/todo.ts
import { z } from 'zod'
import { createTodoSchema, updateTodoSchema } from '@/schemas/todo'

export interface Todo { ... } // 変更なし (Prisma → API 変換後の型)

export type CreateTodoDto = z.infer<typeof createTodoSchema>
export type UpdateTodoDto = z.infer<typeof updateTodoSchema>
```

既存の `schemas/todo.test.ts` が型の正しさを保証しているため追加テスト不要。
ただし循環参照に注意: `schemas/todo.ts` が `types/todo.ts` をインポートしていないことを確認済み。

---

### Task 5: `serializeTodo` の共通化
**対象:** `src/app/api/todos/route.ts:9-15`, `src/app/api/todos/[id]/route.ts:26-30`
**新規ファイル:** `src/lib/serializers.ts`
**問題:** HIGH #8

**修正内容:**
```typescript
// src/lib/serializers.ts
import type { Todo as PrismaTodo } from '@prisma/client'
import type { Todo } from '@/types/todo'

export function serializeTodo(todo: PrismaTodo): Todo {
  return {
    ...todo,
    createdAt: todo.createdAt.toISOString(),
    updatedAt: todo.updatedAt.toISOString(),
  }
}
```

両ルートファイルから `serializeTodo` を削除し、共通モジュールからインポート。
既存の API テスト (`todos.test.ts`) で日付シリアライズがテスト済み。

---

### Task 6: TodoPage エラーハンドリング改善
**対象:** `src/components/todos/TodoPage.tsx`
**問題:** HIGH #4 (エラー未クリア) + HIGH #5 (APIメッセージ未活用)

**RED — テストを書く (既存テストに追加):**
TodoPage のユニットテストは存在しないため、エラーハンドリングは
既存の API テストの 500 パステスト (Task 1) で間接的に担保。
フロントエンドの振る舞いは手動確認 + 既存 E2E テストで担保。

**GREEN — 修正内容:**
1. 各ハンドラの先頭に `setError(null)` を追加 (エラー状態クリア)
2. `!res.ok` 時に `res.json()` のエラーメッセージを活用:
```typescript
const json: ApiResponse<Todo> = await res.json()
if (!res.ok) {
  throw new Error(json.error ?? 'タスクの作成に失敗しました')
}
```
3. `handleToggle` でAPIレスポンスデータを使って状態を更新:
```typescript
if (json.data) {
  setTodos((prev) => prev.map((t) => (t.id === id ? json.data : t)))
}
```

---

### Task 7: TodoForm エラー表示の二重解消
**対象:** `src/components/todos/TodoForm.tsx:47-57, 68-72`
**問題:** HIGH #10

**修正内容:**
`Input` コンポーネントが内部でエラーを表示するため、`TodoForm` 側の
重複エラー表示 (`<p data-testid="title-error">`) を削除。
代わりに `Input` にテスト用の `data-testid` を伝播する方法で統一:

方針: `Input` の `error` prop にテスト ID を含まないため、
`TodoForm` 側のエラー表示を残し、`Input` の `error` prop を
**ボーダー色変更のみ** に使用するよう `Input` を修正。
→ `Input.tsx` のエラーテキスト表示 (L33-37) を削除し、`error` prop は
ボーダースタイルの切り替えのみに使用。

**テスト確認:** 既存の `TodoForm.test.tsx` の `title-error` テストがパスすること。

---

### Task 8: TodoItem アクセシビリティ改善
**対象:** `src/components/todos/TodoItem.tsx`
**問題:** HIGH #9

**RED — テストを書く (既存テストに追加):**
```
src/components/todos/TodoItem.test.tsx に追加:
- チェックボックスに aria-label が設定されていること
- 削除ボタンに aria-label が設定されていること
```

**GREEN — 修正内容:**
```typescript
<input
  type="checkbox"
  aria-label={`「${todo.title}」を${todo.completed ? '未完了にする' : '完了にする'}`}
  ...
/>
<Button
  aria-label={`「${todo.title}」を削除`}
  ...
/>
```

`Button` コンポーネントの props に `aria-label` を追加。

---

## 実施順序

依存関係を考慮した実行順:

```
Phase A (型基盤 — 後続に影響):
  Task 3: ApiResponse Discriminated Union
  Task 4: DTO を Zod から派生

Phase B (バックエンド — Phase A の型を使用):
  Task 1: handleApiError セキュリティ + テスト ← 最重要
  Task 5: serializeTodo 共通化

Phase C (フロントエンド — Phase A+B の型・API を使用):
  Task 6: TodoPage エラーハンドリング
  Task 7: TodoForm エラー表示
  Task 8: TodoItem アクセシビリティ

Phase D (E2E — 最後):
  Task 2: E2E ハードコード修正
```

## 検証方法

1. `cd sample3 && npx jest --coverage` — ユニットテスト全パス + 80%以上
2. `npx tsc --noEmit` — TypeScript 型チェックエラーなし
3. `npm run build` — ビルド成功
4. 新規テスト `errors.test.ts` の全テストケースがパス
5. 既存テスト (`todos.test.ts`, `todo.test.ts`, コンポーネントテスト) が全パス
