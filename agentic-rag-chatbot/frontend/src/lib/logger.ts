/**
 * 環境に応じたロギングユーティリティ
 * 開発環境でのみコンソールに出力し、本番環境では何もしない
 */

type LogLevel = 'error' | 'warn' | 'info' | 'debug'

type LogFunction = (context: string, data: Record<string, unknown>) => void

// テスト用の環境制御フラグ
let _isDevelopmentOverride: boolean | null = null

/**
 * 内部用: 開発環境かどうかを判定
 */
function checkIsDevelopment(): boolean {
  // テスト用のオーバーライドがあればそれを使用
  if (_isDevelopmentOverride !== null) {
    return _isDevelopmentOverride
  }
  // Viteの環境変数を優先、フォールバックでNODE_ENVをチェック
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env.DEV === true
  }
  return process.env.NODE_ENV !== 'production'
}

function createLogFunction(level: LogLevel): LogFunction {
  return (context: string, data: Record<string, unknown>): void => {
    if (!checkIsDevelopment()) {
      return
    }

    const consoleMethod = console[level] as (...args: unknown[]) => void
    consoleMethod(`[${context}]`, data)
  }
}

export const logger = {
  error: createLogFunction('error'),
  warn: createLogFunction('warn'),
  info: createLogFunction('info'),
  debug: createLogFunction('debug'),
} as const

// テスト用のエクスポート
export function setIsDevelopment(value: boolean): void {
  _isDevelopmentOverride = value
}

export function __resetIsDevelopment(): void {
  _isDevelopmentOverride = null
}
