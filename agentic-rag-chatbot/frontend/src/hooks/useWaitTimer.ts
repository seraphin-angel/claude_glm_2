import { useState, useEffect } from 'react'

interface UseWaitTimerReturn {
  readonly waitTime: number
  readonly showWarning: boolean
  readonly showError: boolean
}

/**
 * ストリーミング中の待機時間を監視するフック
 * 30秒以上で警告表示、60秒以上でエラー表示
 */
export function useWaitTimer(isStreaming: boolean): UseWaitTimerReturn {
  const [waitTime, setWaitTime] = useState(0)

  useEffect(() => {
    if (!isStreaming) {
      setWaitTime(0)
      return
    }

    const interval = setInterval(() => {
      setWaitTime((t) => t + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [isStreaming])

  return {
    waitTime,
    showWarning: waitTime >= 30,
    showError: waitTime >= 60,
  }
}
