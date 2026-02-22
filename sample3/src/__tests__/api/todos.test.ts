/**
 * @jest-environment node
 */
import { NextRequest } from 'next/server'
import { GET, POST } from '@/app/api/todos/route'
import { PUT, DELETE } from '@/app/api/todos/[id]/route'
import { prisma } from '@/lib/prisma'
import { Prisma } from '@prisma/client'

// Mock Prisma
jest.mock('@/lib/prisma', () => ({
  prisma: {
    todo: {
      findMany: jest.fn(),
      count: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    },
  },
}))

const mockPrisma = prisma as jest.Mocked<typeof prisma>

const mockTodo = {
  id: 'cltest123',
  title: 'Test Todo',
  completed: false,
  createdAt: new Date('2026-01-01T00:00:00.000Z'),
  updatedAt: new Date('2026-01-01T00:00:00.000Z'),
}

function makePrismaP2025Error() {
  return new Prisma.PrismaClientKnownRequestError('Record not found', {
    code: 'P2025',
    clientVersion: '7.4.0',
  })
}

beforeEach(() => {
  jest.clearAllMocks()
})

// ─── GET /api/todos ───────────────────────────────────────────────────────────

describe('GET /api/todos', () => {
  it('returns a list of todos with pagination', async () => {
    ;(mockPrisma.todo.findMany as jest.Mock).mockResolvedValue([mockTodo])
    ;(mockPrisma.todo.count as jest.Mock).mockResolvedValue(1)

    const req = new NextRequest('http://localhost/api/todos')
    const res = await GET(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.success).toBe(true)
    expect(body.data).toHaveLength(1)
    expect(body.data[0].title).toBe('Test Todo')
    expect(body.meta).toEqual({ total: 1, page: 1, limit: 20 })
  })

  it('filters by completed status', async () => {
    ;(mockPrisma.todo.findMany as jest.Mock).mockResolvedValue([])
    ;(mockPrisma.todo.count as jest.Mock).mockResolvedValue(0)

    const req = new NextRequest('http://localhost/api/todos?completed=true&page=2&limit=5')
    const res = await GET(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(mockPrisma.todo.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { completed: true },
        skip: 5,
        take: 5,
      })
    )
    expect(body.meta).toEqual({ total: 0, page: 2, limit: 5 })
  })

  it('returns 400 for invalid query params', async () => {
    const req = new NextRequest('http://localhost/api/todos?page=0')
    const res = await GET(req)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(body.error).toBeDefined()
  })

  it('returns 500 when database error occurs', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {})
    ;(mockPrisma.todo.findMany as jest.Mock).mockRejectedValue(
      new Error('Connection refused')
    )

    const req = new NextRequest('http://localhost/api/todos')
    const res = await GET(req)
    const body = await res.json()

    expect(res.status).toBe(500)
    expect(body.success).toBe(false)
  })

  it('serializes dates to ISO strings', async () => {
    ;(mockPrisma.todo.findMany as jest.Mock).mockResolvedValue([mockTodo])
    ;(mockPrisma.todo.count as jest.Mock).mockResolvedValue(1)

    const req = new NextRequest('http://localhost/api/todos')
    const res = await GET(req)
    const body = await res.json()

    expect(body.data[0].createdAt).toBe('2026-01-01T00:00:00.000Z')
    expect(body.data[0].updatedAt).toBe('2026-01-01T00:00:00.000Z')
  })
})

// ─── POST /api/todos ──────────────────────────────────────────────────────────

describe('POST /api/todos', () => {
  it('creates a new todo', async () => {
    ;(mockPrisma.todo.create as jest.Mock).mockResolvedValue(mockTodo)

    const req = new NextRequest('http://localhost/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Test Todo' }),
    })
    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(201)
    expect(body.success).toBe(true)
    expect(body.data.title).toBe('Test Todo')
  })

  it('returns 400 for missing title', async () => {
    const req = new NextRequest('http://localhost/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
  })

  it('returns 400 for empty title', async () => {
    const req = new NextRequest('http://localhost/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '' }),
    })
    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
  })

  it('returns 400 for title exceeding 500 characters', async () => {
    const req = new NextRequest('http://localhost/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'a'.repeat(501) }),
    })
    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
  })

  it('returns 400 for invalid JSON body', async () => {
    const req = new NextRequest('http://localhost/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: 'invalid json{{',
    })
    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(body.error).toContain('Invalid JSON')
  })
})

// ─── PUT /api/todos/[id] ──────────────────────────────────────────────────────

describe('PUT /api/todos/[id]', () => {
  it('updates a todo title', async () => {
    const updatedTodo = { ...mockTodo, title: 'Updated' }
    ;(mockPrisma.todo.update as jest.Mock).mockResolvedValue(updatedTodo)

    const req = new NextRequest('http://localhost/api/todos/cltest123', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Updated' }),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: 'cltest123' }) })
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.success).toBe(true)
    expect(body.data.title).toBe('Updated')
  })

  it('toggles completed status', async () => {
    const updatedTodo = { ...mockTodo, completed: true }
    ;(mockPrisma.todo.update as jest.Mock).mockResolvedValue(updatedTodo)

    const req = new NextRequest('http://localhost/api/todos/cltest123', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed: true }),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: 'cltest123' }) })
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.data.completed).toBe(true)
  })

  it('returns 404 via P2025 when todo not found', async () => {
    ;(mockPrisma.todo.update as jest.Mock).mockRejectedValue(makePrismaP2025Error())

    const req = new NextRequest('http://localhost/api/todos/notexist', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Updated' }),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: 'notexist' }) })
    const body = await res.json()

    expect(res.status).toBe(404)
    expect(body.success).toBe(false)
  })

  it('returns 400 when no fields provided', async () => {
    const req = new NextRequest('http://localhost/api/todos/cltest123', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: 'cltest123' }) })
    const body = await res.json()

    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
  })

  it('returns 400 for empty id', async () => {
    const req = new NextRequest('http://localhost/api/todos/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Updated' }),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: '' }) })
    const body = await res.json()
    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(mockPrisma.todo.update).not.toHaveBeenCalled()
  })

  it('returns 400 for id with invalid characters', async () => {
    const req = new NextRequest('http://localhost/api/todos/bad', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Updated' }),
    })
    const res = await PUT(req, { params: Promise.resolve({ id: '../../etc/passwd' }) })
    const body = await res.json()
    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(mockPrisma.todo.update).not.toHaveBeenCalled()
  })
})

// ─── DELETE /api/todos/[id] ───────────────────────────────────────────────────

describe('DELETE /api/todos/[id]', () => {
  it('deletes a todo and returns success with null data', async () => {
    ;(mockPrisma.todo.delete as jest.Mock).mockResolvedValue(mockTodo)

    const req = new NextRequest('http://localhost/api/todos/cltest123', {
      method: 'DELETE',
    })
    const res = await DELETE(req, { params: Promise.resolve({ id: 'cltest123' }) })
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.success).toBe(true)
    expect(body.data).toBeNull()
  })

  it('returns 404 via P2025 when todo not found', async () => {
    ;(mockPrisma.todo.delete as jest.Mock).mockRejectedValue(makePrismaP2025Error())

    const req = new NextRequest('http://localhost/api/todos/notexist', {
      method: 'DELETE',
    })
    const res = await DELETE(req, { params: Promise.resolve({ id: 'notexist' }) })
    const body = await res.json()

    expect(res.status).toBe(404)
    expect(body.success).toBe(false)
  })

  it('returns 400 for empty id', async () => {
    const req = new NextRequest('http://localhost/api/todos/', { method: 'DELETE' })
    const res = await DELETE(req, { params: Promise.resolve({ id: '' }) })
    const body = await res.json()
    expect(res.status).toBe(400)
    expect(body.success).toBe(false)
    expect(mockPrisma.todo.delete).not.toHaveBeenCalled()
  })
})
