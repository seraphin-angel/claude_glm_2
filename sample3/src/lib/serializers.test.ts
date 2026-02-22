/**
 * @jest-environment node
 */
import { serializeTodo } from './serializers'

describe('serializeTodo', () => {
  it('Date を ISO 文字列に変換する', () => {
    const prismaTodo = {
      id: 'cltest123',
      title: 'Test',
      completed: false,
      createdAt: new Date('2026-01-01T00:00:00.000Z'),
      updatedAt: new Date('2026-01-02T00:00:00.000Z'),
    }
    const result = serializeTodo(prismaTodo)
    expect(result.createdAt).toBe('2026-01-01T00:00:00.000Z')
    expect(result.updatedAt).toBe('2026-01-02T00:00:00.000Z')
    expect(typeof result.createdAt).toBe('string')
  })

  it('id, title, completed をそのまま保持する', () => {
    const prismaTodo = {
      id: 'cltest456',
      title: 'Preserve fields',
      completed: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    }
    const result = serializeTodo(prismaTodo)
    expect(result.id).toBe('cltest456')
    expect(result.title).toBe('Preserve fields')
    expect(result.completed).toBe(true)
  })
})
