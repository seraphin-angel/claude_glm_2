import { useState, useCallback, useRef } from 'react'
import type { Message, ChatStatus, HITLRequest, ChatEvent, SourceDocument, QualityScore } from '@/types/message'
import { sendMessage, resumeChat } from '@/lib/api'
import type { SSEConnection } from '@/lib/sse'
import { createSSEConnection, closeSSEConnection } from '@/lib/sse'
import { logger } from '@/lib/logger'

/**
 * エラーオブジェクトからユーザー表示用のメッセージを抽出する
 */
function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  return '予期しないエラーが発生しました'
}

interface ToolHistoryEntry {
  readonly name: string
  readonly status: 'running' | 'done'
}

interface UseChatReturn {
  readonly messages: readonly Message[]
  readonly status: ChatStatus
  readonly streamingContent: string
  readonly currentHITL: HITLRequest | null
  readonly activeTool: string | null
  readonly toolHistory: readonly ToolHistoryEntry[]
  readonly error: string | null
  readonly send: (message: string) => Promise<void>
  readonly respondToHITL: (response: string) => Promise<void>
  readonly resetConversation: () => void
  readonly retryLastMessage: () => Promise<void>
  readonly cancelRequest: () => void
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<readonly Message[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [streamingContent, setStreamingContent] = useState('')
  const [currentHITL, setCurrentHITL] = useState<HITLRequest | null>(null)
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [toolHistory, setToolHistory] = useState<readonly ToolHistoryEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const threadIdRef = useRef<string | null>(null)
  const eventSourceRef = useRef<SSEConnection | null>(null)
  const streamingContentRef = useRef('')
  const statusRef = useRef<ChatStatus>('idle')
  const currentSourcesRef = useRef<readonly SourceDocument[]>([])
  const currentQualityRef = useRef<QualityScore | null>(null)

  const updateStatus = useCallback((newStatus: ChatStatus) => {
    statusRef.current = newStatus
    setStatus(newStatus)
  }, [])

  const handleEvent = useCallback((event: ChatEvent) => {
    switch (event.type) {
      case 'token':
        if (event.content) {
          setError(null)
          streamingContentRef.current += event.content
          setStreamingContent(streamingContentRef.current)
        }
        break

      case 'tool_start':
        if (event.tool_name) {
          setActiveTool(event.tool_name)
          setToolHistory((prev) => [...prev, { name: event.tool_name!, status: 'running' }])
        }
        break

      case 'tool_end':
        setActiveTool(null)
        setToolHistory((prev) =>
          prev.map((entry) =>
            entry.status === 'running' ? { ...entry, status: 'done' } : entry,
          ),
        )
        break

      case 'source':
        if (event.documents) {
          currentSourcesRef.current = event.documents
        }
        break

      case 'quality':
        if (event.is_relevant !== undefined && event.confidence !== undefined) {
          currentQualityRef.current = {
            is_relevant: event.is_relevant,
            confidence: event.confidence,
            reasoning: event.reasoning ?? '',
          }
        }
        break

      case 'hitl_request':
        if (!event.request_id || !event.question) {
          break
        }
        closeSSEConnection(eventSourceRef.current)
        eventSourceRef.current = null
        setCurrentHITL({
          request_id: event.request_id,
          question: event.question,
          options: event.options ?? null,
          input_type: (event.input_type as 'buttons' | 'text') ?? 'text',
        })
        updateStatus('hitl_pending')
        break

      case 'message_complete':
        if (event.content) {
          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: event.content,
            timestamp: new Date(),
            sources: currentSourcesRef.current.length > 0 ? currentSourcesRef.current : undefined,
            qualityScore: currentQualityRef.current ?? undefined,
          }
          setMessages((prev) => [...prev, assistantMessage])
        }
        setStreamingContent('')
        streamingContentRef.current = ''
        // Reset sources and quality for next message
        currentSourcesRef.current = []
        currentQualityRef.current = null
        break

      case 'error':
        setError(event.content ?? 'エラーが発生しました')
        updateStatus('error')
        setStreamingContent('')
        streamingContentRef.current = ''
        break

      case 'done':
        if (statusRef.current !== 'hitl_pending') {
          updateStatus('idle')
        }
        setActiveTool(null)
        break

      case 'ping':
        // Keep-alive、何もしない
        break
    }
  }, [updateStatus])

  const connectSSE = useCallback((threadId: string) => {
    closeSSEConnection(eventSourceRef.current)

    streamingContentRef.current = ''
    setStreamingContent('')
    updateStatus('streaming')
    setError(null)

    const es = createSSEConnection(
      threadId,
      handleEvent,
      () => {
        // 最大リトライ数を超えた場合
        if (statusRef.current !== 'hitl_pending') {
          setError('接続が切断されました')
          updateStatus('error')
        }
      },
      (attempt: number) => {
        // リトライ中の状態を表示
        if (statusRef.current !== 'hitl_pending') {
          setError(`再接続中...（${attempt}/3）`)
        }
      },
    )
    eventSourceRef.current = es
  }, [handleEvent, updateStatus])

  const send = useCallback(async (content: string) => {
    setToolHistory([])
    // ユーザーメッセージを追加
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    updateStatus('streaming')
    setError(null)

    try {
      const response = await sendMessage(content, threadIdRef.current)
      if (response.success && response.data) {
        threadIdRef.current = response.data.thread_id
        connectSSE(response.data.thread_id)
      } else {
        logger.error('useChat', {
          message: 'API returned unsuccessful response',
          error: response.error,
          success: response.success,
          threadId: threadIdRef.current,
        })
        setError(response.error ?? 'メッセージの送信に失敗しました')
        updateStatus('error')
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err)
      logger.error('useChat', {
        message: 'Send message error',
        error: errorMessage,
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        threadId: threadIdRef.current,
      })
      setError(errorMessage)
      updateStatus('error')
    }
  }, [connectSSE, updateStatus])

  const resetConversation = useCallback(() => {
    closeSSEConnection(eventSourceRef.current)
    eventSourceRef.current = null
    threadIdRef.current = null
    streamingContentRef.current = ''
    statusRef.current = 'idle'
    setMessages([])
    setStatus('idle')
    setStreamingContent('')
    setCurrentHITL(null)
    setActiveTool(null)
    setToolHistory([])
    setError(null)
  }, [])

  const retryLastMessage = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user')
    if (!lastUserMessage) {
      logger.warn('useChat', { message: 'No user message found to retry' })
      setError('再試行するメッセージが見つかりません')
      return
    }
    setError(null)
    await send(lastUserMessage.content)
  }, [messages, send])

  const respondToHITL = useCallback(async (response: string) => {
    if (!currentHITL || !threadIdRef.current) {
      logger.error('useChat', {
        message: 'respondToHITL called with invalid state',
        hasHITL: !!currentHITL,
        hasThreadId: !!threadIdRef.current,
      })
      setError('チャットセッションが無効です。ページを再読み込みしてください。')
      return
    }

    const requestId = currentHITL.request_id
    const savedThreadId = threadIdRef.current

    // ユーザーの回答をメッセージとして追加
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: response,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setCurrentHITL(null)
    updateStatus('streaming')

    try {
      const result = await resumeChat(savedThreadId, requestId, response)
      if (result.success && result.data) {
        connectSSE(result.data.thread_id)
      } else {
        logger.error('useChat', {
          message: 'Resume API returned unsuccessful response',
          error: result.error,
          threadId: savedThreadId,
        })
        setError(result.error ?? '再開に失敗しました')
        updateStatus('error')
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err)
      logger.error('useChat', {
        message: 'RespondToHITL error',
        error: errorMessage,
        errorType: err instanceof Error ? err.constructor.name : typeof err,
        threadId: savedThreadId,
      })
      setError(errorMessage)
      updateStatus('error')
    }
  }, [currentHITL, connectSSE, updateStatus])

  const cancelRequest = useCallback(() => {
    // SSE接続を切断
    closeSSEConnection(eventSourceRef.current)
    eventSourceRef.current = null

    // ストリーミング状態をリセット
    streamingContentRef.current = ''
    statusRef.current = 'idle'
    setStreamingContent('')
    setActiveTool(null)
    updateStatus('idle')
  }, [updateStatus])

  return {
    messages,
    status,
    streamingContent,
    currentHITL,
    activeTool,
    toolHistory,
    error,
    send,
    respondToHITL,
    resetConversation,
    retryLastMessage,
    cancelRequest,
  }
}
