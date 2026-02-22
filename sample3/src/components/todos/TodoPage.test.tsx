/**
 * @jest-environment jsdom
 */
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoPage } from './TodoPage'

const mockTodo = {
  id: '1',
  title: 'Test Todo',
  completed: false,
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
}

const mockTodo2 = {
  id: '2',
  title: 'Second Todo',
  completed: true,
  createdAt: '2026-01-02T00:00:00.000Z',
  updatedAt: '2026-01-02T00:00:00.000Z',
}

function mockFetchSuccess(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  })
}

function mockFetchFailure(error: string, status = 500) {
  return Promise.resolve({
    ok: false,
    status,
    json: () => Promise.resolve({ success: false, error }),
  })
}

beforeEach(() => {
  jest.restoreAllMocks()
})

describe('TodoPage', () => {
  // ─── 初期ロード ───────────────────────────────────────────────────────────

  it('ロード中にスピナーが表示される', () => {
    global.fetch = jest.fn().mockImplementation(
      () => new Promise(() => {})
    )
    render(<TodoPage />)
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
  })

  it('正常ロード後にTodoリストが表示される', async () => {
    global.fetch = jest.fn().mockImplementation(() =>
      mockFetchSuccess({ success: true, data: [mockTodo], meta: { total: 1, page: 1, limit: 20 } })
    )
    render(<TodoPage />)

    await waitFor(() => {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
    })
    expect(screen.getByText('Test Todo')).toBeInTheDocument()
  })

  it('空のリストではempty stateが表示される', async () => {
    global.fetch = jest.fn().mockImplementation(() =>
      mockFetchSuccess({ success: true, data: [], meta: { total: 0, page: 1, limit: 20 } })
    )
    render(<TodoPage />)

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    })
  })

  it('APIエラー時にエラーメッセージが表示される', async () => {
    global.fetch = jest.fn().mockImplementation(() =>
      mockFetchFailure('サーバーエラー')
    )
    render(<TodoPage />)

    await waitFor(() => {
      expect(screen.getByTestId('page-error')).toBeInTheDocument()
      expect(screen.getByTestId('page-error')).toHaveTextContent('サーバーエラー')
    })
  })

  it('ネットワークエラー時にフォールバックメッセージが表示される', async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    render(<TodoPage />)

    await waitFor(() => {
      expect(screen.getByTestId('page-error')).toBeInTheDocument()
      expect(screen.getByTestId('page-error')).toHaveTextContent('Failed to fetch')
    })
  })

  // ─── 作成 ─────────────────────────────────────────────────────────────────

  it('新しいTodoを作成するとリストに追加される', async () => {
    const createdTodo = { ...mockTodo, id: '99', title: '新規タスク' }
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [], meta: { total: 0, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: createdTodo }, 201)
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
    })

    await userEvent.type(screen.getByTestId('todo-input'), '新規タスク')
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(screen.getByText('新規タスク')).toBeInTheDocument()
    })
  })

  it('作成失敗時にエラーが表示される', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [], meta: { total: 0, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchFailure('作成に失敗しました')
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument()
    })

    await userEvent.type(screen.getByTestId('todo-input'), '失敗タスク')
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(screen.getByTestId('page-error')).toHaveTextContent('作成に失敗しました')
    })
  })

  // ─── トグル ───────────────────────────────────────────────────────────────

  it('チェックボックスのトグルでcompletedが反転する', async () => {
    const toggledTodo = { ...mockTodo, completed: true }
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [mockTodo], meta: { total: 1, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: toggledTodo })
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Todo')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByTestId('todo-checkbox'))

    await waitFor(() => {
      expect(screen.getByTestId('todo-checkbox')).toBeChecked()
    })
  })

  it('トグル失敗時にエラーが表示される', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [mockTodo], meta: { total: 1, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchFailure('更新に失敗しました')
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Todo')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByTestId('todo-checkbox'))

    await waitFor(() => {
      expect(screen.getByTestId('page-error')).toHaveTextContent('更新に失敗しました')
    })
  })

  // ─── 削除 ─────────────────────────────────────────────────────────────────

  it('削除するとリストから除外される', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [mockTodo, mockTodo2], meta: { total: 2, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: null })
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Todo')).toBeInTheDocument()
      expect(screen.getByText('Second Todo')).toBeInTheDocument()
    })

    const firstItem = screen.getAllByTestId('todo-item')[0]
    await userEvent.click(within(firstItem).getByTestId('delete-button'))

    await waitFor(() => {
      expect(screen.queryByText('Test Todo')).not.toBeInTheDocument()
      expect(screen.getByText('Second Todo')).toBeInTheDocument()
    })
  })

  it('削除失敗時にエラーが表示される', async () => {
    global.fetch = jest.fn()
      .mockImplementationOnce(() =>
        mockFetchSuccess({ success: true, data: [mockTodo], meta: { total: 1, page: 1, limit: 20 } })
      )
      .mockImplementationOnce(() =>
        mockFetchFailure('削除に失敗しました')
      )

    render(<TodoPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Todo')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByTestId('delete-button'))

    await waitFor(() => {
      expect(screen.getByTestId('page-error')).toHaveTextContent('削除に失敗しました')
    })
  })
})
