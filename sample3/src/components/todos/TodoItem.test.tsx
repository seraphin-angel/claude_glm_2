import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoItem } from './TodoItem'
import { Todo } from '@/types/todo'

const baseTodo: Todo = {
  id: '1',
  title: 'テストタスク',
  completed: false,
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
}

describe('TodoItem', () => {
  it('タイトルが表示されること', () => {
    render(
      <TodoItem todo={baseTodo} onToggle={jest.fn()} onDelete={jest.fn()} />
    )
    expect(screen.getByTestId('todo-title')).toHaveTextContent('テストタスク')
  })

  it('チェックボックスクリックで onToggle が呼ばれること', async () => {
    const onToggle = jest.fn()
    render(
      <TodoItem todo={baseTodo} onToggle={onToggle} onDelete={jest.fn()} />
    )
    await userEvent.click(screen.getByTestId('todo-checkbox'))
    expect(onToggle).toHaveBeenCalledWith('1', false)
  })

  it('削除ボタンクリックで onDelete が呼ばれること', async () => {
    const onDelete = jest.fn()
    render(
      <TodoItem todo={baseTodo} onToggle={jest.fn()} onDelete={onDelete} />
    )
    await userEvent.click(screen.getByTestId('delete-button'))
    expect(onDelete).toHaveBeenCalledWith('1')
  })

  it('完了時に line-through スタイルが適用されること', () => {
    const completedTodo: Todo = { ...baseTodo, completed: true }
    render(
      <TodoItem todo={completedTodo} onToggle={jest.fn()} onDelete={jest.fn()} />
    )
    expect(screen.getByTestId('todo-title')).toHaveClass('line-through')
  })

  it('未完了時に line-through スタイルが適用されないこと', () => {
    render(
      <TodoItem todo={baseTodo} onToggle={jest.fn()} onDelete={jest.fn()} />
    )
    expect(screen.getByTestId('todo-title')).not.toHaveClass('line-through')
  })

  it('チェックボックスに aria-label が設定されていること', () => {
    render(
      <TodoItem todo={baseTodo} onToggle={jest.fn()} onDelete={jest.fn()} />
    )
    const checkbox = screen.getByTestId('todo-checkbox')
    expect(checkbox).toHaveAttribute('aria-label')
    expect(checkbox.getAttribute('aria-label')).toContain('テストタスク')
  })

  it('削除ボタンに aria-label が設定されていること', () => {
    render(
      <TodoItem todo={baseTodo} onToggle={jest.fn()} onDelete={jest.fn()} />
    )
    const button = screen.getByTestId('delete-button')
    expect(button).toHaveAttribute('aria-label')
    expect(button.getAttribute('aria-label')).toContain('テストタスク')
  })
})
