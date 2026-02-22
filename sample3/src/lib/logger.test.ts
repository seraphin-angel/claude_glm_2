/**
 * @jest-environment node
 */
import { logger } from './logger'

beforeEach(() => {
  jest.restoreAllMocks()
})

describe('logger', () => {
  it('logger.error delegates to console.error', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {})
    logger.error('test error', 42)
    expect(spy).toHaveBeenCalledWith('test error', 42)
  })

  it('logger.warn delegates to console.warn', () => {
    const spy = jest.spyOn(console, 'warn').mockImplementation(() => {})
    logger.warn('test warning', { detail: true })
    expect(spy).toHaveBeenCalledWith('test warning', { detail: true })
  })
})
