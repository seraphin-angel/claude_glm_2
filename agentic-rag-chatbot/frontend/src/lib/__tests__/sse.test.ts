import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createSSEConnection } from '../sse'
import type { ChatEvent } from '@/types/message'
import { setIsDevelopment, __resetIsDevelopment } from '../logger'

class MockEventSource {
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  readyState = 0
  close = vi.fn(() => {
    this.readyState = 2
  })

  simulateMessage(data: string) {
    this.onmessage?.({ data } as MessageEvent)
  }

  simulateError() {
    this.onerror?.(new Event('error'))
  }
}

let mockEventSourceInstance: MockEventSource

class EventSourceProxy extends MockEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  constructor(_url: string) {
    super()
    mockEventSourceInstance = this
  }
}

beforeEach(() => {
  vi.stubGlobal('EventSource', EventSourceProxy)
  // テスト用に開発モードを有効化
  setIsDevelopment(true)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  // ロガーをリセット
  __resetIsDevelopment()
})

describe('createSSEConnection', () => {
  it('正常なJSONメッセージを受信した場合、onEventが呼ばれる', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    const chatEvent: ChatEvent = { type: 'token', content: 'hello' }
    mockEventSourceInstance.simulateMessage(JSON.stringify(chatEvent))

    expect(onEvent).toHaveBeenCalledOnce()
    expect(onEvent).toHaveBeenCalledWith(chatEvent)
    expect(onError).not.toHaveBeenCalled()
  })

  it('不正なJSON（パースエラー）を受信した場合、onErrorコールバックが呼ばれる', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    mockEventSourceInstance.simulateMessage('this is not valid json {{{')

    expect(onError).toHaveBeenCalledOnce()
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('空のデータ（ping等）を受信した場合は無視される', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    mockEventSourceInstance.simulateMessage('')
    mockEventSourceInstance.simulateMessage('   ')

    expect(onEvent).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })

  it('doneイベントを受信したらEventSourceがcloseされる', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    const doneEvent: ChatEvent = { type: 'done' }
    mockEventSourceInstance.simulateMessage(JSON.stringify(doneEvent))

    expect(mockEventSourceInstance.close).toHaveBeenCalledOnce()
  })

  it('errorイベントを受信したらEventSourceがcloseされる', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    const errorEvent: ChatEvent = { type: 'error', content: 'something went wrong' }
    mockEventSourceInstance.simulateMessage(JSON.stringify(errorEvent))

    expect(mockEventSourceInstance.close).toHaveBeenCalledOnce()
  })

  it('onerrorイベントでEventSourceがcloseされる', () => {
    const onEvent = vi.fn()
    const onError = vi.fn()
    createSSEConnection('thread-1', onEvent, onError)

    mockEventSourceInstance.simulateError()

    expect(mockEventSourceInstance.close).toHaveBeenCalledOnce()
  })

  describe('エラーログ出力', () => {
    it('JSONパースエラー時にlogger.errorで詳細がログ出力される', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const onEvent = vi.fn()
      const onError = vi.fn()
      createSSEConnection('thread-1', onEvent, onError)

      mockEventSourceInstance.simulateMessage('invalid json {{{')

      expect(consoleSpy).toHaveBeenCalledWith(
        '[SSE]',
        expect.objectContaining({
          message: 'JSON parse error',
          rawData: expect.any(String),
          error: expect.any(String),
          threadId: 'thread-1',
        }),
      )
      expect(onError).toHaveBeenCalledOnce()

      consoleSpy.mockRestore()
    })

    it('onerrorイベント時にlogger.errorで接続詳細がログ出力される', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const onEvent = vi.fn()
      const onError = vi.fn()
      createSSEConnection('thread-1', onEvent, onError)

      mockEventSourceInstance.simulateError()

      expect(consoleSpy).toHaveBeenCalledWith(
        '[SSE]',
        expect.objectContaining({
          message: 'Connection error',
          threadId: 'thread-1',
          retryCount: expect.any(Number),
        }),
      )

      consoleSpy.mockRestore()
    })

    it('onRetryコールバックなしでリトライ時にlogger.warnでログ出力される', () => {
      vi.useFakeTimers()
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const onEvent = vi.fn()
      const onError = vi.fn()
      // onRetryを提供しない
      createSSEConnection('thread-1', onEvent, onError)

      mockEventSourceInstance.simulateError()

      expect(consoleSpy).toHaveBeenCalledWith(
        '[SSE]',
        expect.objectContaining({
          message: expect.stringContaining('Retrying connection'),
        }),
      )

      consoleSpy.mockRestore()
      vi.useRealTimers()
    })
  })

  describe('リトライロジック (Criticality: 7)', () => {
    it('onRetryコールバックがリトライ回数と共に呼ばれる', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      createSSEConnection('thread-1', onEvent, onError, onRetry)

      // 1回目のエラー
      mockEventSourceInstance.simulateError()

      expect(onRetry).toHaveBeenCalledWith(1)
      expect(onRetry).toHaveBeenCalledTimes(1)

      // タイマーを進める（1回目のリトライ: 1000ms）
      await vi.advanceTimersByTimeAsync(1000)

      // 2回目のエラー（新しいEventSourceインスタンスが作られる）
      mockEventSourceInstance.simulateError()

      expect(onRetry).toHaveBeenCalledWith(2)
      expect(onRetry).toHaveBeenCalledTimes(2)

      // タイマーを進める（2回目のリトライ: 2000ms）
      await vi.advanceTimersByTimeAsync(2000)

      // 3回目のエラー
      mockEventSourceInstance.simulateError()

      expect(onRetry).toHaveBeenCalledWith(3)
      expect(onRetry).toHaveBeenCalledTimes(3)

      vi.useRealTimers()
    })

    it('最大リトライ数を超えたらonErrorが呼ばれる', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      createSSEConnection('thread-1', onEvent, onError, onRetry)

      // 1回目のエラー → リトライ1
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(1)

      await vi.advanceTimersByTimeAsync(1000)

      // 2回目のエラー → リトライ2
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(2)

      await vi.advanceTimersByTimeAsync(2000)

      // 3回目のエラー → リトライ3
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(3)

      await vi.advanceTimersByTimeAsync(4000)

      // 4回目のエラー → 最大リトライ数超過
      mockEventSourceInstance.simulateError()

      // onRetryは3回までしか呼ばれない
      expect(onRetry).toHaveBeenCalledTimes(3)

      // onErrorが呼ばれる
      expect(onError).toHaveBeenCalled()
      expect(onError).toHaveBeenCalledWith(expect.objectContaining({ type: 'max_retries_exceeded' }))

      vi.useRealTimers()
    })

    it('正常なメッセージ受信後はリトライカウントがリセットされる', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      createSSEConnection('thread-1', onEvent, onError, onRetry)

      // エラー → リトライ1
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(1)

      await vi.advanceTimersByTimeAsync(1000)

      // 正常なメッセージを受信
      const chatEvent = { type: 'token', content: 'hello' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(chatEvent))

      // エラーが発生してもリトライカウントはリセットされているので1から始まる
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(1)

      vi.useRealTimers()
    })
  })
})
