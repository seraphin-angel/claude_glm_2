import { TodoPage } from '@/components/todos/TodoPage'

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-2xl px-4">
        <h1 className="mb-8 text-3xl font-bold text-gray-900">ToDo App</h1>
        <TodoPage />
      </div>
    </main>
  )
}
