import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createSSEConnection, parseChatEvent } from '../sse'
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

describe('parseChatEvent', () => {
  it('正常なtokenイベントを正しくパースする', () => {
    const rawData = JSON.stringify({ type: 'token', content: 'hello' })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({ type: 'token', content: 'hello' })
  })

  it('正常なhitl_requestイベントを正しくパースする', () => {
    const rawData = JSON.stringify({
      type: 'hitl_request',
      request_id: 'req-123',
      question: '確認してください',
      options: ['はい', 'いいえ'],
      input_type: 'buttons',
    })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({
      type: 'hitl_request',
      request_id: 'req-123',
      question: '確認してください',
      options: ['はい', 'いいえ'],
      input_type: 'buttons',
    })
  })

  it('正常なsourceイベントを正しくパースする', () => {
    const rawData = JSON.stringify({
      type: 'source',
      documents: [
        {
          id: 'doc-1',
          title: 'Document 1',
          section: 'Section A',
          score: 0.95,
          snippet: 'This is a snippet',
        },
      ],
    })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({
      type: 'source',
      documents: [
        {
          id: 'doc-1',
          title: 'Document 1',
          section: 'Section A',
          score: 0.95,
          snippet: 'This is a snippet',
        },
      ],
    })
  })

  it('正常なqualityイベントを正しくパースする', () => {
    const rawData = JSON.stringify({
      type: 'quality',
      is_relevant: true,
      confidence: 0.85,
      reasoning: 'This is relevant because...',
    })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({
      type: 'quality',
      is_relevant: true,
      confidence: 0.85,
      reasoning: 'This is relevant because...',
    })
  })

  it('正常なdoneイベントを正しくパースする', () => {
    const rawData = JSON.stringify({ type: 'done' })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({ type: 'done' })
  })

  it('正常なerrorイベントを正しくパースする', () => {
    const rawData = JSON.stringify({ type: 'error', content: 'Error message' })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({ type: 'error', content: 'Error message' })
  })

  it('不正なJSONの場合はnullを返す', () => {
    const result = parseChatEvent('not valid json {{{')
    
    expect(result).toBeNull()
  })

  it('未知のイベントタイプの場合はnullを返す', () => {
    const rawData = JSON.stringify({ type: 'unknown_event', data: 'something' })
    const result = parseChatEvent(rawData)
    
    expect(result).toBeNull()
  })

  it('必須フィールドが欠けている場合はnullを返す', () => {
    // tokenイベントにcontentがない
    const rawData = JSON.stringify({ type: 'token' })
    const result = parseChatEvent(rawData)
    
    expect(result).toBeNull()
  })

  it('フィールドの型が間違っている場合はnullを返す', () => {
    // contentが数値
    const rawData = JSON.stringify({ type: 'token', content: 123 })
    const result = parseChatEvent(rawData)
    
    expect(result).toBeNull()
  })

  it('input_typeが不正な値の場合はnullを返す', () => {
    const rawData = JSON.stringify({
      type: 'hitl_request',
      request_id: 'req-123',
      question: '確認してください',
      options: null,
      input_type: 'invalid_type', // 'buttons' | 'text' 以外
    })
    const result = parseChatEvent(rawData)
    
    expect(result).toBeNull()
  })

  it('tool_startイベントを正しくパースする', () => {
    const rawData = JSON.stringify({ type: 'tool_start', tool_name: 'search' })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({ type: 'tool_start', tool_name: 'search' })
  })

  it('pingイベントを正しくパースする', () => {
    const rawData = JSON.stringify({ type: 'ping' })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({ type: 'ping' })
  })

  it('qualityイベントでreasoningが省略可能であることを確認', () => {
    const rawData = JSON.stringify({
      type: 'quality',
      is_relevant: true,
      confidence: 0.85,
    })
    const result = parseChatEvent(rawData)
    
    expect(result).toEqual({
      type: 'quality',
      is_relevant: true,
      confidence: 0.85,
    })
  })
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
    it('スキーマ検証エラー時にlogger.errorで詳細がログ出力される', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const onEvent = vi.fn()
      const onError = vi.fn()
      createSSEConnection('thread-1', onEvent, onError)

      mockEventSourceInstance.simulateMessage('invalid json {{{')

      expect(consoleSpy).toHaveBeenCalledWith(
        '[SSE]',
        expect.objectContaining({
          message: 'ChatEvent validation error',
          rawData: expect.any(String),
          error: expect.any(String),
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

  describe('重複メッセージ防止 (Criticality: 7-8)', () => {
    it('再接続後に重複メッセージが配信されない', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      // 重複排除オプションを有効化
      createSSEConnection('thread-1', onEvent, onError, onRetry, { deduplicate: true })

      // 最初の接続でメッセージを受信
      const event1 = { type: 'token', content: 'hello', message_id: 'msg-1' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(event1))

      expect(onEvent).toHaveBeenCalledTimes(1)
      expect(onEvent).toHaveBeenCalledWith(event1)

      // エラーで切断
      mockEventSourceInstance.simulateError()
      expect(onRetry).toHaveBeenCalledWith(1)

      // 再接続
      await vi.advanceTimersByTimeAsync(1000)

      // 再接続後、同じmessage_idのメッセージが来ても配信されない
      const duplicateEvent = { type: 'token', content: 'hello', message_id: 'msg-1' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(duplicateEvent))

      // 重複なのでonEventは呼ばれない
      expect(onEvent).toHaveBeenCalledTimes(1)

      // 新しいメッセージは配信される
      const newEvent = { type: 'token', content: 'world', message_id: 'msg-2' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(newEvent))

      expect(onEvent).toHaveBeenCalledTimes(2)
      expect(onEvent).toHaveBeenLastCalledWith(newEvent)

      vi.useRealTimers()
    })

    it('message_idがないメッセージは重複排除されない', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      createSSEConnection('thread-1', onEvent, onError, onRetry, { deduplicate: true })

      // message_idがないメッセージ
      const eventWithoutId = { type: 'token', content: 'hello' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(eventWithoutId))

      expect(onEvent).toHaveBeenCalledTimes(1)

      // エラーで切断して再接続
      mockEventSourceInstance.simulateError()
      await vi.advanceTimersByTimeAsync(1000)

      // 同じ内容でもmessage_idがないので配信される
      mockEventSourceInstance.simulateMessage(JSON.stringify(eventWithoutId))

      expect(onEvent).toHaveBeenCalledTimes(2)

      vi.useRealTimers()
    })

    it('重複排除が無効な場合は重複メッセージも配信される', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      // deduplicate: false またはオプションなし
      createSSEConnection('thread-1', onEvent, onError, onRetry)

      const event1 = { type: 'token', content: 'hello', message_id: 'msg-1' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(event1))

      expect(onEvent).toHaveBeenCalledTimes(1)

      // エラーで切断して再接続
      mockEventSourceInstance.simulateError()
      await vi.advanceTimersByTimeAsync(1000)

      // 重複排除がないので配信される
      mockEventSourceInstance.simulateMessage(JSON.stringify(event1))

      expect(onEvent).toHaveBeenCalledTimes(2)

      vi.useRealTimers()
    })

    it('多数のメッセージIDを保持してもメモリリークしない', async () => {
      vi.useFakeTimers()
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onRetry = vi.fn()

      createSSEConnection('thread-1', onEvent, onError, onRetry, {
        deduplicate: true,
        maxSeenIds: 100
      })

      // 100件のユニークメッセージを送信
      for (let i = 0; i < 100; i++) {
        const event = { type: 'token', content: `msg-${i}`, message_id: `id-${i}` } as const
        mockEventSourceInstance.simulateMessage(JSON.stringify(event))
      }

      expect(onEvent).toHaveBeenCalledTimes(100)

      // 最初のメッセージIDはもう保持されていない可能性がある（LRU的な動作）
      // ただし、最新のメッセージは重複排除される
      const recentEvent = { type: 'token', content: 'msg-99', message_id: 'id-99' } as const
      mockEventSourceInstance.simulateMessage(JSON.stringify(recentEvent))
      expect(onEvent).toHaveBeenCalledTimes(100) // 重複なので増えない

      vi.useRealTimers()
    })
  })
})
