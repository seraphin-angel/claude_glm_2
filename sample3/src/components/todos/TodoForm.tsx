'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

interface TodoFormProps {
  onCreate: (title: string) => Promise<void>
}

export function TodoForm({ onCreate }: TodoFormProps) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const validate = (title: string): string | null => {
    if (title.trim().length === 0) {
      return 'タイトルを入力してください'
    }
    if (title.trim().length > 500) {
      return 'タイトルは500文字以内で入力してください'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate(value)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await onCreate(value.trim())
      setValue('')
    } catch (err) {
      const message = err instanceof Error ? err.message : '送信に失敗しました'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex gap-2">
        <div className="flex-1">
          <Input
            value={value}
            onChange={(v) => {
              setValue(v)
              if (error) setError(null)
            }}
            placeholder="新しいタスクを入力..."
            error={error ?? undefined}
            disabled={isSubmitting}
            data-testid="todo-input"
          />
        </div>
        <Button
          type="submit"
          loading={isSubmitting}
          disabled={isSubmitting}
          data-testid="add-todo-button"
        >
          追加
        </Button>
      </div>
      {error && (
        <p className="text-xs text-red-600" data-testid="title-error">
          {error}
        </p>
      )}
    </form>
  )
}
