import type { ChatEvent } from '@/types/message'
import { ChatEventSchema } from '@/types/message'
import { logger } from '@/lib/logger'

export type SSEEventHandler = (event: ChatEvent) => void

/**
 * JSON文字列をChatEventとして解析し、Zodスキーマで検証する
 * @param rawData - JSON形式の文字列
 * @returns 検証済みのChatEvent、または検証失敗時はnull
 */
export function parseChatEvent(rawData: string): ChatEvent | null {
  try {
    const parsed = JSON.parse(rawData)
    return ChatEventSchema.parse(parsed) as ChatEvent
  } catch (e) {
    logger.error('SSE', {
      message: 'ChatEvent validation error',
      rawData: rawData.substring(0, 200),
      error: e instanceof Error ? e.message : String(e),
    })
    return null
  }
}

export interface SSEConnection {
  readonly close: () => void
}

export interface SSEOptions {
  /** 重複排除を有効にする（message_idベース） */
  deduplicate?: boolean
  /** 保持する最大message_id数（LRU的に古いものから削除） */
  maxSeenIds?: number
}

const MAX_RETRIES = 3
const BASE_DELAY_MS = 1000
const DEFAULT_MAX_SEEN_IDS = 1000

export function createSSEConnection(
  threadId: string,
  onEvent: SSEEventHandler,
  onError?: (error: Event) => void,
  onRetry?: (attempt: number) => void,
  options?: SSEOptions,
): SSEConnection {
  let retryCount = 0
  let currentEventSource: EventSource | null = null
  let closed = false

  // 重複排除用のmessage_idセット
  const deduplicate = options?.deduplicate ?? false
  const maxSeenIds = options?.maxSeenIds ?? DEFAULT_MAX_SEEN_IDS
  const seenMessageIds = new Set<string>()

  function connect() {
    if (closed) return

    const url = `/api/chat/stream/${threadId}`
    const eventSource = new EventSource(url)
    currentEventSource = eventSource

    eventSource.onmessage = (event: MessageEvent) => {
      const rawData = event.data as string
      if (!rawData || rawData.trim() === '') return

      const data = parseChatEvent(rawData)
      if (!data) {
        // parseChatEvent内でログ出力済み
        if (onError) onError(new Event('parse_error'))
        return
      }

      // 重複排除チェック
      if (deduplicate && 'message_id' in data && typeof data.message_id === 'string') {
        if (seenMessageIds.has(data.message_id)) {
          // 重複メッセージは無視
          return
        }
        // 新しいmessage_idを記録
        seenMessageIds.add(data.message_id)
        // メモリリーク防止：maxSeenIdsを超えたら古いものから削除
        if (seenMessageIds.size > maxSeenIds) {
          const iterator = seenMessageIds.values()
          const oldest = iterator.next().value
          if (oldest) {
            seenMessageIds.delete(oldest)
          }
        }
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
