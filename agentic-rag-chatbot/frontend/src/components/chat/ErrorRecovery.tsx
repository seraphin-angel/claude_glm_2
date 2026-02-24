import { RefreshCw, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorRecoveryProps {
  readonly error: string
  readonly onRetry: () => void
  readonly onReset: () => void
}

function getErrorMessage(error: string): { message: string; showRetry: boolean } {
  if (error.includes('接続')) {
    return {
      message: '接続に失敗しました。ネットワークを確認してください。',
      showRetry: true,
    }
  }
  if (error.includes('429')) {
    return {
      message: 'リクエストが多すぎます。しばらくお待ちください。',
      showRetry: false,
    }
  }
  return {
    message: error,
    showRetry: true,
  }
}

export function ErrorRecovery({ error, onRetry, onReset }: ErrorRecoveryProps) {
  const { message, showRetry } = getErrorMessage(error)

  return (
    <div
      className="px-4 py-3 bg-red-50 dark:bg-red-950 border-t"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-red-600 dark:text-red-400">{message}</p>
          <div className="flex items-center gap-3 mt-2">
            {showRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="gap-1.5 text-red-600 dark:text-red-400 border-red-300 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                リトライ
              </Button>
            )}
            <button
              type="button"
              onClick={onReset}
              className="text-sm text-red-500 dark:text-red-400 underline hover:text-red-700 dark:hover:text-red-300"
            >
              新しい会話を始める
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
