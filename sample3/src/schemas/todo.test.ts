import { titleSchema, idSchema, createTodoSchema, updateTodoSchema, listQuerySchema } from './todo'

describe('titleSchema', () => {
  it('titleSchema がエクスポートされている', () => {
    expect(titleSchema).toBeDefined()
  })

  it('trim後に500文字ちょうどは許可する', () => {
    const result = titleSchema.parse(' ' + 'a'.repeat(500))
    expect(result).toHaveLength(500)
  })
})

describe('idSchema', () => {
  it('accepts a valid cuid', () => {
    expect(() => idSchema.parse('cltest123456789')).not.toThrow()
  })

  it('rejects an empty string', () => {
    expect(() => idSchema.parse('')).toThrow()
  })

  it('rejects path traversal characters', () => {
    expect(() => idSchema.parse('../../etc')).toThrow()
  })

  it('rejects strings over 128 characters', () => {
    expect(() => idSchema.parse('a'.repeat(129))).toThrow()
  })
})

describe('createTodoSchema', () => {
  it('accepts a valid title', () => {
    const result = createTodoSchema.parse({ title: 'Buy groceries' })
    expect(result.title).toBe('Buy groceries')
  })

  it('trims whitespace from title', () => {
    const result = createTodoSchema.parse({ title: '  Buy groceries  ' })
    expect(result.title).toBe('Buy groceries')
  })

  it('rejects an empty string', () => {
    expect(() => createTodoSchema.parse({ title: '' })).toThrow()
  })

  it('rejects a whitespace-only string', () => {
    expect(() => createTodoSchema.parse({ title: '   ' })).toThrow()
  })

  it('rejects a title exceeding 500 characters', () => {
    expect(() => createTodoSchema.parse({ title: 'a'.repeat(501) })).toThrow()
  })

  it('accepts a title of exactly 500 characters', () => {
    const result = createTodoSchema.parse({ title: 'a'.repeat(500) })
    expect(result.title).toHaveLength(500)
  })

  it('rejects missing title field', () => {
    expect(() => createTodoSchema.parse({})).toThrow()
  })
})

describe('updateTodoSchema', () => {
  it('accepts title update only', () => {
    const result = updateTodoSchema.parse({ title: 'Updated title' })
    expect(result.title).toBe('Updated title')
    expect(result.completed).toBeUndefined()
  })

  it('accepts completed update only', () => {
    const result = updateTodoSchema.parse({ completed: true })
    expect(result.completed).toBe(true)
    expect(result.title).toBeUndefined()
  })

  it('accepts both title and completed', () => {
    const result = updateTodoSchema.parse({ title: 'Done', completed: true })
    expect(result.title).toBe('Done')
    expect(result.completed).toBe(true)
  })

  it('rejects an empty request body (no fields)', () => {
    expect(() => updateTodoSchema.parse({})).toThrow()
  })

  it('rejects title set to empty string', () => {
    expect(() => updateTodoSchema.parse({ title: '' })).toThrow()
  })

  it('rejects title exceeding 500 characters', () => {
    expect(() => updateTodoSchema.parse({ title: 'a'.repeat(501) })).toThrow()
  })

  it('trims whitespace from title', () => {
    const result = updateTodoSchema.parse({ title: '  Trimmed  ' })
    expect(result.title).toBe('Trimmed')
  })
})

describe('listQuerySchema', () => {
  it('returns default values when no params given', () => {
    const result = listQuerySchema.parse({})
    expect(result.page).toBe(1)
    expect(result.limit).toBe(20)
    expect(result.completed).toBeUndefined()
  })

  it('coerces string numbers to integers', () => {
    const result = listQuerySchema.parse({ page: '3', limit: '10' })
    expect(result.page).toBe(3)
    expect(result.limit).toBe(10)
  })

  it('accepts completed=true filter', () => {
    const result = listQuerySchema.parse({ completed: 'true' })
    expect(result.completed).toBe('true')
  })

  it('accepts completed=false filter', () => {
    const result = listQuerySchema.parse({ completed: 'false' })
    expect(result.completed).toBe('false')
  })

  it('rejects page=0', () => {
    expect(() => listQuerySchema.parse({ page: '0' })).toThrow()
  })

  it('rejects limit=0', () => {
    expect(() => listQuerySchema.parse({ limit: '0' })).toThrow()
  })

  it('rejects limit exceeding 100', () => {
    expect(() => listQuerySchema.parse({ limit: '101' })).toThrow()
  })

  it('rejects invalid completed value', () => {
    expect(() => listQuerySchema.parse({ completed: 'yes' })).toThrow()
  })
})
