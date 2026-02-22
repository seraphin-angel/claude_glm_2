export interface Message {
  readonly id: string
  readonly role: 'user' | 'assistant'
  readonly content: string
  readonly timestamp: Date
}

export interface HITLRequest {
  readonly request_id: string
  readonly question: string
  readonly options: string[] | null
  readonly input_type: 'buttons' | 'text'
}

export type ChatEventType =
  | 'token'
  | 'hitl_request'
  | 'message_complete'
  | 'error'
  | 'done'
  | 'tool_start'
  | 'tool_end'
  | 'ping'

export interface ChatEvent {
  readonly type: ChatEventType
  readonly content?: string
  readonly request_id?: string
  readonly question?: string
  readonly options?: string[]
  readonly input_type?: string
  readonly tool_name?: string
}

export type ChatStatus = 'idle' | 'streaming' | 'hitl_pending' | 'error'
