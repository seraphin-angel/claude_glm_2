import { ScrollArea } from '@/components/ui/scroll-area'
import type { Message } from '@/types/message'
import { useAutoScroll } from '@/hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { MarkdownRenderer } from './MarkdownRenderer'
import { TypingIndicator } from './TypingIndicator'
import { SuggestChips } from './SuggestChips'

interface MessageListProps {
  readonly messages: readonly Message[]
  readonly streamingContent: string
  readonly isStreaming: boolean
  readonly onSuggestSelect: (question: string) => void
}

export function MessageList({ messages, streamingContent, isStreaming, onSuggestSelect }: MessageListProps) {
  const scrollRef = useAutoScroll<HTMLDivElement>([messages, streamingContent])

  return (
    <ScrollArea className="flex-1 px-4">
      <div ref={scrollRef} className="py-4 space-y-2" role="log" aria-live="polite">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <p className="text-lg font-medium">製品サポートへようこそ</p>
            <p className="text-sm mt-2">製品に関するご質問をお気軽にどうぞ</p>
            <SuggestChips onSelect={onSuggestSelect} />
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* ストリーミング中の部分テキスト表示 */}
        {isStreaming && streamingContent && (
          <div className="flex w-full justify-start mb-4">
            <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-muted text-foreground px-4 py-3" aria-live="polite">
              <MarkdownRenderer content={streamingContent} />
              <span className="inline-block w-[2px] h-[1em] bg-foreground ml-0.5 animate-blink align-middle" />
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
