import { NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { Prisma } from '@prisma/client'
import type { ApiResponse } from '@/types/api'
import { logger } from '@/lib/logger'

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function isSyntaxError(error: unknown): boolean {
  if (error instanceof SyntaxError) return true
  if (typeof error === 'object' && error !== null) {
    const e = error as Record<string, unknown>
    return e.name === 'SyntaxError' || e.constructor?.name === 'SyntaxError'
  }
  return false
}

export function handleApiError(error: unknown): NextResponse<ApiResponse<never>> {
  if (error instanceof ZodError) {
    const message = error.issues.map(e => e.message).join(', ')
    return NextResponse.json(
      { success: false, error: message },
      { status: 400 }
    )
  }

  if (isSyntaxError(error)) {
    return NextResponse.json(
      { success: false, error: 'Invalid JSON in request body' },
      { status: 400 }
    )
  }

  if (error instanceof ApiError) {
    if (error.statusCode >= 500) {
      logger.error('[ApiError]', error.statusCode, error.message)
    }
    return NextResponse.json(
      { success: false, error: error.message },
      { status: error.statusCode }
    )
  }

  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    switch (error.code) {
      case 'P2025':
        return NextResponse.json(
          { success: false, error: 'Record not found' },
          { status: 404 }
        )
      case 'P2002':
        return NextResponse.json(
          { success: false, error: 'A record with this value already exists' },
          { status: 409 }
        )
      default:
        logger.error('[Prisma Error]', error.code, error.message)
        return NextResponse.json(
          { success: false, error: 'A database error occurred' },
          { status: 500 }
        )
    }
  }

  if (error instanceof Prisma.PrismaClientInitializationError) {
    logger.error('[Prisma Init Error]', error.errorCode, error.message)
    return NextResponse.json(
      { success: false, error: 'Database is currently unavailable' },
      { status: 503 }
    )
  }

  if (error instanceof Prisma.PrismaClientValidationError) {
    logger.error('[Prisma Validation Error]', error.message)
    return NextResponse.json(
      { success: false, error: 'A database error occurred' },
      { status: 500 }
    )
  }

  logger.error('[Unhandled Error]', error)
  const isDev = process.env.NODE_ENV === 'development'
  const message = isDev && error instanceof Error
    ? error.message
    : 'An unexpected error occurred'

  return NextResponse.json(
    { success: false, error: message },
    { status: 500 }
  )
}
