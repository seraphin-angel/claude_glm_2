import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { logger, setIsDevelopment, __resetIsDevelopment } from '../logger'

describe('logger', () => {
  const originalEnv = process.env

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    // テスト後に開発モードに戻す
    __resetIsDevelopment()
  })

  describe('開発環境 (isDevelopment = true)', () => {
    beforeEach(() => {
      setIsDevelopment(true)
    })

    it('logger.errorがコンソールにエラーを出力する', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      logger.error('TestContext', { message: 'test error', code: 500 })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {
        message: 'test error',
        code: 500,
      })

      consoleSpy.mockRestore()
    })

    it('logger.warnがコンソールに警告を出力する', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      logger.warn('TestContext', { message: 'test warning' })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {
        message: 'test warning',
      })

      consoleSpy.mockRestore()
    })

    it('logger.infoがコンソールに情報を出力する', () => {
      const consoleSpy = vi.spyOn(console, 'info').mockImplementation(() => {})

      logger.info('TestContext', { status: 'connected' })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {
        status: 'connected',
      })

      consoleSpy.mockRestore()
    })

    it('logger.debugがコンソールにデバッグ情報を出力する', () => {
      const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})

      logger.debug('TestContext', { debug: true })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', { debug: true })

      consoleSpy.mockRestore()
    })

    it('Errorオブジェクトが適切に処理される', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const error = new Error('Test error message')
      logger.error('TestContext', { error, stack: error.stack })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {
        error,
        stack: error.stack,
      })

      consoleSpy.mockRestore()
    })
  })

  describe('本番環境 (isDevelopment = false)', () => {
    beforeEach(() => {
      setIsDevelopment(false)
    })

    it('logger.errorは本番環境で何も出力しない', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      logger.error('TestContext', { message: 'production error' })

      expect(consoleSpy).not.toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('logger.warnは本番環境で何も出力しない', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      logger.warn('TestContext', { message: 'production warning' })

      expect(consoleSpy).not.toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('logger.infoは本番環境で何も出力しない', () => {
      const consoleSpy = vi.spyOn(console, 'info').mockImplementation(() => {})

      logger.info('TestContext', { status: 'production' })

      expect(consoleSpy).not.toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('logger.debugは本番環境で何も出力しない', () => {
      const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})

      logger.debug('TestContext', { debug: true })

      expect(consoleSpy).not.toHaveBeenCalled()

      consoleSpy.mockRestore()
    })
  })

  describe('エッジケース', () => {
    beforeEach(() => {
      setIsDevelopment(true)
    })

    it('空のデータオブジェクトでも動作する', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      logger.error('TestContext', {})

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {})

      consoleSpy.mockRestore()
    })

    it('ネストしたオブジェクトを適切に処理する', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      logger.error('TestContext', {
        nested: {
          level1: {
            level2: 'value',
          },
        },
      })

      expect(consoleSpy).toHaveBeenCalledWith('[TestContext]', {
        nested: {
          level1: {
            level2: 'value',
          },
        },
      })

      consoleSpy.mockRestore()
    })
  })
})
