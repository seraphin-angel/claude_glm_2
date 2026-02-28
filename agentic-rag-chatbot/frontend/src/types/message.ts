import { z } from 'zod'

// ============================================
// Zod Schemas for Runtime Validation
// ============================================

export const SourceDocumentSchema = z.object({
  id: z.string(),
  title: z.string(),
  section: z.string(),
  score: z.number(),
  snippet: z.string(),
})

export const QualityScoreSchema = z.object({
  is_relevant: z.boolean(),
  confidence: z.number(),
  reasoning: z.string(),
})

// UserMessage Schema - sources, qualityScore を持たない
export const UserMessageSchema = z.object({
  id: z.string(),
  role: z.literal('user'),
  content: z.string(),
  timestamp: z.coerce.date(),
})

// AssistantMessage Schema - sources, qualityScore を持つ
export const AssistantMessageSchema = z.object({
  id: z.string(),
  role: z.literal('assistant'),
  content: z.string(),
  timestamp: z.coerce.date(),
  sources: z.array(SourceDocumentSchema).optional(),
  qualityScore: QualityScoreSchema.optional(),
})

// Message Schema (discriminated union)
export const MessageSchema = z.discriminatedUnion('role', [
  UserMessageSchema,
  AssistantMessageSchema,
])

export const HITLRequestSchema = z.object({
  request_id: z.string(),
  question: z.string(),
  options: z.array(z.string()).nullable(),
  input_type: z.enum(['buttons', 'text']),
})

// ============================================
// Individual Event Schemas
// ============================================

export const TokenEventSchema = z.object({
  type: z.literal('token'),
  content: z.string(),
  // 重複排除用のオプションフィールド（サーバーから送信される場合がある）
  message_id: z.string().optional(),
})

export const HitlRequestEventSchema = z.object({
  type: z.literal('hitl_request'),
  request_id: z.string(),
  question: z.string(),
  options: z.array(z.string()).nullable(),
  input_type: z.enum(['buttons', 'text']),
})

export const MessageCompleteEventSchema = z.object({
  type: z.literal('message_complete'),
  content: z.string(),
})

export const ErrorEventSchema = z.object({
  type: z.literal('error'),
  content: z.string(),
})

export const DoneEventSchema = z.object({
  type: z.literal('done'),
})

export const ToolStartEventSchema = z.object({
  type: z.literal('tool_start'),
  tool_name: z.string(),
})

export const ToolEndEventSchema = z.object({
  type: z.literal('tool_end'),
})

export const PingEventSchema = z.object({
  type: z.literal('ping'),
})

export const SourceEventSchema = z.object({
  type: z.literal('source'),
  documents: z.array(SourceDocumentSchema),
})

export const QualityEventSchema = z.object({
  type: z.literal('quality'),
  is_relevant: z.boolean(),
  confidence: z.number(),
  reasoning: z.string().optional(),
})

// ChatEvent Schema (discriminated union)
export const ChatEventSchema = z.discriminatedUnion('type', [
  TokenEventSchema,
  HitlRequestEventSchema,
  MessageCompleteEventSchema,
  ErrorEventSchema,
  DoneEventSchema,
  ToolStartEventSchema,
  ToolEndEventSchema,
  PingEventSchema,
  SourceEventSchema,
  QualityEventSchema,
])

// ============================================
// TypeScript Interfaces
// ============================================

export interface SourceDocument {
  readonly id: string
  readonly title: string
  readonly section: string
  readonly score: number
  readonly snippet: string
}

export interface QualityScore {
  readonly is_relevant: boolean
  readonly confidence: number
  readonly reasoning: string
}

// UserMessage - sources, qualityScore を持たない
export interface UserMessage {
  readonly id: string
  readonly role: 'user'
  readonly content: string
  readonly timestamp: Date
}

// AssistantMessage - sources, qualityScore を持つ
export interface AssistantMessage {
  readonly id: string
  readonly role: 'assistant'
  readonly content: string
  readonly timestamp: Date
  readonly sources?: readonly SourceDocument[]
  readonly qualityScore?: QualityScore
}

// 判別可能ユニオン
export type Message = UserMessage | AssistantMessage

// 型ガード関数
export function isUserMessage(message: Message): message is UserMessage {
  return message.role === 'user'
}

export function isAssistantMessage(message: Message): message is AssistantMessage {
  return message.role === 'assistant'
}

// ファクトリー関数
export function createUserMessage(content: string): UserMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: new Date(),
  }
}

export function createAssistantMessage(
  content: string,
  sources?: readonly SourceDocument[],
  qualityScore?: QualityScore,
): AssistantMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content,
    timestamp: new Date(),
    sources,
    qualityScore,
  }
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
  | 'source'
  | 'quality'

// Individual event types for Discriminated Union
export interface TokenEvent {
  readonly type: 'token'
  readonly content: string
  readonly message_id?: string
}

export interface HitlRequestEvent {
  readonly type: 'hitl_request'
  readonly request_id: string
  readonly question: string
  readonly options: string[] | null
  readonly input_type: 'buttons' | 'text'
}

export interface MessageCompleteEvent {
  readonly type: 'message_complete'
  readonly content: string
}

export interface ErrorEvent {
  readonly type: 'error'
  readonly content: string
}

export interface DoneEvent {
  readonly type: 'done'
}

export interface ToolStartEvent {
  readonly type: 'tool_start'
  readonly tool_name: string
}

export interface ToolEndEvent {
  readonly type: 'tool_end'
}

export interface PingEvent {
  readonly type: 'ping'
}

export interface SourceEvent {
  readonly type: 'source'
  readonly documents: readonly SourceDocument[]
}

export interface QualityEvent {
  readonly type: 'quality'
  readonly is_relevant: boolean
  readonly confidence: number
  readonly reasoning?: string
}

// Discriminated Union type - use this for event handling
export type ChatEvent =
  | TokenEvent
  | HitlRequestEvent
  | MessageCompleteEvent
  | ErrorEvent
  | DoneEvent
  | ToolStartEvent
  | ToolEndEvent
  | PingEvent
  | SourceEvent
  | QualityEvent

export type ChatStatus = 'idle' | 'streaming' | 'hitl_pending' | 'error'
