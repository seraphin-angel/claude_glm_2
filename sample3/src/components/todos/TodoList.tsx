import { Todo } from '@/types/todo'
import { TodoItem } from './TodoItem'

interface TodoListProps {
  todos: Todo[]
  onToggle: (id: string, completed: boolean) => void
  onDelete: (id: string) => void
}

export function TodoList({ todos, onToggle, onDelete }: TodoListProps) {
  if (todos.length === 0) {
    return (
      <p
        className="py-8 text-center text-sm text-gray-500"
        data-testid="empty-state"
      >
        タスクがありません。新しいタスクを追加してください。
      </p>
    )
  }

  return (
    <ul className="flex flex-col gap-2" data-testid="todo-list">
      {todos.map((todo) => (
        <li key={todo.id}>
          <TodoItem todo={todo} onToggle={onToggle} onDelete={onDelete} />
        </li>
      ))}
    </ul>
  )
}
