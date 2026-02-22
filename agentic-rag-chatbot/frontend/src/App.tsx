import { ChatWindow } from '@/components/chat/ChatWindow'
import { ErrorBoundary } from '@/components/ErrorBoundary'

function App() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b bg-card px-6 py-4">
        <h1 className="text-xl font-bold text-foreground">
          製品サポート チャットボット
        </h1>
        <p className="text-sm text-muted-foreground">
          製品に関するご質問にお答えします
        </p>
      </header>
      <main className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-3xl h-[calc(100vh-120px)]">
          <ErrorBoundary>
            <ChatWindow />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  )
}

export default App
