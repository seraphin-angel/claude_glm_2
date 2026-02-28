import { useState } from 'react'
import { Check, Copy, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { logger } from '@/lib/logger'

interface CopyButtonProps {
  readonly text: string
}

type CopyState = 'idle' | 'copied' | 'error'

// 各状態に対応するラベル定義（aria-label と title を統合）
const STATE_LABELS: Record<CopyState, { aria: string; title: string }> = {
  copied: { aria: 'コピー完了', title: 'コピー完了' },
  error: { aria: 'コピー失敗', title: 'コピーに失敗しました' },
  idle: { aria: 'コピー', title: 'コピー' },
}

// 状態に応じたアイコンを返す
function getStateIcon(state: CopyState) {
  switch (state) {
    case 'copied':
      return <Check className="w-4 h-4" />
    case 'error':
      return <AlertCircle className="w-4 h-4" />
    default:
      return <Copy className="w-4 h-4" />
  }
}

export function CopyButton({ text }: CopyButtonProps) {
  const [copyState, setCopyState] = useState<CopyState>('idle')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopyState('copied')
      setTimeout(() => setCopyState('idle'), 2000)
    } catch (error) {
      logger.error('CopyButton', {
        message: 'Clipboard API failed',
        error: error instanceof Error ? error.message : String(error),
      })

      // Fallback: traditional selection + copy
      try {
        const textArea = document.createElement('textarea')
        textArea.value = text
        textArea.style.position = 'fixed'
        textArea.style.left = '-9999px'
        document.body.appendChild(textArea)
        textArea.select()
        const success = document.execCommand('copy')
        document.body.removeChild(textArea)

        if (success) {
          setCopyState('copied')
          setTimeout(() => setCopyState('idle'), 2000)
        } else {
          setCopyState('error')
          setTimeout(() => setCopyState('idle'), 3000)
        }
      } catch (fallbackError) {
        logger.error('CopyButton', {
          message: 'Fallback copy failed',
          error: fallbackError instanceof Error ? fallbackError.message : String(fallbackError),
        })
        setCopyState('error')
        setTimeout(() => setCopyState('idle'), 3000)
      }
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'p-1.5 rounded-md transition-all duration-200',
        'hover:bg-accent hover:text-accent-foreground',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        copyState === 'copied' && 'text-green-600',
        copyState === 'error' && 'text-red-500',
        copyState === 'idle' && 'text-muted-foreground',
      )}
      aria-label={STATE_LABELS[copyState].aria}
      title={STATE_LABELS[copyState].title}
    >
      {getStateIcon(copyState)}
    </button>
  )
}
