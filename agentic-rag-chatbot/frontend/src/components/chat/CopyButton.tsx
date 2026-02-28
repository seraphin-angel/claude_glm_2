import { useState } from 'react'
import { Check, Copy, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CopyButtonProps {
  readonly text: string
}

type CopyState = 'idle' | 'copied' | 'error'

export function CopyButton({ text }: CopyButtonProps) {
  const [copyState, setCopyState] = useState<CopyState>('idle')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopyState('copied')
      setTimeout(() => setCopyState('idle'), 2000)
    } catch (error) {
      console.error('Failed to copy text:', error)

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
        console.error('Fallback copy also failed:', fallbackError)
        setCopyState('error')
        setTimeout(() => setCopyState('idle'), 3000)
      }
    }
  }

  const getAriaLabel = () => {
    switch (copyState) {
      case 'copied':
        return 'コピー完了'
      case 'error':
        return 'コピー失敗'
      default:
        return 'コピー'
    }
  }

  const getTitle = () => {
    switch (copyState) {
      case 'copied':
        return 'コピー完了'
      case 'error':
        return 'コピーに失敗しました'
      default:
        return 'コピー'
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
      aria-label={getAriaLabel()}
      title={getTitle()}
    >
      {copyState === 'copied' ? (
        <Check className="w-4 h-4" />
      ) : copyState === 'error' ? (
        <AlertCircle className="w-4 h-4" />
      ) : (
        <Copy className="w-4 h-4" />
      )}
    </button>
  )
}
