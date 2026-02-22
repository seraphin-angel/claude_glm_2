import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { handleApiError } from '@/lib/errors'
import { serializeTodo } from '@/lib/serializers'
import { createTodoSchema, listQuerySchema } from '@/schemas/todo'
import type { ApiResponse } from '@/types/api'
import type { Todo } from '@/types/todo'

export async function GET(req: NextRequest): Promise<NextResponse<ApiResponse<Todo[]>>> {
  try {
    const { searchParams } = req.nextUrl
    const query = listQuerySchema.parse({
      page: searchParams.get('page') ?? undefined,
      limit: searchParams.get('limit') ?? undefined,
      completed: searchParams.get('completed') ?? undefined,
    })

    const where = query.completed !== undefined
      ? { completed: query.completed === 'true' }
      : {}

    const skip = (query.page - 1) * query.limit

    const [todos, total] = await Promise.all([
      prisma.todo.findMany({
        where,
        skip,
        take: query.limit,
        orderBy: { createdAt: 'desc' },
      }),
      prisma.todo.count({ where }),
    ])

    return NextResponse.json({
      success: true,
      data: todos.map(serializeTodo),
      meta: {
        total,
        page: query.page,
        limit: query.limit,
      },
    })
  } catch (error) {
    return handleApiError(error)
  }
}

export async function POST(req: NextRequest): Promise<NextResponse<ApiResponse<Todo>>> {
  try {
    const body = await req.json()
    const validated = createTodoSchema.parse(body)

    const todo = await prisma.todo.create({
      data: { title: validated.title },
    })

    return NextResponse.json({ success: true, data: serializeTodo(todo) }, { status: 201 })
  } catch (error) {
    return handleApiError(error)
  }
}
