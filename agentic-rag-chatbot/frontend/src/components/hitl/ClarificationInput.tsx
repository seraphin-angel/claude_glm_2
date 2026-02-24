import { useState, useCallback, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send } from 'lucide-react'

interface ClarificationInputProps {
  readonly onSubmit: (text: string) => void
  readonly disabled: boolean
  readonly placeholder?: string
}

export function ClarificationInput({ onSubmit, disabled, placeholder }: ClarificationInputProps) {
  const [value, setValue] = useState('')

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim()
    if (trimmed && !disabled) {
      onSubmit(trimmed)
      setValue('')
    }
  }, [value, disabled, onSubmit])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit],
  )

  return (
    <div className="flex gap-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? '回答を入力してください...'}
        disabled={disabled}
        className="flex-1"
        aria-label="回答入力"
      />
      <Button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        size="icon"
        aria-label="回答を送信"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  )
}
