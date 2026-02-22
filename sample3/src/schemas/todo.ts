import { z } from 'zod'

export const idSchema = z.string()
  .min(1, 'ID is required')
  .max(128, 'ID is too long')
  .regex(/^[a-zA-Z0-9_-]+$/, 'ID contains invalid characters')

export const titleSchema = z.string()
  .trim()
  .min(1, 'Title is required')
  .max(500, 'Title cannot exceed 500 characters')

export const createTodoSchema = z.object({
  title: titleSchema
})

export const updateTodoSchema = z.object({
  title: titleSchema.optional(),
  completed: z.boolean().optional()
}).refine(
  (data) => data.title !== undefined || data.completed !== undefined,
  { message: 'At least one field must be provided' }
)

export const listQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  completed: z.enum(['true', 'false']).optional()
})
