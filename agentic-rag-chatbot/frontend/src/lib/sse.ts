import type { ChatEvent } from '@/types/message'
import { logger } from '@/lib/logger'

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
      const rawData = event.data as string
      if (!rawData || rawData.trim() === '') return

      let data: ChatEvent
      try {
        data = JSON.parse(rawData)
      } catch (parseError) {
        // エラー詳細をログ出力
        logger.error('SSE', {
          message: 'JSON parse error',
          rawData: rawData.substring(0, 200),
          error: parseError instanceof Error ? parseError.message : String(parseError),
          threadId,
        })
        if (onError) onError(new Event('parse_error'))
        return
      }

      retryCount = 0
      onEvent(data)

      if (data.type === 'done' || data.type === 'error') {
        eventSource.close()
      }
    }

    eventSource.onerror = () => {
      // エラー詳細をログ出力
      logger.error('SSE', {
        message: 'Connection error',
        readyState: eventSource.readyState,
        threadId,
        retryCount,
        url,
      })

      eventSource.close()
      if (closed) return

      if (retryCount < MAX_RETRIES) {
        retryCount++
        const delay = BASE_DELAY_MS * Math.pow(2, retryCount - 1)
        if (onRetry) {
          onRetry(retryCount)
        } else {
          // デフォルトでログ出力
          logger.warn('SSE', {
            message: `Retrying connection (${retryCount}/${MAX_RETRIES})`,
            threadId,
          })
        }
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
