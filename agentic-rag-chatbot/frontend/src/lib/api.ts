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

/**
 * 汎用APIリクエストラッパー
 * エラーハンドリングとネットワークエラー変換を統一
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })

    if (!response.ok) {
      throw new Error(await createHttpErrorMessage(response))
    }

    return (await response.json()) as ApiResponse<T>
  } catch (error) {
    throw handleNetworkError(error)
  }
}

export async function sendMessage(
  message: string,
  threadId: string | null = null,
  imageData?: string,
): Promise<ApiResponse<ChatStartData>> {
  return apiRequest<ChatStartData>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, thread_id: threadId, image_data: imageData ?? null }),
  })
}

export async function uploadImage(
  imageData: string,
  filename: string,
  mimeType: string,
): Promise<ApiResponse<{ image_id: string }>> {
  return apiRequest<{ image_id: string }>('/chat/image', {
    method: 'POST',
    body: JSON.stringify({ image_data: imageData, filename, mime_type: mimeType }),
  })
}

export async function resumeChat(
  threadId: string,
  requestId: string,
  userResponse: string,
): Promise<ApiResponse<ChatStartData>> {
  return apiRequest<ChatStartData>(`/chat/resume/${threadId}`, {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId, response: userResponse }),
  })
}

export async function sendFeedback(
  messageId: string,
  rating: 'positive' | 'negative',
): Promise<ApiResponse<void>> {
  return apiRequest<void>('/feedback', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, rating }),
  })
}
