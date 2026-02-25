import type { Message } from '@/types/message'
import { cn } from '@/lib/utils'
import { MarkdownRenderer } from './MarkdownRenderer'
import { MessageFeedback } from './MessageFeedback'
import { CopyButton } from './CopyButton'
import { SourceCitations } from './SourceCitations'

interface MessageBubbleProps {
  readonly message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start',
      )}
    >
      <div
        role="article"
        aria-label={isUser ? 'ユーザーのメッセージ' : 'アシスタントのメッセージ'}
        className={cn(
          'max-w-[90%] sm:max-w-[80%] rounded-2xl px-4 py-3',
          'group relative',
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-md'
            : 'bg-muted text-foreground rounded-bl-md',
        )}
      >
        {!isUser && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <CopyButton text={message.content} />
          </div>
        )}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        ) : (
          <div className="text-sm">
            <MarkdownRenderer content={message.content} />
          </div>
        )}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitations sources={message.sources} qualityScore={message.qualityScore} />
        )}
        <time
          className={cn(
            'text-[10px] mt-1 block',
            isUser ? 'text-primary-foreground/70' : 'text-muted-foreground',
          )}
        >
          {message.timestamp.toLocaleTimeString('ja-JP', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
        {!isUser && <MessageFeedback messageId={message.id} />}
      </div>
    </div>
  )
}
