import { test, expect } from '@playwright/test'
import { Client } from 'pg'

const TEST_DB_URL = process.env.TEST_DATABASE_URL
  ?? 'postgresql://todouser:todopass@host.docker.internal:5433/todos_test?schema=public'

async function clearDatabase() {
  const client = new Client({ connectionString: TEST_DB_URL })
  try {
    await client.connect()
    await client.query('DELETE FROM todos')
  } finally {
    await client.end()
  }
}

test.beforeEach(async () => {
  await clearDatabase()
})

// ─── ページロード ─────────────────────────────────────────────────────────────

test.describe('ページロード', () => {
  test('Todoアプリのページが表示される', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('ToDo App')).toBeVisible()
    await expect(page.getByTestId('todo-input')).toBeVisible()
    await expect(page.getByTestId('add-todo-button')).toBeVisible()
  })

  test('初期状態では空のリストメッセージが表示される', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('empty-state')).toBeVisible()
    await expect(page.getByTestId('empty-state')).toContainText('タスクがありません')
  })
})

// ─── タスク追加 ───────────────────────────────────────────────────────────────

test.describe('タスク追加', () => {
  test('新しいタスクを追加できる', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('E2E テストタスク')
    await page.getByTestId('add-todo-button').click()
    
    await expect(page.getByTestId('todo-list')).toBeVisible()
    await expect(page.getByTestId('todo-title').first()).toContainText('E2E テストタスク')
  })

  test('空のタイトルでは追加できない', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('add-todo-button').click()
    
    await expect(page.getByTestId('title-error')).toBeVisible()
    await expect(page.getByTestId('title-error')).toContainText('タイトルを入力してください')
    await expect(page.getByTestId('todo-list')).not.toBeVisible()
  })

  test('追加後に入力フィールドがクリアされる', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('クリアされるタスク')
    await page.getByTestId('add-todo-button').click()
    
    await expect(page.getByTestId('todo-title').first()).toContainText('クリアされるタスク')
    await expect(page.getByTestId('todo-input')).toHaveValue('')
  })

  test('複数のタスクを追加できる', async ({ page }) => {
    await page.goto('/')
    
    for (const title of ['タスク A', 'タスク B', 'タスク C']) {
      await page.getByTestId('todo-input').fill(title)
      await page.getByTestId('add-todo-button').click()
      await expect(page.getByTestId('todo-title').first()).toContainText(title)
    }
    
    await expect(page.getByTestId('todo-item')).toHaveCount(3)
  })
})

// ─── タスク完了切り替え ───────────────────────────────────────────────────────

test.describe('タスク完了切り替え', () => {
  test('チェックボックスでタスクを完了にできる', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('完了テストタスク')
    await page.getByTestId('add-todo-button').click()
    await expect(page.getByTestId('todo-title').first()).toBeVisible()
    
    const checkbox = page.getByTestId('todo-checkbox').first()
    await expect(checkbox).not.toBeChecked()
    await checkbox.click()
    await expect(checkbox).toBeChecked()
    
    const title = page.getByTestId('todo-title').first()
    await expect(title).toHaveClass(/line-through/)
  })

  test('完了したタスクを未完了に戻せる', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('未完了に戻すタスク')
    await page.getByTestId('add-todo-button').click()
    await expect(page.getByTestId('todo-title').first()).toBeVisible()
    
    const checkbox = page.getByTestId('todo-checkbox').first()
    await checkbox.click()
    await expect(checkbox).toBeChecked()
    
    await checkbox.click()
    await expect(checkbox).not.toBeChecked()
    
    const title = page.getByTestId('todo-title').first()
    await expect(title).not.toHaveClass(/line-through/)
  })
})

// ─── タスク削除 ───────────────────────────────────────────────────────────────

test.describe('タスク削除', () => {
  test('削除ボタンでタスクを削除できる', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('削除するタスク')
    await page.getByTestId('add-todo-button').click()
    await expect(page.getByTestId('todo-item')).toHaveCount(1)
    
    await page.getByTestId('delete-button').first().click()
    
    await expect(page.getByTestId('todo-item')).toHaveCount(0)
    await expect(page.getByTestId('empty-state')).toBeVisible()
  })

  test('複数タスクのうち1つだけ削除できる', async ({ page }) => {
    await page.goto('/')
    
    for (const title of ['削除しないタスク', '削除するタスク']) {
      await page.getByTestId('todo-input').fill(title)
      await page.getByTestId('add-todo-button').click()
      await expect(page.getByTestId('todo-title').first()).toContainText(title)
    }
    
    await expect(page.getByTestId('todo-item')).toHaveCount(2)
    
    // 最初のアイテム（最新 = '削除するタスク'）を削除
    await page.getByTestId('delete-button').first().click()
    
    await expect(page.getByTestId('todo-item')).toHaveCount(1)
    await expect(page.getByTestId('todo-title').first()).toContainText('削除しないタスク')
  })
})

// ─── ページリロード後の永続性 ─────────────────────────────────────────────────

test.describe('データ永続性', () => {
  test('ページリロード後もタスクが保持される', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('永続タスク')
    await page.getByTestId('add-todo-button').click()
    await expect(page.getByTestId('todo-title').first()).toContainText('永続タスク')
    
    await page.reload()
    
    await expect(page.getByTestId('todo-list')).toBeVisible()
    await expect(page.getByTestId('todo-title').first()).toContainText('永続タスク')
  })

  test('完了状態がリロード後も保持される', async ({ page }) => {
    await page.goto('/')
    
    await page.getByTestId('todo-input').fill('完了永続タスク')
    await page.getByTestId('add-todo-button').click()
    await expect(page.getByTestId('todo-title').first()).toBeVisible()
    
    await page.getByTestId('todo-checkbox').first().click()
    await expect(page.getByTestId('todo-checkbox').first()).toBeChecked()
    
    await page.reload()
    
    await expect(page.getByTestId('todo-checkbox').first()).toBeChecked()
  })
})
