import { render, screen } from '@testing-library/react'
import { TodoList } from './TodoList'
import { Todo } from '@/types/todo'

const makeTodo = (id: string, title: string, completed = false): Todo => ({
  id,
  title,
  completed,
  createdAt: '2024-01-01T00:00:00.000Z',
  updatedAt: '2024-01-01T00:00:00.000Z',
})

describe('TodoList', () => {
  it('todos が空の場合に空状態メッセージが表示されること', () => {
    render(<TodoList todos={[]} onToggle={jest.fn()} onDelete={jest.fn()} />)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
  })

  it('todos のリストが正しく表示されること', () => {
    const todos = [
      makeTodo('1', 'タスク1'),
      makeTodo('2', 'タスク2'),
      makeTodo('3', 'タスク3'),
    ]
    render(<TodoList todos={todos} onToggle={jest.fn()} onDelete={jest.fn()} />)

    expect(screen.getByTestId('todo-list')).toBeInTheDocument()
    const items = screen.getAllByTestId('todo-item')
    expect(items).toHaveLength(3)
  })

  it('todos がある場合は空状態メッセージが表示されないこと', () => {
    const todos = [makeTodo('1', 'タスク1')]
    render(<TodoList todos={todos} onToggle={jest.fn()} onDelete={jest.fn()} />)
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
  })
})
