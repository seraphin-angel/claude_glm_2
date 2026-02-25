import type { ApiResponse, ChatStartData } from '@/types/api'

const API_BASE = '/api'

/**
 * ネットワークエラーをユーザーフレンドリーなメッセージに変換
 */
function handleNetworkError(error: unknown): never {
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    throw new Error('ネットワークに接続できません。インターネット接続を確認してください。')
  }
  // JSONパースエラー（SyntaxError）の場合
  // error.name を使用して、クロスレルム(iframe/VM)のエラーにも対応
  if (error instanceof Error && error.name === 'SyntaxError') {
    throw new Error('サーバーからの応答を解析できませんでした。しばらく待ってから再試行してください。')
  }
  throw error
}

/**
 * HTTPエラーレスポンスから詳細なエラーメッセージを生成
 */
async function createHttpErrorMessage(response: Response): Promise<string> {
  const statusText = response.statusText ? ` ${response.statusText}` : ''
  let errorBody = ''
  try {
    errorBody = await response.text()
    if (errorBody) {
      errorBody = ` - ${errorBody.substring(0, 100)}`
    }
  } catch {
    // レスポンスボディの読み取りに失敗した場合は無視
  }
  return `API error: ${response.status}${statusText}${errorBody}`
}

export async function sendMessage(
  message: string,
  threadId: string | null = null,
): Promise<ApiResponse<ChatStartData>> {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, thread_id: threadId }),
    })

    if (!response.ok) {
      throw new Error(await createHttpErrorMessage(response))
    }

    return (await response.json()) as ApiResponse<ChatStartData>
  } catch (error) {
    throw handleNetworkError(error)
  }
}

export async function resumeChat(
  threadId: string,
  requestId: string,
  userResponse: string,
): Promise<ApiResponse<ChatStartData>> {
  try {
    const response = await fetch(`${API_BASE}/chat/resume/${threadId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId, response: userResponse }),
    })

    if (!response.ok) {
      throw new Error(await createHttpErrorMessage(response))
    }

    return (await response.json()) as ApiResponse<ChatStartData>
  } catch (error) {
    throw handleNetworkError(error)
  }
}

export async function sendFeedback(
  messageId: string,
  rating: 'positive' | 'negative',
): Promise<ApiResponse<void>> {
  try {
    const response = await fetch(`${API_BASE}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, rating }),
    })

    if (!response.ok) {
      throw new Error(await createHttpErrorMessage(response))
    }

    return (await response.json()) as ApiResponse<void>
  } catch (error) {
    throw handleNetworkError(error)
  }
}
