'use client'

import { useEffect, useState } from 'react'
import { Todo } from '@/types/todo'
import { ApiResponse } from '@/types/api'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorMessage } from '@/components/ui/ErrorMessage'
import { TodoForm } from './TodoForm'
import { TodoList } from './TodoList'

function extractErrorMessage(json: ApiResponse<unknown>, fallback: string): string {
  if (!json.success) {
    return json.error
  }
  return fallback
}

export function TodoPage() {
  const [todos, setTodos] = useState<Todo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTodos = async () => {
      try {
        const res = await fetch('/api/todos')
        const json: ApiResponse<Todo[]> = await res.json()
        if (!res.ok) {
          throw new Error(extractErrorMessage(json, 'データの取得に失敗しました'))
        }
        if (json.success) {
          setTodos(json.data ?? [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'データの取得に失敗しました')
      } finally {
        setIsLoading(false)
      }
    }
    fetchTodos()
  }, [])

  const handleCreate = async (title: string) => {
    setError(null)
    try {
      const res = await fetch('/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
      const json: ApiResponse<Todo> = await res.json()
      if (!res.ok) {
        throw new Error(extractErrorMessage(json, 'タスクの作成に失敗しました'))
      }
      if (json.success) {
        setTodos((prev) => [json.data, ...prev])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'タスクの作成に失敗しました')
    }
  }

  const handleToggle = async (id: string, completed: boolean) => {
    setError(null)
    try {
      const res = await fetch(`/api/todos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: !completed }),
      })
      const json: ApiResponse<Todo> = await res.json()
      if (!res.ok) {
        throw new Error(extractErrorMessage(json, 'タスクの更新に失敗しました'))
      }
      if (json.success) {
        setTodos((prev) =>
          prev.map((t) => (t.id === id ? json.data : t))
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'タスクの更新に失敗しました')
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      const res = await fetch(`/api/todos/${id}`, {
        method: 'DELETE',
      })
      const json: ApiResponse<null> = await res.json()
      if (!res.ok) {
        throw new Error(extractErrorMessage(json, 'タスクの削除に失敗しました'))
      }
      setTodos((prev) => prev.filter((t) => t.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'タスクの削除に失敗しました')
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <TodoForm onCreate={handleCreate} />
      {error && (
        <ErrorMessage message={error} data-testid="page-error" />
      )}
      {isLoading ? (
        <div className="flex justify-center py-8" data-testid="loading-spinner">
          <Spinner />
        </div>
      ) : (
        <TodoList todos={todos} onToggle={handleToggle} onDelete={handleDelete} />
      )}
    </div>
  )
}
