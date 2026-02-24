import type { ApiResponse, ChatStartData } from '@/types/api'

const API_BASE = '/api'

export async function sendMessage(
  message: string,
  threadId: string | null = null,
): Promise<ApiResponse<ChatStartData>> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json() as Promise<ApiResponse<ChatStartData>>
}

export async function resumeChat(
  threadId: string,
  requestId: string,
  userResponse: string,
): Promise<ApiResponse<ChatStartData>> {
  const response = await fetch(`${API_BASE}/chat/resume/${threadId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId, response: userResponse }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json() as Promise<ApiResponse<ChatStartData>>
}

export async function sendFeedback(
  messageId: string,
  rating: 'positive' | 'negative',
): Promise<ApiResponse<void>> {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id: messageId, rating }),
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json() as Promise<ApiResponse<void>>
}
