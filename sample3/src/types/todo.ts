import type { z } from 'zod'
import type { createTodoSchema, updateTodoSchema } from '@/schemas/todo'

export interface Todo {
  id: string
  title: string
  completed: boolean
  createdAt: string
  updatedAt: string
}

export type CreateTodoDto = z.infer<typeof createTodoSchema>

export type UpdateTodoDto = z.infer<typeof updateTodoSchema>
