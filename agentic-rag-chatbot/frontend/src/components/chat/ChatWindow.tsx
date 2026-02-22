import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useChat } from '@/hooks/useChat'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { HITLWidget } from '@/components/hitl/HITLWidget'

export function ChatWindow() {
  const {
    messages,
    status,
    streamingContent,
    currentHITL,
    activeTool,
    error,
    send,
    respondToHITL,
  } = useChat()

  const isDisabled = status === 'streaming'

  return (
    <Card className="flex flex-col h-full overflow-hidden">
      {/* ツール実行中のインジケーター */}
      {activeTool && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-950 border-b flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          <span className="text-xs text-blue-700 dark:text-blue-300">
            {activeTool} を実行中...
          </span>
        </div>
      )}

      {/* メッセージ一覧 */}
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={status === 'streaming'}
      />

      {/* HITL ウィジェット */}
      {status === 'hitl_pending' && currentHITL && (
        <div className="px-4 pb-2">
          <HITLWidget
            request={currentHITL}
            onRespond={respondToHITL}
            disabled={false}
          />
        </div>
      )}

      {/* エラー表示 */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-950 border-t">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* ステータスバッジ */}
      {status !== 'idle' && (
        <div className="px-4 py-1 flex justify-end">
          <Badge variant="secondary" className="text-[10px]">
            {status === 'streaming' && '応答中...'}
            {status === 'hitl_pending' && '確認待ち'}
            {status === 'error' && 'エラー'}
          </Badge>
        </div>
      )}

      {/* 入力エリア */}
      <ChatInput
        onSend={send}
        disabled={isDisabled || status === 'hitl_pending'}
      />
    </Card>
  )
}
