import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoForm } from './TodoForm'

describe('TodoForm', () => {
  it('入力とボタンが表示されること', () => {
    render(<TodoForm onCreate={jest.fn()} />)
    expect(screen.getByTestId('todo-input')).toBeInTheDocument()
    expect(screen.getByTestId('add-todo-button')).toBeInTheDocument()
  })

  it('有効な入力で onCreate が呼ばれること', async () => {
    const onCreate = jest.fn().mockResolvedValue(undefined)
    render(<TodoForm onCreate={onCreate} />)

    await userEvent.type(screen.getByTestId('todo-input'), 'テストタスク')
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('テストタスク')
    })
  })

  it('空文字列でバリデーションエラーが表示されること', async () => {
    render(<TodoForm onCreate={jest.fn()} />)

    await userEvent.click(screen.getByTestId('add-todo-button'))

    expect(screen.getByTestId('title-error')).toBeInTheDocument()
  })

  it('送信成功後にフォームがクリアされること', async () => {
    const onCreate = jest.fn().mockResolvedValue(undefined)
    render(<TodoForm onCreate={onCreate} />)

    await userEvent.type(screen.getByTestId('todo-input'), 'テストタスク')
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(screen.getByTestId('todo-input')).toHaveValue('')
    })
  })

  it('500文字超でバリデーションエラーが表示されること', async () => {
    render(<TodoForm onCreate={jest.fn()} />)

    const longText = 'a'.repeat(501)
    await userEvent.type(screen.getByTestId('todo-input'), longText)
    await userEvent.click(screen.getByTestId('add-todo-button'))

    expect(screen.getByTestId('title-error')).toBeInTheDocument()
  })

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

    resolveCreate()
  })

  it('前後スペース込みで500文字超でもtrim後500文字以内なら送信できる', async () => {
    const onCreate = jest.fn().mockResolvedValue(undefined)
    render(<TodoForm onCreate={onCreate} />)

    const text = ' ' + 'a'.repeat(500) + ' '
    await userEvent.type(screen.getByTestId('todo-input'), text)
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith('a'.repeat(500))
    })
  })

  it('onCreate が失敗した場合、フォーム内にエラーメッセージが表示される', async () => {
    const onCreate = jest.fn().mockRejectedValue(new Error('サーバーエラー'))
    render(<TodoForm onCreate={onCreate} />)

    await userEvent.type(screen.getByTestId('todo-input'), '失敗タスク')
    await userEvent.click(screen.getByTestId('add-todo-button'))

    await waitFor(() => {
      expect(screen.getByTestId('title-error')).toHaveTextContent('サーバーエラー')
    })
  })

  it('バリデーションエラー後に入力するとエラーが消える', async () => {
    render(<TodoForm onCreate={jest.fn()} />)

    await userEvent.click(screen.getByTestId('add-todo-button'))
    expect(screen.getByTestId('title-error')).toBeInTheDocument()

    await userEvent.type(screen.getByTestId('todo-input'), 'a')
    expect(screen.queryByTestId('title-error')).not.toBeInTheDocument()
  })
})
