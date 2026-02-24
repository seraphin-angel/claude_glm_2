import type { ChatEvent } from '@/types/message'

export type SSEEventHandler = (event: ChatEvent) => void

export interface SSEConnection {
  readonly close: () => void
}

const MAX_RETRIES = 3
const BASE_DELAY_MS = 1000

export function createSSEConnection(
  threadId: string,
  onEvent: SSEEventHandler,
  onError?: (error: Event) => void,
  onRetry?: (attempt: number) => void,
): SSEConnection {
  let retryCount = 0
  let currentEventSource: EventSource | null = null
  let closed = false

  function connect() {
    if (closed) return

    const url = `/api/chat/stream/${threadId}`
    const eventSource = new EventSource(url)
    currentEventSource = eventSource

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data: ChatEvent = JSON.parse(event.data as string)
        retryCount = 0
        onEvent(data)

        if (data.type === 'done' || data.type === 'error') {
          eventSource.close()
        }
      } catch {
        // パースエラーは無視（ping 等）
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
      if (closed) return

      if (retryCount < MAX_RETRIES) {
        retryCount++
        const delay = BASE_DELAY_MS * Math.pow(2, retryCount - 1)
        if (onRetry) onRetry(retryCount)
        setTimeout(connect, delay)
      } else {
        if (onError) {
          onError(new Event('max_retries_exceeded'))
        }
      }
    }
  }

  connect()

  return {
    close: () => {
      closed = true
      if (currentEventSource && currentEventSource.readyState !== EventSource.CLOSED) {
        currentEventSource.close()
      }
    },
  }
}

export function closeSSEConnection(connection: SSEConnection | null): void {
  if (connection) {
    connection.close()
  }
}
