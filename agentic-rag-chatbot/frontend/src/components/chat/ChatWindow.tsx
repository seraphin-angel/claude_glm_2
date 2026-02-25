import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RotateCcw } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { useWaitTimer } from '@/hooks/useWaitTimer'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { HITLWidget } from '@/components/hitl/HITLWidget'
import { ToolProgress } from './ToolProgress'
import { ErrorRecovery } from './ErrorRecovery'
import { WaitNotification } from './WaitNotification'

export function ChatWindow() {
  const {
    messages,
    status,
    streamingContent,
    currentHITL,
    toolHistory,
    error,
    send,
    respondToHITL,
    resetConversation,
    retryLastMessage,
    cancelRequest,
  } = useChat()

  const isStreaming = status === 'streaming'
  const { showWarning, showError } = useWaitTimer(isStreaming)

  const isDisabled = isStreaming

  return (
    <Card className="flex flex-col h-full overflow-hidden" role="main" aria-label="チャット">
      {/* 新しい会話ヘッダーバー */}
      {messages.length > 0 && (
        <div className="px-4 py-2 border-b flex items-center justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={resetConversation}
            disabled={isStreaming}
            className="gap-2 text-muted-foreground hover:text-foreground"
          >
            <RotateCcw className="w-4 h-4" />
            新しい会話
          </Button>
        </div>
      )}

      {/* ツール実行履歴 */}
      {toolHistory.length > 0 && <ToolProgress toolHistory={toolHistory} />}

      {/* 長時間待機通知 */}
      <WaitNotification
        showWarning={showWarning}
        showError={showError}
        onCancel={cancelRequest}
      />

      {/* メッセージ一覧 */}
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        onSuggestSelect={send}
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
        <ErrorRecovery
          error={error}
          onRetry={retryLastMessage}
          onReset={resetConversation}
        />
      )}

      {/* ステータスバッジ */}
      {status !== 'idle' && (
        <div className="px-3 sm:px-4 py-1 flex justify-end">
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
