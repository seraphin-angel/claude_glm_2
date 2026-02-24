import { useState } from 'react'
import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { sendFeedback } from '@/lib/api'
import { cn } from '@/lib/utils'

interface MessageFeedbackProps {
  readonly messageId: string
}

type FeedbackRating = 'positive' | 'negative' | null

export function MessageFeedback({ messageId }: MessageFeedbackProps) {
  const [selected, setSelected] = useState<FeedbackRating>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleFeedback(rating: 'positive' | 'negative') {
    if (isSubmitting) return
    const next = selected === rating ? null : rating

    setSelected(next)

    if (next === null) return

    setIsSubmitting(true)
    try {
      await sendFeedback(messageId, next)
    } catch {
      // 送信失敗時は選択状態を戻す（UIの楽観的更新を元に戻す）
      setSelected(selected)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="flex items-center gap-1 mt-1"
      aria-label="メッセージへのフィードバック"
    >
      <button
        type="button"
        onClick={() => handleFeedback('positive')}
        disabled={isSubmitting}
        aria-label="役に立った"
        aria-pressed={selected === 'positive'}
        className={cn(
          'rounded p-1 transition-colors',
          'text-muted-foreground hover:text-foreground',
          selected === 'positive' && 'text-green-600 hover:text-green-700',
          isSubmitting && 'opacity-50 cursor-not-allowed',
        )}
      >
        <ThumbsUp size={14} />
      </button>
      <button
        type="button"
        onClick={() => handleFeedback('negative')}
        disabled={isSubmitting}
        aria-label="役に立たなかった"
        aria-pressed={selected === 'negative'}
        className={cn(
          'rounded p-1 transition-colors',
          'text-muted-foreground hover:text-foreground',
          selected === 'negative' && 'text-red-500 hover:text-red-600',
          isSubmitting && 'opacity-50 cursor-not-allowed',
        )}
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  )
}
