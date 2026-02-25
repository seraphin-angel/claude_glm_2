import { Button } from '@/components/ui/button'
import { AlertTriangle, XCircle } from 'lucide-react'

interface WaitNotificationProps {
  readonly showWarning: boolean
  readonly showError: boolean
  readonly onCancel: () => void
}

export function WaitNotification({ showWarning, showError, onCancel }: WaitNotificationProps) {
  if (!showWarning && !showError) {
    return null
  }

  // エラー状態（60秒以上）
  if (showError) {
    return (
      <div
        className="mx-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between animate-in fade-in slide-in-from-top-2 duration-300"
        role="alert"
      >
        <div className="flex items-center gap-2 text-red-700">
          <XCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">タイムアウトしました</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="text-red-700 border-red-300 hover:bg-red-100 hover:text-red-800"
        >
          キャンセルして再試行
        </Button>
      </div>
    )
  }

  // 警告状態（30秒以上）
  return (
    <div
      className="mx-4 mb-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-300"
      role="status"
    >
      <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
      <span className="text-sm text-yellow-700">処理に時間がかかっています...</span>
    </div>
  )
}
