import { ScrollArea } from '@/components/ui/scroll-area'
import type { Message } from '@/types/message'
import { useAutoScroll } from '@/hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

interface MessageListProps {
  readonly messages: readonly Message[]
  readonly streamingContent: string
  readonly isStreaming: boolean
}

export function MessageList({ messages, streamingContent, isStreaming }: MessageListProps) {
  const scrollRef = useAutoScroll<HTMLDivElement>([messages, streamingContent])

  return (
    <ScrollArea className="flex-1 px-4">
      <div ref={scrollRef} className="py-4 space-y-2">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <p className="text-lg font-medium">製品サポートへようこそ</p>
            <p className="text-sm mt-2">製品に関するご質問をお気軽にどうぞ</p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* ストリーミング中の部分テキスト表示 */}
        {isStreaming && streamingContent && (
          <div className="flex w-full justify-start mb-4">
            <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-muted text-foreground px-4 py-3">
              <p className="text-sm whitespace-pre-wrap break-words">
                {streamingContent}
              </p>
            </div>
          </div>
        )}

        {/* タイピングインジケーター */}
        {isStreaming && !streamingContent && (
          <TypingIndicator />
        )}
      </div>
    </ScrollArea>
  )
}
