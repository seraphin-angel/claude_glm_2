import { Todo } from '@/types/todo'
import { Button } from '@/components/ui/Button'

interface TodoItemProps {
  todo: Todo
  onToggle: (id: string, completed: boolean) => void
  onDelete: (id: string) => void
}

export function TodoItem({ todo, onToggle, onDelete }: TodoItemProps) {
  return (
    <div
      className="flex items-center gap-3 rounded-md border border-gray-200 bg-white px-4 py-3"
      data-testid="todo-item"
    >
      <input
        type="checkbox"
        checked={todo.completed}
        onChange={() => onToggle(todo.id, todo.completed)}
        aria-label={`「${todo.title}」を${todo.completed ? '未完了にする' : '完了にする'}`}
        className="h-4 w-4 cursor-pointer rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        data-testid="todo-checkbox"
      />
      <span
        className={`flex-1 text-sm ${
          todo.completed ? 'text-gray-400 line-through' : 'text-gray-900'
        }`}
        data-testid="todo-title"
      >
        {todo.title}
      </span>
      <Button
        variant="danger"
        onClick={() => onDelete(todo.id)}
        aria-label={`「${todo.title}」を削除`}
        data-testid="delete-button"
      >
        削除
      </Button>
    </div>
  )
}
