import type { ChatEvent } from '@/types/message'

export type SSEEventHandler = (event: ChatEvent) => void

export function createSSEConnection(
  threadId: string,
  onEvent: SSEEventHandler,
  onError?: (error: Event) => void,
): EventSource {
  const url = `/api/chat/stream/${threadId}`
  const eventSource = new EventSource(url)

  eventSource.onmessage = (event: MessageEvent) => {
    try {
      const data: ChatEvent = JSON.parse(event.data as string)
      onEvent(data)

      // done または error で自動切断
      if (data.type === 'done' || data.type === 'error') {
        eventSource.close()
      }
    } catch {
      // パースエラーは無視（ping 等）
    }
  }

  eventSource.onerror = (error: Event) => {
    if (onError) {
      onError(error)
    }
    eventSource.close()
  }

  return eventSource
}

export function closeSSEConnection(eventSource: EventSource | null): void {
  if (eventSource && eventSource.readyState !== EventSource.CLOSED) {
    eventSource.close()
  }
}
