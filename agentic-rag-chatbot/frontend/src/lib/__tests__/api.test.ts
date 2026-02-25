import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { sendMessage, resumeChat, sendFeedback } from '../api'

describe('api', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // TypeScriptの型システム検証: 各関数が常にApiResponse<T>を返すことを確認
  describe('戻り値の型安全性', () => {
    it('sendMessageは常にApiResponse<ChatStartData>を返し、undefinedを返さない', async () => {
      // 正常系
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { thread_id: 'thread-1' } }),
      })

      const result1 = await sendMessage('hello')
      expect(result1).toBeDefined()
      expect(typeof result1.success).toBe('boolean')

      // ネットワークエラー時も例外がスローされ、undefinedが返らないことを確認
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      try {
        await sendMessage('hello')
        // もし到这里に到達した場合、例外がスローされているべき
        fail('例外がスローされるべきですが、スローされませんでした')
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toBe(
          'ネットワークに接続できません。インターネット接続を確認してください。',
        )
      }
    })

    it('resumeChatは常にApiResponse<ChatStartData>を返し、undefinedを返さない', async () => {
      // ネットワークエラー時
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      try {
        await resumeChat('thread-1', 'req-1', 'response')
        fail('例外がスローされるべきですが、スローされませんでした')
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toBe(
          'ネットワークに接続できません。インターネット接続を確認してください。',
        )
      }
    })

    it('sendFeedbackは常にApiResponse<void>を返し、undefinedを返さない', async () => {
      // ネットワークエラー時
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      try {
        await sendFeedback('msg-1', 'positive')
        fail('例外がスローされるべきですが、スローされませんでした')
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toBe(
          'ネットワークに接続できません。インターネット接続を確認してください。',
        )
      }
    })
  })

  describe('sendMessage', () => {
    it('正常なレスポンスを返す', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { thread_id: 'thread-1' } }),
      })

      const result = await sendMessage('hello')

      expect(result.success).toBe(true)
      expect(result.data?.thread_id).toBe('thread-1')
    })

    it('HTTPエラー時にステータスコードとステータステキストを含むエラーを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('Server error details'),
      })

      await expect(sendMessage('hello')).rejects.toThrow('API error: 500 Internal Server Error')
    })

    it('ネットワークエラー（Failed to fetch）時にユーザーフレンドリーなメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      await expect(sendMessage('hello')).rejects.toThrow(
        'ネットワークに接続できません。インターネット接続を確認してください。',
      )
    })

    it('JSONパースエラー時に適切なエラーを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      })

      await expect(sendMessage('hello')).rejects.toThrow()
    })

    it('JSONパースエラー時にユーザーフレンドリーなエラーメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      })

      await expect(sendMessage('hello')).rejects.toThrow(
        'サーバーからの応答を解析できませんでした。しばらく待ってから再試行してください。',
      )
    })

    it('threadIdを指定した場合、リクエストボディに含まれる (Criticality: 7)', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { thread_id: 'existing-thread' } }),
      })

      const result = await sendMessage('hello', 'existing-thread')

      expect(result.success).toBe(true)
      // fetchが正しいボディで呼ばれたことを確認
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ message: 'hello', thread_id: 'existing-thread' }),
        }),
      )
    })

    it('threadIdを指定しない場合、リクエストボディのthread_idはnullになる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { thread_id: 'new-thread' } }),
      })

      await sendMessage('hello')

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/chat',
        expect.objectContaining({
          body: JSON.stringify({ message: 'hello', thread_id: null }),
        }),
      )
    })
  })

  describe('resumeChat', () => {
    it('正常なレスポンスを返す', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: { thread_id: 'thread-1' } }),
      })

      const result = await resumeChat('thread-1', 'req-1', 'response')

      expect(result.success).toBe(true)
    })

    it('ネットワークエラー時にユーザーフレンドリーなメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      await expect(resumeChat('thread-1', 'req-1', 'response')).rejects.toThrow(
        'ネットワークに接続できません。インターネット接続を確認してください。',
      )
    })

    it('JSONパースエラー時にユーザーフレンドリーなエラーメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      })

      await expect(resumeChat('thread-1', 'req-1', 'response')).rejects.toThrow(
        'サーバーからの応答を解析できませんでした。しばらく待ってから再試行してください。',
      )
    })
  })

  describe('sendFeedback', () => {
    it('正常なレスポンスを返す', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

      const result = await sendFeedback('msg-1', 'positive')

      expect(result.success).toBe(true)
    })

    it('HTTPエラー時にエラーを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: () => Promise.resolve(''),
      })

      await expect(sendFeedback('msg-1', 'positive')).rejects.toThrow('API error: 400 Bad Request')
    })

    it('ネットワークエラー時にユーザーフレンドリーなメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new TypeError('Failed to fetch'),
      )

      await expect(sendFeedback('msg-1', 'positive')).rejects.toThrow(
        'ネットワークに接続できません。インターネット接続を確認してください。',
      )
    })

    it('JSONパースエラー時にユーザーフレンドリーなエラーメッセージを投げる', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      })

      await expect(sendFeedback('msg-1', 'positive')).rejects.toThrow(
        'サーバーからの応答を解析できませんでした。しばらく待ってから再試行してください。',
      )
    })
  })
})
