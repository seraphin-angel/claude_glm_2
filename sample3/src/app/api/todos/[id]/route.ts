import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { handleApiError } from '@/lib/errors'
import { serializeTodo } from '@/lib/serializers'
import { idSchema, updateTodoSchema } from '@/schemas/todo'
import type { ApiResponse } from '@/types/api'
import type { Todo } from '@/types/todo'

type RouteContext = {
  params: Promise<{ id: string }>
}

export async function PUT(
  req: NextRequest,
  { params }: RouteContext
): Promise<NextResponse<ApiResponse<Todo>>> {
  try {
    const { id } = await params
    const validatedId = idSchema.parse(id)
    const body = await req.json()
    const validated = updateTodoSchema.parse(body)

    const todo = await prisma.todo.update({
      where: { id: validatedId },
      data: validated,
    })

    return NextResponse.json({ success: true, data: serializeTodo(todo) })
  } catch (error) {
    return handleApiError(error)
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: RouteContext
): Promise<NextResponse<ApiResponse<null>>> {
  try {
    const { id } = await params
    const validatedId = idSchema.parse(id)

    await prisma.todo.delete({ where: { id: validatedId } })

    return NextResponse.json({ success: true, data: null })
  } catch (error) {
    return handleApiError(error)
  }
}
