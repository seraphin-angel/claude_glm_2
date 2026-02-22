import type { Todo as PrismaTodo } from '@prisma/client'
import type { Todo } from '@/types/todo'

export function serializeTodo(todo: PrismaTodo): Todo {
  return {
    ...todo,
    createdAt: todo.createdAt.toISOString(),
    updatedAt: todo.updatedAt.toISOString(),
  }
}
