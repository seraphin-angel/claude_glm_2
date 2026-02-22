import { useState, useCallback, useRef } from 'react'
import type { Message, ChatStatus, HITLRequest, ChatEvent } from '@/types/message'
import { sendMessage, resumeChat } from '@/lib/api'
import { createSSEConnection, closeSSEConnection } from '@/lib/sse'

interface UseChatReturn {
  readonly messages: readonly Message[]
  readonly status: ChatStatus
  readonly streamingContent: string
  readonly currentHITL: HITLRequest | null
  readonly activeTool: string | null
  readonly error: string | null
  readonly send: (message: string) => Promise<void>
  readonly respondToHITL: (response: string) => Promise<void>
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<readonly Message[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [streamingContent, setStreamingContent] = useState('')
  const [currentHITL, setCurrentHITL] = useState<HITLRequest | null>(null)
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const threadIdRef = useRef<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const streamingContentRef = useRef('')
  const statusRef = useRef<ChatStatus>('idle')

  const updateStatus = useCallback((newStatus: ChatStatus) => {
    statusRef.current = newStatus
    setStatus(newStatus)
  }, [])

  const handleEvent = useCallback((event: ChatEvent) => {
    switch (event.type) {
      case 'token':
        if (event.content) {
          streamingContentRef.current += event.content
          setStreamingContent(streamingContentRef.current)
        }
        break

      case 'tool_start':
        setActiveTool(event.tool_name ?? null)
        break

      case 'tool_end':
        setActiveTool(null)
        break

      case 'hitl_request':
        // SSE切断し、HITL UI を表示
        closeSSEConnection(eventSourceRef.current)
        eventSourceRef.current = null
        setCurrentHITL({
          request_id: event.request_id!,
          question: event.question!,
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
          }
          setMessages((prev) => [...prev, assistantMessage])
        }
        setStreamingContent('')
        streamingContentRef.current = ''
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
        // SSE接続エラー
        if (statusRef.current !== 'hitl_pending') {
          setError('接続が切断されました')
          updateStatus('error')
        }
      },
    )
    eventSourceRef.current = es
  }, [handleEvent, updateStatus])

  const send = useCallback(async (content: string) => {
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
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'メッセージの送信に失敗しました')
      updateStatus('error')
    }
  }, [connectSSE, updateStatus])

  const respondToHITL = useCallback(async (response: string) => {
    if (!currentHITL || !threadIdRef.current) return

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
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '再開に失敗しました')
      updateStatus('error')
    }
  }, [currentHITL, connectSSE, updateStatus])

  return {
    messages,
    status,
    streamingContent,
    currentHITL,
    activeTool,
    error,
    send,
    respondToHITL,
  }
}
