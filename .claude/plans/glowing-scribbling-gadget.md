# TDD修正計画: sample3 Critical/High 問題対応

## Context

コードレビュー（6つの専門エージェントによる並列分析）で発見された Critical 2件 / High 5件の問題を TDD アプローチで修正する。H-5（Rate Limiting）はミドルウェア設計が必要で今回のスコープ外とする。

## 実施順序

依存関係を考慮した順序:

```
C-2 (Prisma設定) → H-3 (スキーマ共通化) → H-4 (Prismaエラー処理) → H-2 (不正JSON→400) → H-1 (idバリデーション) → C-1 (catchブロック)
```

---

## 修正 C-2: prisma/schema.prisma — url 欠落

**ファイル:** `prisma/schema.prisma`
**テスト:** 不要（設定変更のみ）

```diff
 datasource db {
   provider = "postgresql"
+  url      = env("DATABASE_URL")
 }
```

---

## 修正 H-3: スキーマ共通化 + バリデーション不一致修正

### 変更ファイル
- `src/schemas/todo.ts` — `titleSchema` を共通抽出
- `src/components/todos/TodoForm.tsx` — `validate` で `title.trim().length > 500` に修正

### テストファイル
- `src/schemas/todo.test.ts` — `titleSchema` テスト追加
- `src/components/todos/TodoForm.test.tsx` — trim境界値テスト追加

### TDDサイクル

**RED:** `titleSchema` のimportが存在しないため失敗するテストを追加

```typescript
// src/schemas/todo.test.ts に追加
import { titleSchema } from './todo'

describe('titleSchema', () => {
  it('titleSchema がエクスポートされている', () => {
    expect(titleSchema).toBeDefined()
  })
  it('trim後に500文字ちょうどは許可する', () => {
    const result = titleSchema.parse(' ' + 'a'.repeat(500))
    expect(result).toHaveLength(500)
  })
})
```

**GREEN:** `src/schemas/todo.ts` を修正

```typescript
export const titleSchema = z.string()
  .trim()
  .min(1, 'Title is required')
  .max(500, 'Title cannot exceed 500 characters')

export const createTodoSchema = z.object({ title: titleSchema })

export const updateTodoSchema = z.object({
  title: titleSchema.optional(),
  completed: z.boolean().optional()
}).refine(
  (data) => data.title !== undefined || data.completed !== undefined,
  { message: 'At least one field must be provided' }
)
```

**TodoForm.tsx の validate 修正:**
```diff
-    if (title.length > 500) {
+    if (title.trim().length > 500) {
```

**REFACTOR:** 既存26テスト全パスを確認

---

## 修正 H-4: errors.ts — Prismaエラークラス追加対応

### 変更ファイル
- `src/lib/errors.ts` — `PrismaClientInitializationError` / `PrismaClientValidationError` ハンドラー追加

### テストファイル
- `src/lib/errors.test.ts` — 2テスト追加

### Prismaコンストラクタシグネチャ（実機確認済み）
- `PrismaClientInitializationError(message: string, clientVersion: string, errorCode?: string)`
- `PrismaClientValidationError(message: string, { clientVersion }: Options)`

### TDDサイクル

**RED:** テスト追加

```typescript
// src/lib/errors.test.ts に追加
it('returns 503 for PrismaClientInitializationError', async () => {
  const error = new Prisma.PrismaClientInitializationError(
    "Can't reach database server", '7.4.0'
  )
  const res = handleApiError(error)
  const body = await res.json()
  expect(res.status).toBe(503)
  expect(body.success).toBe(false)
  expect(body.error).toBe('Database is currently unavailable')
  expect(body.error).not.toContain('database server')
  expect(logger.error).toHaveBeenCalled()
})

it('returns 500 for PrismaClientValidationError', async () => {
  const error = new Prisma.PrismaClientValidationError(
    'Invalid prisma.todo.findMany() call', { clientVersion: '7.4.0' }
  )
  const res = handleApiError(error)
  const body = await res.json()
  expect(res.status).toBe(500)
  expect(body.success).toBe(false)
  expect(body.error).toBe('A database error occurred')
  expect(logger.error).toHaveBeenCalled()
})
```

**GREEN:** `src/lib/errors.ts` の `PrismaClientKnownRequestError` ハンドラーの後に追加

```typescript
if (error instanceof Prisma.PrismaClientInitializationError) {
  logger.error('[Prisma Init Error]', error.errorCode, error.message)
  return NextResponse.json(
    { success: false, error: 'Database is currently unavailable' },
    { status: 503 }
  )
}

if (error instanceof Prisma.PrismaClientValidationError) {
  logger.error('[Prisma Validation Error]', error.message)
  return NextResponse.json(
    { success: false, error: 'A database error occurred' },
    { status: 500 }
  )
}
```

---

## 修正 H-2: 不正JSON → 400 を返す

### 変更ファイル
- `src/lib/errors.ts` — `SyntaxError` ハンドラー追加

### テストファイル
- `src/lib/errors.test.ts` — SyntaxError テスト追加
- `src/__tests__/api/todos.test.ts` — 既存テスト修正 (500→400)

### TDDサイクル

**RED:** テスト修正＋追加

```typescript
// src/__tests__/api/todos.test.ts 既存テスト修正
it('returns 400 for invalid JSON body', async () => {
  const req = new NextRequest('http://localhost/api/todos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: 'invalid json{{',
  })
  const res = await POST(req)
  const body = await res.json()
  expect(res.status).toBe(400)
  expect(body.success).toBe(false)
  expect(body.error).toContain('Invalid JSON')
})

// src/lib/errors.test.ts に追加
it('returns 400 for SyntaxError (invalid JSON)', async () => {
  const res = handleApiError(new SyntaxError('Unexpected token'))
  const body = await res.json()
  expect(res.status).toBe(400)
  expect(body.success).toBe(false)
  expect(body.error).toContain('Invalid JSON')
  expect(logger.error).not.toHaveBeenCalled()
})
```

**GREEN:** `src/lib/errors.ts` の `ZodError` ハンドラー直後に追加

```typescript
if (error instanceof SyntaxError) {
  return NextResponse.json(
    { success: false, error: 'Invalid JSON in request body' },
    { status: 400 }
  )
}
```

---

## 修正 H-1: [id]/route.ts — idバリデーション

### 変更ファイル
- `src/schemas/todo.ts` — `idSchema` 追加
- `src/app/api/todos/[id]/route.ts` — `idSchema.parse(id)` 追加

### テストファイル
- `src/schemas/todo.test.ts` — idSchema テスト4件追加
- `src/__tests__/api/todos.test.ts` — PUT/DELETE の id不正テスト3件追加

### TDDサイクル

**RED:** テスト追加

```typescript
// src/schemas/todo.test.ts に追加
import { idSchema } from './todo'

describe('idSchema', () => {
  it('accepts a valid cuid', () => {
    expect(() => idSchema.parse('cltest123456789')).not.toThrow()
  })
  it('rejects an empty string', () => {
    expect(() => idSchema.parse('')).toThrow()
  })
  it('rejects path traversal characters', () => {
    expect(() => idSchema.parse('../../etc')).toThrow()
  })
  it('rejects strings over 128 characters', () => {
    expect(() => idSchema.parse('a'.repeat(129))).toThrow()
  })
})

// src/__tests__/api/todos.test.ts に追加 (PUT)
it('returns 400 for empty id', async () => {
  const req = new NextRequest('http://localhost/api/todos/', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Updated' }),
  })
  const res = await PUT(req, { params: Promise.resolve({ id: '' }) })
  const body = await res.json()
  expect(res.status).toBe(400)
  expect(body.success).toBe(false)
  expect(mockPrisma.todo.update).not.toHaveBeenCalled()
})

it('returns 400 for id with invalid characters', async () => {
  const req = new NextRequest('http://localhost/api/todos/bad', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Updated' }),
  })
  const res = await PUT(req, { params: Promise.resolve({ id: '../../etc/passwd' }) })
  const body = await res.json()
  expect(res.status).toBe(400)
  expect(mockPrisma.todo.update).not.toHaveBeenCalled()
})

// src/__tests__/api/todos.test.ts に追加 (DELETE)
it('returns 400 for empty id', async () => {
  const req = new NextRequest('http://localhost/api/todos/', { method: 'DELETE' })
  const res = await DELETE(req, { params: Promise.resolve({ id: '' }) })
  const body = await res.json()
  expect(res.status).toBe(400)
  expect(mockPrisma.todo.delete).not.toHaveBeenCalled()
})
```

**GREEN:**

`src/schemas/todo.ts` に追加:
```typescript
export const idSchema = z.string()
  .min(1, 'ID is required')
  .max(128, 'ID is too long')
  .regex(/^[a-zA-Z0-9_-]+$/, 'ID contains invalid characters')
```

`src/app/api/todos/[id]/route.ts` の PUT/DELETE に追加:
```typescript
import { idSchema, updateTodoSchema } from '@/schemas/todo'

// PUT/DELETE 各ハンドラーの params 取得直後に:
const validatedId = idSchema.parse(id)
// where: { id: validatedId } を使用
```

---

## 修正 C-1: TodoForm.tsx — catchブロックでエラー表示

### 変更ファイル
- `src/components/todos/TodoForm.tsx` — catch 内で `setError` を呼ぶ

### テストファイル
- `src/components/todos/TodoForm.test.tsx` — エラー表示テスト追加

### TDDサイクル

**RED:** テスト追加

```typescript
it('onCreate が失敗した場合、フォーム内にエラーメッセージが表示される', async () => {
  const onCreate = jest.fn().mockRejectedValue(new Error('サーバーエラー'))
  render(<TodoForm onCreate={onCreate} />)
  await userEvent.type(screen.getByTestId('todo-input'), '失敗タスク')
  await userEvent.click(screen.getByTestId('add-todo-button'))
  await waitFor(() => {
    expect(screen.getByTestId('title-error')).toHaveTextContent('サーバーエラー')
  })
})
```

**GREEN:** `src/components/todos/TodoForm.tsx` の catch ブロック修正

```diff
-    } catch {
-      // Error display is handled by the caller (e.g. TodoPage)
+    } catch (err) {
+      const message = err instanceof Error ? err.message : '送信に失敗しました'
+      setError(message)
     } finally {
```

**既存テスト影響:** `TodoPage.handleCreate` は内部で try/catch して再スローしないため、TodoForm の catch には到達しない。`TodoPage.test.tsx` のテストは変更不要。

---

## 変更ファイルまとめ

| ファイル | 修正ID | 変更内容 |
|---------|--------|---------|
| `prisma/schema.prisma` | C-2 | `url = env("DATABASE_URL")` 追加 |
| `src/schemas/todo.ts` | H-3, H-1 | `titleSchema` 共通化 + `idSchema` 追加 |
| `src/lib/errors.ts` | H-4, H-2 | Prismaエラー2種 + SyntaxError ハンドラー追加 |
| `src/app/api/todos/[id]/route.ts` | H-1 | `idSchema.parse(id)` 追加 |
| `src/components/todos/TodoForm.tsx` | H-3, C-1 | trim修正 + catch内エラー表示 |

## テスト追加まとめ

| テストファイル | 新規 | 修正 |
|--------------|------|------|
| `src/schemas/todo.test.ts` | +6 (titleSchema 2 + idSchema 4) | 0 |
| `src/lib/errors.test.ts` | +3 (InitError, ValidationError, SyntaxError) | 0 |
| `src/__tests__/api/todos.test.ts` | +3 (PUT id空/不正, DELETE id空) | 1 (500→400修正) |
| `src/components/todos/TodoForm.test.tsx` | +2 (エラー表示, trim境界値) | 0 |
| **合計** | **+14** | **1** |

## 検証手順

各修正後に:
```bash
cd /workspace/sample3 && npx jest --passWithNoTests
```

全修正完了後にカバレッジ確認:
```bash
cd /workspace/sample3 && npx jest --coverage
```

80%以上のカバレッジ閾値をクリアすることを確認。
