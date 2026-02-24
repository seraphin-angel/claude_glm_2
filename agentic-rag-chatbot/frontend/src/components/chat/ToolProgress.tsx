import { getToolLabel } from '@/lib/tool-labels'

interface ToolHistoryEntry {
  readonly name: string
  readonly status: 'running' | 'done'
}

interface ToolProgressProps {
  readonly toolHistory: readonly ToolHistoryEntry[]
}

export function ToolProgress({ toolHistory }: ToolProgressProps) {
  if (toolHistory.length === 0) return null

  return (
    <div className="px-4 py-2 bg-blue-50 dark:bg-blue-950 border-b" role="status" aria-live="polite">
      <ul className="flex flex-col gap-1">
        {toolHistory.map((entry, index) => (
          <li key={index} className="flex items-center gap-2">
            {entry.status === 'running' ? (
              <svg
                className="w-3 h-3 text-blue-500 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              <svg
                className="w-3 h-3 text-green-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={3}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
            <span
              className={`text-xs ${
                entry.status === 'running'
                  ? 'text-blue-700 dark:text-blue-300'
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {getToolLabel(entry.name)}
              {entry.status === 'running' && ' を実行中...'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
