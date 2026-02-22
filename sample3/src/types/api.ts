export type ApiResponse<T> =
  | { success: true; data: T; error?: never; meta?: { total: number; page: number; limit: number } }
  | { success: false; error: string; data?: never; meta?: never }
