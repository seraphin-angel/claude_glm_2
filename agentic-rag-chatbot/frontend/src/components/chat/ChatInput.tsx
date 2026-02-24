import { useState, useCallback, useRef, useEffect, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send } from 'lucide-react'

interface ChatInputProps {
  readonly onSend: (message: string) => void
  readonly disabled: boolean
}

const LINE_HEIGHT = 20
const MAX_LINES = 5
const MAX_HEIGHT = LINE_HEIGHT * MAX_LINES

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`
    }
  }, [input])

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setInput('')
      const textarea = textareaRef.current
      if (textarea) {
        textarea.style.height = 'auto'
      }
    }
  }, [input, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div className="flex gap-2 p-3 sm:p-4 border-t bg-card" role="form">
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="質問を入力してください..."
        disabled={disabled}
        rows={1}
        className="flex-1"
        aria-label="メッセージ入力"
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        size="icon"
        aria-label="送信"
        className="min-w-[44px] min-h-[44px]"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}
