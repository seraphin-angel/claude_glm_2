import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { Message } from '@/types/message'
import { MessageBubble } from './MessageBubble'
import { MarkdownRenderer } from './MarkdownRenderer'
import { TypingIndicator } from './TypingIndicator'
import { SuggestChips } from './SuggestChips'
import { ScrollToBottomButton } from './ScrollToBottomButton'

const SCROLL_THRESHOLD = 100

interface MessageListProps {
  readonly messages: readonly Message[]
  readonly streamingContent: string
  readonly isStreaming: boolean
  readonly onSuggestSelect: (question: string) => void
}

export function MessageList({ messages, streamingContent, isStreaming, onSuggestSelect }: MessageListProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const [isNearBottom, setIsNearBottom] = useState(true)

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const viewport = viewportRef.current
    if (viewport) {
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior,
      })
    }
  }

  const handleScroll = () => {
    const viewport = viewportRef.current
    if (!viewport) return

    const { scrollTop, scrollHeight, clientHeight } = viewport
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight
    setIsNearBottom(distanceFromBottom < SCROLL_THRESHOLD)
  }

  // Auto-scroll when new messages arrive and user is near bottom
  useEffect(() => {
    if (isNearBottom && viewportRef.current) {
      // Use instant scroll during streaming to avoid lag
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight
    }
  }, [messages, streamingContent, isNearBottom])

  // Set up scroll event listener on the viewport
  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport) return

    // Find the actual scrollable viewport element
    const scrollableViewport = viewport.closest('[data-radix-scroll-area-viewport]') as HTMLDivElement | null
    if (scrollableViewport) {
      scrollableViewport.addEventListener('scroll', handleScroll)
      return () => scrollableViewport.removeEventListener('scroll', handleScroll)
    }
  }, [])

  return (
    <ScrollArea className="flex-1 px-4 relative">
      <div ref={viewportRef} className="py-4 space-y-2" role="log" aria-live="polite">
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

      {/* 最新メッセージへボタン */}
      <ScrollToBottomButton
        isVisible={!isNearBottom}
        onClick={() => scrollToBottom('smooth')}
      />
    </ScrollArea>
  )
}
