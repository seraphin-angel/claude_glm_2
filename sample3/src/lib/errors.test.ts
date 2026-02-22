/**
 * @jest-environment node
 */
import { ZodError, z } from 'zod'
import { Prisma } from '@prisma/client'
import { ApiError, handleApiError } from './errors'
import { logger } from './logger'

const originalEnv = process.env.NODE_ENV

beforeEach(() => {
  jest.spyOn(logger, 'error').mockImplementation(() => {})
})

afterEach(() => {
  (process.env as Record<string, string | undefined>).NODE_ENV = originalEnv
  jest.restoreAllMocks()
})

describe('handleApiError', () => {
  // ─── ZodError ─────────────────────────────────────────────────────────────
  it('returns 400 with joined issue messages for ZodError', async () => {
    const schema = z.object({ title: z.string().min(1, 'Title is required') })
    let zodError: ZodError
    try {
      schema.parse({})
    } catch (e) {
      zodError = e as ZodError
    }

    const res = handleApiError(zodError!)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(body.error).toBeDefined()
  })

  // ─── ApiError ─────────────────────────────────────────────────────────────
  it('returns the statusCode from ApiError', async () => {
    const res = handleApiError(new ApiError('Forbidden', 403))
    const body = await res.json()

    expect(res.status).toBe(403)
    expect(body.success).toBe(false)
    expect(body.error).toBe('Forbidden')
  })

  // ─── Prisma P2025 ────────────────────────────────────────────────────────
  it('returns 404 for Prisma P2025 error', async () => {
    const error = new Prisma.PrismaClientKnownRequestError('Record not found', {
      code: 'P2025',
      clientVersion: '7.4.0',
    })

    const res = handleApiError(error)
    const body = await res.json()

    expect(res.status).toBe(404)
    expect(body.success).toBe(false)
    expect(body.error).toBe('Record not found')
  })

  // ─── Prisma P2002 ────────────────────────────────────────────────────────
  it('returns 409 for Prisma P2002 unique constraint error', async () => {
    const error = new Prisma.PrismaClientKnownRequestError(
      'Unique constraint failed on the fields: (`title`)',
      { code: 'P2002', clientVersion: '7.4.0' }
    )

    const res = handleApiError(error)
    const body = await res.json()

    expect(res.status).toBe(409)
    expect(body.success).toBe(false)
    expect(body.error).toBeDefined()
  })

  // ─── Prisma unknown code ─────────────────────────────────────────────────
  it('returns 500 with generic message for other Prisma known errors', async () => {
    const error = new Prisma.PrismaClientKnownRequestError('Something went wrong', {
      code: 'P2003',
      clientVersion: '7.4.0',
    })

    const res = handleApiError(error)
    const body = await res.json()

    expect(res.status).toBe(500)
    expect(body.success).toBe(false)
    expect(body.error).not.toContain('Something went wrong')
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── PrismaClientInitializationError ─────────────────────────────────────
  it('returns 503 for PrismaClientInitializationError', async () => {
    const error = new Prisma.PrismaClientInitializationError(
      "Can't reach database server", '7.4.0'
    )
    const res = handleApiError(error)
    const body = await res.json()
    expect(res.status).toBe(503)
    expect(body.success).toBe(false)
    expect(body.error).toBe('Database is currently unavailable')
    expect(body.error).not.toContain('database server')
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── PrismaClientValidationError ───────────────────────────────────────
  it('returns 500 for PrismaClientValidationError', async () => {
    const error = new Prisma.PrismaClientValidationError(
      'Invalid prisma.todo.findMany() call', { clientVersion: '7.4.0' }
    )
    const res = handleApiError(error)
    const body = await res.json()
    expect(res.status).toBe(500)
    expect(body.success).toBe(false)
    expect(body.error).toBe('A database error occurred')
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── SyntaxError (invalid JSON) ──────────────────────────────────────────
  it('returns 400 for SyntaxError (invalid JSON)', async () => {
    const res = handleApiError(new SyntaxError('Unexpected token'))
    const body = await res.json()
    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(body.error).toContain('Invalid JSON')
    expect(logger.error).not.toHaveBeenCalled()
  })

  // ─── Generic Error (production) ──────────────────────────────────────────
  it('does NOT leak error.message in production', async () => {
    (process.env as Record<string, string | undefined>).NODE_ENV = 'production'

    const res = handleApiError(new Error('Database connection string: postgres://secret'))
    const body = await res.json()

    expect(res.status).toBe(500)
    expect(body.error).not.toContain('secret')
    expect(body.error).not.toContain('Database connection')
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── Generic Error (development) ─────────────────────────────────────────
  it('includes error.message in development', async () => {
    (process.env as Record<string, string | undefined>).NODE_ENV = 'development'

    const res = handleApiError(new Error('Detailed dev error'))
    const body = await res.json()

    expect(res.status).toBe(500)
    expect(body.error).toBe('Detailed dev error')
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── Non-Error object ────────────────────────────────────────────────────
  it('returns 500 with generic message for non-Error objects', async () => {
    const res = handleApiError('string error')
    const body = await res.json()

    expect(res.status).toBe(500)
    expect(body.success).toBe(false)
    expect(body.error).toBeDefined()
    expect(logger.error).toHaveBeenCalled()
  })

  // ─── Logging ─────────────────────────────────────────────────────────────
  it('does NOT log for ZodError (expected validation)', async () => {
    const schema = z.object({ title: z.string() })
    let zodError: ZodError
    try {
      schema.parse({ title: 123 })
    } catch (e) {
      zodError = e as ZodError
    }

    handleApiError(zodError!)

    expect(logger.error).not.toHaveBeenCalled()
  })

  it('does NOT log for ApiError with 4xx status', async () => {
    handleApiError(new ApiError('Not Found', 404))
    expect(logger.error).not.toHaveBeenCalled()
  })

  it('logs for ApiError with 5xx status', async () => {
    handleApiError(new ApiError('Internal Error', 500))
    expect(logger.error).toHaveBeenCalled()
  })
})
