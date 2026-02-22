# TDD修正計画: sample3/ Critical / Important / High 問題

## Context

PR Review Toolkit による6エージェントレビューの結果、Critical 3件、Important 4件、High 4件の問題が検出された。
これらをTDDアプローチ（RED → GREEN → REFACTOR）で修正する。

テーブル名は Prisma スキーマ `@@map("todos")` により **`todos`（小文字）** が正しい。

---

## 修正対象サマリー

| # | 重大度 | 問題 | ファイル |
|---|--------|------|---------|
| 1 | Critical | ハードコードDB認証情報 + テーブル名誤り | `e2e/global-setup.ts` |
| 2 | Critical | DB接続リーク（try/finally なし） | `e2e/global-setup.ts`, `e2e/todos.spec.ts` |
| 3 | Critical | TodoPage テスト皆無 | 新規: `TodoPage.test.tsx` |
| 4 | Important | console.error の本番コード混入 | `src/lib/errors.ts` |
| 5 | High | TodoForm onCreate失敗時テスト欠如 | `TodoForm.test.tsx` |
| 6 | High | isSubmitting UI状態テスト欠如 | `TodoForm.test.tsx` |
| 7 | High | serializers.ts テスト皆無 | 新規: `serializers.test.ts` |
| 8 | High | 不正JSON / DBエラーのAPIテスト欠如 | `__tests__/api/todos.test.ts` |

---

## Phase 1: E2E テストインフラ修正（Critical #1, #2）

### 対象ファイル
- `sample3/e2e/global-setup.ts`
- `sample3/e2e/todos.spec.ts`

### 変更内容

**`e2e/global-setup.ts`:**
- 環境変数 `TEST_DATABASE_URL` を使用（`todos.spec.ts` と統一）
- テーブル名を `"Todo"` → `todos` に修正（Prisma @@map に合致）
- `try/finally` で `client.end()` を保証

```typescript
import { Client } from 'pg'

const TEST_DB_URL = process.env.TEST_DATABASE_URL
  ?? 'postgresql://todouser:todopass@host.docker.internal:5433/todos_test?schema=public'

async function globalSetup() {
  const client = new Client({ connectionString: TEST_DB_URL })
  try {
    await client.connect()
    await client.query('DELETE FROM todos')
  } finally {
    await client.end()
  }
}

export default globalSetup
```

**`e2e/todos.spec.ts` の `clearDatabase` 関数:**
- `try/finally` で `client.end()` を保証

```typescript
async function clearDatabase() {
  const client = new Client({ connectionString: TEST_DB_URL })
  try {
    await client.connect()
    await client.query('DELETE FROM todos')
  } finally {
    await client.end()
  }
}
```

---

## Phase 2: Logger 抽象化（Important #4）

### TDD: RED → GREEN → REFACTOR

**RED** - テストを先に書く:
- 新規: `sample3/src/lib/logger.ts`
- 新規: `sample3/src/lib/logger.test.ts`

**logger.test.ts:**
```typescript
// logger.error が console.error に委譲することを確認
// logger.warn が console.warn に委譲することを確認
```

**GREEN** - 最小実装:

**`sample3/src/lib/logger.ts`:**
```typescript
export const logger = {
  error: (...args: unknown[]) => console.error(...args),
  warn: (...args: unknown[]) => console.warn(...args),
}
```

**REFACTOR** - `errors.ts` を更新:
- `console.error(...)` → `logger.error(...)` に3箇所置換
- `errors.test.ts` の `jest.spyOn(console, 'error')` → `jest.spyOn(logger, 'error')` に更新
- `import { logger } from '@/lib/logger'` を追加

### 対象ファイル
- 新規: `sample3/src/lib/logger.ts`
- 新規: `sample3/src/lib/logger.test.ts`
- 修正: `sample3/src/lib/errors.ts` (3箇所の console.error を logger.error に)
- 修正: `sample3/src/lib/errors.test.ts` (spyOn 対象を logger に変更)

---

## Phase 3: serializers.ts テスト作成（High #7）

### TDD: RED → GREEN（実装は既存）

**新規: `sample3/src/lib/serializers.test.ts`:**

```typescript
import { serializeTodo } from './serializers'

describe('serializeTodo', () => {
  it('Date を ISO 文字列に変換する', () => {
    const prismaTodo = {
      id: 'cltest123',
      title: 'Test',
      completed: false,
      createdAt: new Date('2026-01-01T00:00:00.000Z'),
      updatedAt: new Date('2026-01-02T00:00:00.000Z'),
    }
    const result = serializeTodo(prismaTodo)
    expect(result.createdAt).toBe('2026-01-01T00:00:00.000Z')
    expect(result.updatedAt).toBe('2026-01-02T00:00:00.000Z')
    expect(typeof result.createdAt).toBe('string')
  })

  it('id, title, completed をそのまま保持する', () => {
    const prismaTodo = {
      id: 'cltest456',
      title: 'Preserve fields',
      completed: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    }
    const result = serializeTodo(prismaTodo)
    expect(result.id).toBe('cltest456')
    expect(result.title).toBe('Preserve fields')
    expect(result.completed).toBe(true)
  })
})
```

実装は既存で正しいため、テストは即 GREEN になる。

---

## Phase 4: TodoForm テスト補強（High #5, #6）

### 対象ファイル
- 修正: `sample3/src/components/todos/TodoForm.test.tsx`

### 追加テストケース

```typescript
it('onCreate が失敗した場合、入力値がクリアされない', async () => {
  const onCreate = jest.fn().mockRejectedValue(new Error('API Error'))
  render(<TodoForm onCreate={onCreate} />)
  await userEvent.type(screen.getByTestId('todo-input'), '失敗するタスク')
  await userEvent.click(screen.getByTestId('add-todo-button'))
  await waitFor(() => {
    expect(screen.getByTestId('todo-input')).toHaveValue('失敗するタスク')
    expect(screen.getByTestId('add-todo-button')).not.toBeDisabled()
  })
})

it('送信中はボタンとインプットが無効化される', async () => {
  let resolveCreate!: () => void
  const onCreate = jest.fn().mockImplementation(
    () => new Promise<void>((resolve) => { resolveCreate = resolve })
  )
  render(<TodoForm onCreate={onCreate} />)
  await userEvent.type(screen.getByTestId('todo-input'), 'テスト')
  await userEvent.click(screen.getByTestId('add-todo-button'))
  expect(screen.getByTestId('add-todo-button')).toBeDisabled()
  expect(screen.getByTestId('todo-input')).toBeDisabled()
  // cleanup
  resolveCreate()
})

it('バリデーションエラー後に入力するとエラーが消える', async () => {
  render(<TodoForm onCreate={jest.fn()} />)
  await userEvent.click(screen.getByTestId('add-todo-button'))
  expect(screen.getByTestId('title-error')).toBeInTheDocument()
  await userEvent.type(screen.getByTestId('todo-input'), 'a')
  expect(screen.queryByTestId('title-error')).not.toBeInTheDocument()
})
```

---

## Phase 5: API テスト補強（High #8）

### 対象ファイル
- 修正: `sample3/src/__tests__/api/todos.test.ts`

### 追加テストケース

```typescript
// GET: DBエラー時
it('データベースエラー時に500を返す', async () => {
  ;(mockPrisma.todo.findMany as jest.Mock).mockRejectedValue(
    new Error('Connection refused')
  )
  const req = new NextRequest('http://localhost/api/todos')
  const res = await GET(req)
  expect(res.status).toBe(500)
  const body = await res.json()
  expect(body.success).toBe(false)
})

// POST: 不正JSONボディ
it('不正なJSONボディで500を返す', async () => {
  const req = new NextRequest('http://localhost/api/todos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: 'invalid json{{',
  })
  const res = await POST(req)
  expect(res.status).toBe(500)
  const body = await res.json()
  expect(body.success).toBe(false)
})
```

---

## Phase 6: TodoPage テスト作成（Critical #3）

### TDD: RED → GREEN（実装は既存）

### 対象ファイル
- 新規: `sample3/src/components/todos/TodoPage.test.tsx`

### テスト戦略
- `global.fetch` をモックして API レスポンスをシミュレート
- テスト環境: jsdom（デフォルト）
- 既存テストのパターン（`userEvent`, `waitFor`, `screen.getByTestId`）に準拠

### テストケース一覧

```typescript
/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TodoPage from './TodoPage'

const mockTodo = {
  id: '1', title: 'Test', completed: false,
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
}

beforeEach(() => {
  jest.restoreAllMocks()
})

describe('TodoPage', () => {
  // 初期ロード
  it('ロード中にスピナーが表示される', ...)
  it('正常ロード後にTodoリストが表示される', ...)
  it('APIエラー時にエラーメッセージが表示される', ...)
  it('ネットワークエラー時にフォールバックメッセージが表示される', ...)

  // 作成
  it('新しいTodoを作成するとリストに追加される', ...)
  it('作成失敗時にエラーが表示される', ...)

  // トグル
  it('チェックボックスのトグルでcompletedが反転する', ...)
  it('トグル失敗時にエラーが表示される', ...)

  // 削除
  it('削除するとリストから除外される', ...)
  it('削除失敗時にエラーが表示される', ...)
})
```

各テストは `global.fetch = jest.fn()` でモックし、`mockResolvedValueOnce` / `mockRejectedValueOnce` でレスポンスを制御する。

---

## 検証手順

### 1. ユニットテスト実行
```bash
cd sample3 && npm test
```
全テストが PASS し、カバレッジ 80%+ を確認。

### 2. 個別テスト確認
```bash
npx jest src/lib/logger.test.ts
npx jest src/lib/serializers.test.ts
npx jest src/lib/errors.test.ts
npx jest src/components/todos/TodoForm.test.tsx
npx jest src/components/todos/TodoPage.test.tsx
npx jest src/__tests__/api/todos.test.ts
```

### 3. TypeScript ビルド確認
```bash
npx tsc --noEmit
```

### 4. console.error 残存確認
`src/lib/errors.ts` に `console.error` が残っていないことを grep で確認。

---

## ファイル変更一覧

| 操作 | ファイル |
|------|---------|
| 修正 | `sample3/e2e/global-setup.ts` |
| 修正 | `sample3/e2e/todos.spec.ts` |
| 新規 | `sample3/src/lib/logger.ts` |
| 新規 | `sample3/src/lib/logger.test.ts` |
| 修正 | `sample3/src/lib/errors.ts` |
| 修正 | `sample3/src/lib/errors.test.ts` |
| 新規 | `sample3/src/lib/serializers.test.ts` |
| 修正 | `sample3/src/components/todos/TodoForm.test.tsx` |
| 新規 | `sample3/src/components/todos/TodoPage.test.tsx` |
| 修正 | `sample3/src/__tests__/api/todos.test.ts` |
