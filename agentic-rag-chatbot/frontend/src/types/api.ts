export interface ApiResponse<T> {
  readonly success: boolean
  readonly data?: T
  readonly error?: string
}

export interface ChatStartData {
  readonly thread_id: string
  readonly status: string
}
