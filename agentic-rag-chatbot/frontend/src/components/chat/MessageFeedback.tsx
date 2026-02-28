import { useState } from 'react'
import { ThumbsDown, ThumbsUp, RotateCcw } from 'lucide-react'
import { sendFeedback } from '@/lib/api'
import { cn } from '@/lib/utils'
import { logger } from '@/lib/logger'

interface MessageFeedbackProps {
  readonly messageId: string
}

type FeedbackRating = 'positive' | 'negative' | null

export function MessageFeedback({ messageId }: MessageFeedbackProps) {
  const [selected, setSelected] = useState<FeedbackRating>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastAttemptedRating, setLastAttemptedRating] = useState<'positive' | 'negative' | null>(null)

  async function handleFeedback(rating: 'positive' | 'negative') {
    if (isSubmitting) return
    const next = selected === rating ? null : rating

    setSelected(next)
    setError(null)

    if (next === null) return

    setIsSubmitting(true)
    setLastAttemptedRating(rating)
    try {
      await sendFeedback(messageId, next)
    } catch (err) {
      // 送信失敗時は選択状態を戻す（UIの楽観的更新を元に戻す）
      setSelected(null)
      const errorMessage = err instanceof Error ? err.message : '送信に失敗しました'
      setError(errorMessage)
      logger.error('MessageFeedback', {
        message: 'Failed to send feedback',
        messageId,
        rating,
        error: errorMessage,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRetry() {
    if (!lastAttemptedRating || isSubmitting) return

    setError(null)
    setIsSubmitting(true)
    try {
      await sendFeedback(messageId, lastAttemptedRating)
      setSelected(lastAttemptedRating)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '送信に失敗しました'
      setError(errorMessage)
      logger.error('MessageFeedback', {
        message: 'Retry failed',
        messageId,
        rating: lastAttemptedRating,
        error: errorMessage,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="flex items-center gap-1 mt-1"
      role="group"
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
      {error && (
        <>
          <span className="text-xs text-red-500 ml-2" role="alert">
            送信に失敗しました
          </span>
          <button
            type="button"
            onClick={handleRetry}
            disabled={isSubmitting}
            aria-label="再試行"
            className={cn(
              'rounded p-1 transition-colors text-muted-foreground hover:text-foreground',
              isSubmitting && 'opacity-50 cursor-not-allowed',
            )}
          >
            <RotateCcw size={12} />
          </button>
        </>
      )}
    </div>
  )
}
