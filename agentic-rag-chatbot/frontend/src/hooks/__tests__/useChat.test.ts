import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChat } from '../useChat'
import { setIsDevelopment, __resetIsDevelopment } from '@/lib/logger'

// crypto.randomUUIDのモック
vi.stubGlobal('crypto', {
  randomUUID: () => 'test-uuid-' + Math.random().toString(36).slice(2),
})

// 個別インスタンスの型定義
interface MockEventSourceInstance {
  onmessage: ((event: MessageEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onopen: ((event: Event) => void) | null
  readyState: number
  close: ReturnType<typeof vi.fn>
  simulateMessage: (data: object) => void
  url: string
}

// 後方互換性のための単一インスタンス参照
let mockEventSourceInstance: MockEventSourceInstance

// MockEventSourceクラス（複数インスタンス追跡対応）
class MockEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2
  static instances: MockEventSourceInstance[] = []

  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onopen: ((event: Event) => void) | null = null
  readyState = 0
  url: string
  close = vi.fn(() => {
    this.readyState = 2
  })

  constructor(url: string) {
    this.url = url
    const instance = this as unknown as MockEventSourceInstance
    instance.simulateMessage = (data: object) => {
      this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
    }
    instance.url = url
    MockEventSource.instances.push(instance)
    mockEventSourceInstance = instance
  }
}

beforeEach(() => {
  MockEventSource.instances = []
  vi.stubGlobal('EventSource', MockEventSource)
  vi.stubGlobal('fetch', vi.fn())
  // テスト用に開発モードを有効化
  setIsDevelopment(true)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  // ロガーをリセット
  __resetIsDevelopment()
})

function mockFetchSuccess(data: object) {
  ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ success: true, data }),
  })
}

function mockFetchFailure(error: string) {
  ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ success: false, error }),
  })
}

describe('useChat', () => {
  describe('C2: hitl_request のフィールド欠落ガード', () => {
    it('request_idとquestionが正しく提供された場合、currentHITLが設定される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-1',
          question: 'どちらですか？',
          options: ['A', 'B'],
          input_type: 'buttons',
        })
      })

      expect(result.current.currentHITL).toEqual({
        request_id: 'req-1',
        question: 'どちらですか？',
        options: ['A', 'B'],
        input_type: 'buttons',
      })
    })

    it('hitl_requestイベントで全フィールドが正しく設定される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-1',
          question: 'どちらですか？',
          options: ['A', 'B'],
          input_type: 'buttons',
        })
      })

      expect(result.current.currentHITL).toEqual({
        request_id: 'req-1',
        question: 'どちらですか？',
        options: ['A', 'B'],
        input_type: 'buttons',
      })
      expect(result.current.status).toBe('hitl_pending')
    })

    it('hitl_requestイベントでoptionsがnullの場合も正しく処理される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-2',
          question: 'テキストを入力してください',
          options: null,
          input_type: 'text',
        })
      })

      expect(result.current.currentHITL).toEqual({
        request_id: 'req-2',
        question: 'テキストを入力してください',
        options: null,
        input_type: 'text',
      })
    })
  })

  describe('C4: response.success === false のエラーハンドリング', () => {
    it('send()でAPIがsuccess:falseを返した場合、errorステートが設定される', async () => {
      mockFetchFailure('サーバーエラーです')
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.error).toBe('サーバーエラーです')
      expect(result.current.status).toBe('error')
    })

    it('send()でAPIがsuccess:falseでerrorなしの場合、デフォルトメッセージが設定される', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: false }),
      })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.error).toBeTruthy()
      expect(result.current.status).toBe('error')
    })
  })

  describe('エラーログ出力', () => {
    it('send()でネットワークエラー時にlogger.errorで詳細がログ出力される', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Network error'),
      )
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        '[useChat]',
        expect.objectContaining({
          message: 'Send message error',
          error: 'Network error',
        }),
      )
      expect(result.current.error).toBe('Network error')

      consoleSpy.mockRestore()
    })

    it('send()で予期しないエラー型の場合、logger.errorで詳細がログ出力される', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce({ weird: 'object' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        '[useChat]',
        expect.objectContaining({
          message: 'Send message error',
          error: '予期しないエラーが発生しました',
          errorType: 'object',
        }),
      )
      expect(result.current.error).toBe('予期しないエラーが発生しました')

      consoleSpy.mockRestore()
    })

    it('respondToHITL()でエラー時にlogger.errorで詳細がログ出力される', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-1',
          question: 'どちらですか？',
        })
      })

      ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Resume failed'),
      )

      await act(async () => {
        await result.current.respondToHITL('response')
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        '[useChat]',
        expect.objectContaining({
          message: 'RespondToHITL error',
          error: 'Resume failed',
        }),
      )

      consoleSpy.mockRestore()
    })

    it('retryLastMessage()でメッセージがない場合、logger.warnでログ出力される', async () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.retryLastMessage()
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        '[useChat]',
        expect.objectContaining({
          message: 'No user message found to retry',
        }),
      )

      consoleSpy.mockRestore()
    })

    it('respondToHITL()で無効な状態の場合、logger.errorでログ出力される', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { result } = renderHook(() => useChat())

      // currentHITLがnullの状態でrespondToHITLを呼ぶ
      await act(async () => {
        await result.current.respondToHITL('response')
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        '[useChat]',
        expect.objectContaining({
          message: 'respondToHITL called with invalid state',
          hasHITL: false,
          hasThreadId: false,
        }),
      )

      consoleSpy.mockRestore()
    })
  })

  describe('ユーザーフィードバック付き早期return', () => {
    it('respondToHITL()でcurrentHITLがnullの場合、setErrorが呼ばれる', async () => {
      const { result } = renderHook(() => useChat())

      // currentHITLがnullの状態でrespondToHITLを呼ぶ
      await act(async () => {
        await result.current.respondToHITL('response')
      })

      expect(result.current.error).toBe('チャットセッションが無効です。ページを再読み込みしてください。')
    })

    it('retryLastMessage()でユーザーメッセージがない場合、setErrorが呼ばれる', async () => {
      const { result } = renderHook(() => useChat())

      // メッセージがない状態でretryLastMessageを呼ぶ
      await act(async () => {
        await result.current.retryLastMessage()
      })

      expect(result.current.error).toBe('再試行するメッセージが見つかりません')
    })
  })

  describe('message_complete イベント処理 (Criticality: 8)', () => {
    it('message_completeイベントでアシスタントメッセージが追加される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'message_complete',
          content: 'これはアシスタントの回答です。',
        })
      })

      expect(result.current.messages).toHaveLength(2) // ユーザー + アシスタント
      const assistantMessage = result.current.messages[1]
      expect(assistantMessage.role).toBe('assistant')
      expect(assistantMessage.content).toBe('これはアシスタントの回答です。')
    })

    it('message_completeイベントでsourcesが正しく設定される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // 先にsourceイベントを送信
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'source',
          documents: [
            { id: 'doc-1', content: 'Document content', metadata: { source: 'test' } },
          ],
        })
      })

      // message_completeイベントを送信
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'message_complete',
          content: '回答です。',
        })
      })

      const assistantMessage = result.current.messages[1]
      expect(assistantMessage.sources).toBeDefined()
      expect(assistantMessage.sources).toHaveLength(1)
      expect(assistantMessage.sources?.[0].id).toBe('doc-1')
    })

    it('message_completeイベントでqualityScoreが正しく設定される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // 先にqualityイベントを送信
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'quality',
          is_relevant: true,
          confidence: 0.95,
          reasoning: 'Highly relevant to the query',
        })
      })

      // message_completeイベントを送信
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'message_complete',
          content: '回答です。',
        })
      })

      const assistantMessage = result.current.messages[1]
      expect(assistantMessage.qualityScore).toBeDefined()
      expect(assistantMessage.qualityScore?.is_relevant).toBe(true)
      expect(assistantMessage.qualityScore?.confidence).toBe(0.95)
      expect(assistantMessage.qualityScore?.reasoning).toBe('Highly relevant to the query')
    })

    it('message_complete後にstreamingContentがクリアされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // トークンを累積
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'ストリーミング',
        })
      })

      expect(result.current.streamingContent).toBe('ストリーミング')

      // message_complete
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'message_complete',
          content: '最終回答',
        })
      })

      expect(result.current.streamingContent).toBe('')
    })
  })

  describe('token イベント累積 (Criticality: 8)', () => {
    it('複数のtokenイベントでstreamingContentが累積される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'Hello',
        })
      })

      expect(result.current.streamingContent).toBe('Hello')

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: ' World',
        })
      })

      expect(result.current.streamingContent).toBe('Hello World')

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: '!',
        })
      })

      expect(result.current.streamingContent).toBe('Hello World!')
    })

    it('tokenイベントでerrorステートがクリアされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // エラーを設定
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'error',
          content: '一時的なエラー',
        })
      })

      expect(result.current.error).toBe('一時的なエラー')

      // 新しいトークンが来たらエラーがクリアされる
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: '再開',
        })
      })

      expect(result.current.error).toBeNull()
      expect(result.current.streamingContent).toBe('再開')
    })

    it('tokenイベントのcontentが蓄積される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'Hello',
        })
      })

      expect(result.current.streamingContent).toBe('Hello')

      // 追加のトークンイベント
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: ' World',
        })
      })

      // 蓄積されていることを確認
      expect(result.current.streamingContent).toBe('Hello World')
    })
  })

  describe('resetConversation (Criticality: 7)', () => {
    it('全ステートがリセットされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      // メッセージを送信して状態を変更
      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'Streaming content',
        })
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-1',
          question: '質問ですか？',
        })
      })

      // 状態が設定されていることを確認
      expect(result.current.messages.length).toBeGreaterThan(0)
      expect(result.current.streamingContent).toBe('Streaming content')
      expect(result.current.currentHITL).not.toBeNull()

      // リセット実行
      act(() => {
        result.current.resetConversation()
      })

      // 全ステートがリセットされていることを確認
      expect(result.current.messages).toHaveLength(0)
      expect(result.current.status).toBe('idle')
      expect(result.current.streamingContent).toBe('')
      expect(result.current.currentHITL).toBeNull()
      expect(result.current.activeTool).toBeNull()
      expect(result.current.toolHistory).toHaveLength(0)
      expect(result.current.error).toBeNull()
    })

    it('SSE接続がクローズされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // リセット実行
      act(() => {
        result.current.resetConversation()
      })

      // EventSourceのcloseが呼ばれたことを確認
      expect(mockEventSourceInstance.close).toHaveBeenCalled()
    })

    it('エラー状態からもリセットできる', async () => {
      mockFetchFailure('サーバーエラー')
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.status).toBe('error')
      expect(result.current.error).toBe('サーバーエラー')

      // リセット実行
      act(() => {
        result.current.resetConversation()
      })

      expect(result.current.status).toBe('idle')
      expect(result.current.error).toBeNull()
    })
  })

  describe('cancelRequest (Criticality: 7)', () => {
    it('SSE接続が切断される', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      // ストリーミング中にキャンセル
      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'Streaming...',
        })
      })

      expect(result.current.streamingContent).toBe('Streaming...')

      // キャンセル実行
      act(() => {
        result.current.cancelRequest()
      })

      // EventSourceのcloseが呼ばれたことを確認
      expect(mockEventSourceInstance.close).toHaveBeenCalled()
    })

    it('ステータスがidleになる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.status).toBe('streaming')

      // キャンセル実行
      act(() => {
        result.current.cancelRequest()
      })

      expect(result.current.status).toBe('idle')
    })

    it('streamingContentがクリアされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'token',
          content: 'Streaming content',
        })
      })

      expect(result.current.streamingContent).toBe('Streaming content')

      // キャンセル実行
      act(() => {
        result.current.cancelRequest()
      })

      expect(result.current.streamingContent).toBe('')
    })

    it('activeToolがクリアされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'tool_start',
          tool_name: 'search_tool',
        })
      })

      expect(result.current.activeTool).toBe('search_tool')

      // キャンセル実行
      act(() => {
        result.current.cancelRequest()
      })

      expect(result.current.activeTool).toBeNull()
    })
  })

  describe('同時送信防止 (Criticality: 7-8)', () => {
    it('streaming状態では送信がブロックされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      // 最初の送信
      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.status).toBe('streaming')

      // fetchをリセット
      const fetchCallCount = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length

      // streaming中に再度送信
      await act(async () => {
        await result.current.send('another message')
      })

      // fetchは追加で呼ばれない（ブロックされた）
      // ※現在の実装ではブロックされないので、このテストはRED（失敗）になる
      expect((global.fetch as ReturnType<typeof vi.fn>).mock.calls.length).toBe(fetchCallCount)
    })

    it('error状態では送信が可能', async () => {
      mockFetchFailure('エラー発生')
      const { result } = renderHook(() => useChat())

      // エラーになる送信
      await act(async () => {
        await result.current.send('hello')
      })

      expect(result.current.status).toBe('error')

      // fetchをリセットして成功に設定
      ;(global.fetch as ReturnType<typeof vi.fn>).mockClear()
      mockFetchSuccess({ thread_id: 'thread-2', status: 'started' })

      // error状態からは送信可能
      await act(async () => {
        await result.current.send('retry')
      })

      expect(global.fetch).toHaveBeenCalledTimes(1)
    })

    it('hitl_pending状態では送信がブロックされる', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      // HITLリクエストが来るまで送信
      await act(async () => {
        await result.current.send('hello')
      })

      act(() => {
        mockEventSourceInstance.simulateMessage({
          type: 'hitl_request',
          request_id: 'req-1',
          question: 'どちらですか？',
        })
      })

      expect(result.current.status).toBe('hitl_pending')

      // fetchをリセット
      ;(global.fetch as ReturnType<typeof vi.fn>).mockClear()

      // hitl_pending中に送信を試みる
      await act(async () => {
        await result.current.send('another message')
      })

      // fetchは呼ばれない（ブロックされるべき）
      // ※現在の実装ではブロックされないので、このテストはRED（失敗）になる
      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('idle状態では送信が可能', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      expect(result.current.status).toBe('idle')

      // idle状態では送信可能
      await act(async () => {
        await result.current.send('hello')
      })

      expect(global.fetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('SSE Network Error Recovery', () => {
    it('should transition to error state on network failure', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      // メッセージ送信
      await act(async () => {
        await result.current.send('Hello')
      })

      expect(result.current.status).toBe('streaming')

      // EventSourceのonerrorをトリガー（複数回のリトライをシミュレート）
      await act(async () => {
        const eventSource = MockEventSource.instances[0]
        if (eventSource && eventSource.onerror) {
          // 最大リトライ数(3回)を超えるまでエラーをトリガー
          for (let i = 0; i < 4; i++) {
            eventSource.onerror(new Event('error'))
            // リトライのsetTimeoutを進めるために少し待機
            await new Promise((resolve) => setTimeout(resolve, 10))
          }
        }
      })

      expect(result.current.status).toBe('error')
      expect(result.current.error).toBeTruthy()
    })

    it('should recover when reconnection succeeds after failure', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      // 最初のメッセージ送信
      await act(async () => {
        await result.current.send('Hello')
      })

      expect(result.current.status).toBe('streaming')

      // 最初の接続でエラーをトリガー（リトライを発生させるが、最終的にエラーにする）
      await act(async () => {
        const es = MockEventSource.instances[0]
        if (es?.onerror) {
          // 最大リトライ数を超える
          for (let i = 0; i < 4; i++) {
            es.onerror(new Event('error'))
            await new Promise((resolve) => setTimeout(resolve, 10))
          }
        }
      })

      expect(result.current.status).toBe('error')

      // 再接続のためにretryLastMessageを呼ぶ
      mockFetchSuccess({ thread_id: 'thread-2', status: 'started' })

      await act(async () => {
        await result.current.retryLastMessage()
      })

      // 新しいEventSourceインスタンスが作成される
      const newEs = MockEventSource.instances[MockEventSource.instances.length - 1]

      // 接続成功をシミュレート
      await act(async () => {
        if (newEs?.onopen) {
          newEs.onopen(new Event('open'))
        }
        if (newEs?.onmessage) {
          newEs.onmessage({
            data: JSON.stringify({ type: 'done' }),
          } as MessageEvent)
        }
      })

      expect(result.current.status).toBe('idle')
      expect(result.current.error).toBeNull()
    })

    it('should show user-friendly message after max retries exceeded', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('Hello')
      })

      // 複数回エラー（リトライ上限到達）- 最大3回リトライ後、4回目でエラー
      await act(async () => {
        const es = MockEventSource.instances[0]
        if (es?.onerror) {
          for (let i = 0; i < 4; i++) {
            es.onerror(new Event('error'))
            await new Promise((resolve) => setTimeout(resolve, 10))
          }
        }
      })

      expect(result.current.status).toBe('error')
      // エラーメッセージには「接続が切断されました」が含まれる
      expect(result.current.error).toContain('接続が切断されました')
    })

    it('should display retry attempt count during reconnection', async () => {
      mockFetchSuccess({ thread_id: 'thread-1', status: 'started' })
      const { result } = renderHook(() => useChat())

      await act(async () => {
        await result.current.send('Hello')
      })

      // 最初のエラーでリトライ状態になる
      await act(async () => {
        const es = MockEventSource.instances[0]
        if (es?.onerror) {
          es.onerror(new Event('error'))
          await new Promise((resolve) => setTimeout(resolve, 10))
        }
      })

      // リトライ中のメッセージが表示される（「再接続中...（1/3）」など）
      expect(result.current.error).toMatch(/再接続中.*1\/3/)

      // 2回目のリトライ
      await act(async () => {
        const es = MockEventSource.instances[0]
        if (es?.onerror) {
          es.onerror(new Event('error'))
          await new Promise((resolve) => setTimeout(resolve, 10))
        }
      })

      expect(result.current.error).toMatch(/再接続中.*2\/3/)
    })
  })
})
