import { describe, it, expect } from 'vitest'
import type {
  ChatEvent,
  TokenEvent,
  HitlRequestEvent,
  MessageCompleteEvent,
  ErrorEvent,
  DoneEvent,
  ToolStartEvent,
  ToolEndEvent,
  PingEvent,
  SourceEvent,
  QualityEvent,
  Message,
  UserMessage,
  AssistantMessage,
} from '../message'
import {
  isUserMessage,
  isAssistantMessage,
  createUserMessage,
  createAssistantMessage,
} from '../message'

// Type-level tests - these will fail at compile time if types are wrong
type _TestTokenEventHasContent = TokenEvent extends { readonly content: string } ? true : false
type _TestHitlRequestHasRequiredFields = HitlRequestEvent extends {
  readonly request_id: string
  readonly question: string
  readonly options: string[] | null
  readonly input_type: 'buttons' | 'text'
} ? true : false
type _TestDoneEventHasNoExtraFields = DoneEvent extends { readonly type: 'done' } ? true : false

describe('ChatEvent Discriminated Union Types', () => {
  describe('TokenEvent', () => {
    it('validates token event with required content', () => {
      const event: TokenEvent = { type: 'token', content: 'hello' }
      expect(event.type).toBe('token')
      expect(event.content).toBe('hello')
    })

    it('allows empty string content', () => {
      const event: TokenEvent = { type: 'token', content: '' }
      expect(event.content).toBe('')
    })
  })

  describe('HitlRequestEvent', () => {
    it('validates hitl_request event with all required fields', () => {
      const event: HitlRequestEvent = {
        type: 'hitl_request',
        request_id: 'req-123',
        question: 'Select an option',
        options: ['A', 'B', 'C'],
        input_type: 'buttons',
      }
      expect(event.request_id).toBe('req-123')
      expect(event.options).toEqual(['A', 'B', 'C'])
      expect(event.input_type).toBe('buttons')
    })

    it('allows null options', () => {
      const event: HitlRequestEvent = {
        type: 'hitl_request',
        request_id: 'req-456',
        question: 'Enter text',
        options: null,
        input_type: 'text',
      }
      expect(event.options).toBeNull()
    })
  })

  describe('MessageCompleteEvent', () => {
    it('validates message_complete event with content', () => {
      const event: MessageCompleteEvent = {
        type: 'message_complete',
        content: 'Full message',
      }
      expect(event.content).toBe('Full message')
    })
  })

  describe('ErrorEvent', () => {
    it('validates error event with content', () => {
      const event: ErrorEvent = {
        type: 'error',
        content: 'Something went wrong',
      }
      expect(event.content).toBe('Something went wrong')
    })
  })

  describe('DoneEvent', () => {
    it('validates done event without extra fields', () => {
      const event: DoneEvent = { type: 'done' }
      expect(event.type).toBe('done')
    })
  })

  describe('ToolStartEvent', () => {
    it('validates tool_start event with tool_name', () => {
      const event: ToolStartEvent = {
        type: 'tool_start',
        tool_name: 'search',
      }
      expect(event.tool_name).toBe('search')
    })
  })

  describe('ToolEndEvent', () => {
    it('validates tool_end event without extra fields', () => {
      const event: ToolEndEvent = { type: 'tool_end' }
      expect(event.type).toBe('tool_end')
    })
  })

  describe('PingEvent', () => {
    it('validates ping event without extra fields', () => {
      const event: PingEvent = { type: 'ping' }
      expect(event.type).toBe('ping')
    })
  })

  describe('SourceEvent', () => {
    it('validates source event with documents', () => {
      const event: SourceEvent = {
        type: 'source',
        documents: [
          {
            id: 'doc-1',
            title: 'Document 1',
            section: 'Section A',
            score: 0.95,
            snippet: 'Some text...',
          },
        ],
      }
      expect(event.documents).toHaveLength(1)
      expect(event.documents[0].id).toBe('doc-1')
    })

    it('allows empty documents array', () => {
      const event: SourceEvent = {
        type: 'source',
        documents: [],
      }
      expect(event.documents).toHaveLength(0)
    })
  })

  describe('QualityEvent', () => {
    it('validates quality event with required fields', () => {
      const event: QualityEvent = {
        type: 'quality',
        is_relevant: true,
        confidence: 0.85,
      }
      expect(event.is_relevant).toBe(true)
      expect(event.confidence).toBe(0.85)
    })

    it('includes optional reasoning', () => {
      const event: QualityEvent = {
        type: 'quality',
        is_relevant: false,
        confidence: 0.3,
        reasoning: 'Not related to the query',
      }
      expect(event.reasoning).toBe('Not related to the query')
    })
  })

  describe('Type narrowing', () => {
    it('correctly narrows type in switch statement for token', () => {
      const event: ChatEvent = { type: 'token', content: 'test' }

      switch (event.type) {
        case 'token':
          // TypeScript should know event has content
          expect(event.content).toBe('test')
          break
        default:
          expect.fail('Should not reach default')
      }
    })

    it('correctly narrows type in switch statement for hitl_request', () => {
      const event: ChatEvent = {
        type: 'hitl_request',
        request_id: 'req-1',
        question: 'Pick one',
        options: ['A', 'B'],
        input_type: 'buttons',
      }

      switch (event.type) {
        case 'hitl_request':
          // TypeScript should know event has all required fields
          expect(event.request_id).toBe('req-1')
          expect(event.question).toBe('Pick one')
          expect(event.options).toEqual(['A', 'B'])
          expect(event.input_type).toBe('buttons')
          break
        default:
          expect.fail('Should not reach default')
      }
    })

    it('correctly narrows type in switch statement for source', () => {
      const event: ChatEvent = {
        type: 'source',
        documents: [
          { id: '1', title: 'Doc', section: 'S1', score: 0.9, snippet: 'text' },
        ],
      }

      switch (event.type) {
        case 'source':
          // TypeScript should know event has documents
          expect(event.documents).toHaveLength(1)
          break
        default:
          expect.fail('Should not reach default')
      }
    })

    it('correctly narrows type in switch statement for quality', () => {
      const event: ChatEvent = {
        type: 'quality',
        is_relevant: true,
        confidence: 0.95,
        reasoning: 'Highly relevant',
      }

      switch (event.type) {
        case 'quality':
          // TypeScript should know event has is_relevant and confidence
          expect(event.is_relevant).toBe(true)
          expect(event.confidence).toBe(0.95)
          expect(event.reasoning).toBe('Highly relevant')
          break
        default:
          expect.fail('Should not reach default')
      }
    })

    it('correctly handles done event without extra fields', () => {
      const event: ChatEvent = { type: 'done' }

      switch (event.type) {
        case 'done':
          // TypeScript should know event has no extra fields
          expect(event.type).toBe('done')
          break
        default:
          expect.fail('Should not reach default')
      }
    })
  })

  describe('Exhaustiveness check', () => {
    it('ensures all event types are handled', () => {
      const events: ChatEvent[] = [
        { type: 'token', content: 'a' },
        { type: 'hitl_request', request_id: 'r1', question: 'Q?', options: null, input_type: 'text' },
        { type: 'message_complete', content: 'done' },
        { type: 'error', content: 'err' },
        { type: 'done' },
        { type: 'tool_start', tool_name: 'tool' },
        { type: 'tool_end' },
        { type: 'ping' },
        { type: 'source', documents: [] },
        { type: 'quality', is_relevant: true, confidence: 1.0 },
      ]

      const handledTypes: string[] = []

      for (const event of events) {
        switch (event.type) {
          case 'token':
            handledTypes.push(event.type)
            break
          case 'hitl_request':
            handledTypes.push(event.type)
            break
          case 'message_complete':
            handledTypes.push(event.type)
            break
          case 'error':
            handledTypes.push(event.type)
            break
          case 'done':
            handledTypes.push(event.type)
            break
          case 'tool_start':
            handledTypes.push(event.type)
            break
          case 'tool_end':
            handledTypes.push(event.type)
            break
          case 'ping':
            handledTypes.push(event.type)
            break
          case 'source':
            handledTypes.push(event.type)
            break
          case 'quality':
            handledTypes.push(event.type)
            break
          default:
            // This should never happen with a complete discriminated union
            const _exhaustiveCheck: never = event
            throw new Error(`Unhandled event type: ${JSON.stringify(_exhaustiveCheck)}`)
        }
      }

      expect(handledTypes).toHaveLength(10)
    })
  })
})

// Type-level tests for Message discriminated union
type _TestUserMessageHasNoSources = UserMessage extends { readonly sources?: unknown } ? false : true
type _TestAssistantMessageHasSources = AssistantMessage extends { readonly sources?: unknown } ? true : false
type _TestUserMessageRole = UserMessage extends { readonly role: 'user' } ? true : false
type _TestAssistantMessageRole = AssistantMessage extends { readonly role: 'assistant' } ? true : false

describe('Message Discriminated Union Types', () => {
  describe('createUserMessage', () => {
    it('creates a valid user message', () => {
      const message = createUserMessage('Hello, world!')

      expect(message.role).toBe('user')
      expect(message.content).toBe('Hello, world!')
      expect(message.id).toBeDefined()
      expect(message.timestamp).toBeInstanceOf(Date)
    })

    it('creates user message without sources or qualityScore', () => {
      const message = createUserMessage('Test')

      // TypeScript ensures these properties don't exist on UserMessage
      expect(message).not.toHaveProperty('sources')
      expect(message).not.toHaveProperty('qualityScore')
    })
  })

  describe('createAssistantMessage', () => {
    it('creates a valid assistant message with content only', () => {
      const message = createAssistantMessage('Response text')

      expect(message.role).toBe('assistant')
      expect(message.content).toBe('Response text')
      expect(message.id).toBeDefined()
      expect(message.timestamp).toBeInstanceOf(Date)
      expect(message.sources).toBeUndefined()
      expect(message.qualityScore).toBeUndefined()
    })

    it('creates assistant message with sources', () => {
      const sources = [
        { id: '1', title: 'Doc', section: 'S1', score: 0.9, snippet: 'text' },
      ]
      const message = createAssistantMessage('Response', sources)

      expect(message.sources).toEqual(sources)
    })

    it('creates assistant message with qualityScore', () => {
      const qualityScore = {
        is_relevant: true,
        confidence: 0.95,
        reasoning: 'Highly relevant',
      }
      const message = createAssistantMessage('Response', undefined, qualityScore)

      expect(message.qualityScore).toEqual(qualityScore)
    })

    it('creates assistant message with both sources and qualityScore', () => {
      const sources = [
        { id: '1', title: 'Doc', section: 'S1', score: 0.9, snippet: 'text' },
      ]
      const qualityScore = {
        is_relevant: true,
        confidence: 0.95,
        reasoning: 'Highly relevant',
      }
      const message = createAssistantMessage('Response', sources, qualityScore)

      expect(message.sources).toEqual(sources)
      expect(message.qualityScore).toEqual(qualityScore)
    })
  })

  describe('isUserMessage type guard', () => {
    it('returns true for user messages', () => {
      const message = createUserMessage('User input')
      expect(isUserMessage(message)).toBe(true)
    })

    it('returns false for assistant messages', () => {
      const message = createAssistantMessage('Assistant response')
      expect(isUserMessage(message)).toBe(false)
    })
  })

  describe('isAssistantMessage type guard', () => {
    it('returns true for assistant messages', () => {
      const message = createAssistantMessage('Assistant response')
      expect(isAssistantMessage(message)).toBe(true)
    })

    it('returns false for user messages', () => {
      const message = createUserMessage('User input')
      expect(isAssistantMessage(message)).toBe(false)
    })
  })

  describe('Type narrowing with discriminated union', () => {
    it('correctly narrows type in switch statement for user message', () => {
      const message: Message = createUserMessage('Hello')

      switch (message.role) {
        case 'user':
          // TypeScript should know message is UserMessage
          expect(message.content).toBe('Hello')
          expect(message.role).toBe('user')
          break
        case 'assistant':
          expect.fail('Should not reach assistant case')
      }
    })

    it('correctly narrows type in switch statement for assistant message', () => {
      const sources = [
        { id: '1', title: 'Doc', section: 'S1', score: 0.9, snippet: 'text' },
      ]
      const qualityScore = {
        is_relevant: true,
        confidence: 0.95,
        reasoning: 'Highly relevant',
      }
      const message: Message = createAssistantMessage('Response', sources, qualityScore)

      switch (message.role) {
        case 'assistant':
          // TypeScript should know message is AssistantMessage
          expect(message.content).toBe('Response')
          expect(message.sources).toEqual(sources)
          expect(message.qualityScore).toEqual(qualityScore)
          break
        case 'user':
          expect.fail('Should not reach user case')
      }
    })

    it('handles mixed message array correctly', () => {
      const messages: Message[] = [
        createUserMessage('Question 1'),
        createAssistantMessage('Answer 1'),
        createUserMessage('Question 2'),
        createAssistantMessage('Answer 2', [
          { id: '1', title: 'Doc', section: 'S1', score: 0.9, snippet: 'text' },
        ]),
      ]

      const userMessages = messages.filter(isUserMessage)
      const assistantMessages = messages.filter(isAssistantMessage)

      expect(userMessages).toHaveLength(2)
      expect(assistantMessages).toHaveLength(2)
      expect(userMessages.every((m) => m.role === 'user')).toBe(true)
      expect(assistantMessages.every((m) => m.role === 'assistant')).toBe(true)
    })
  })

  describe('Exhaustiveness check for Message', () => {
    it('ensures all message types are handled', () => {
      const messages: Message[] = [
        createUserMessage('User input'),
        createAssistantMessage('Assistant response'),
      ]

      const handledRoles: string[] = []

      for (const message of messages) {
        switch (message.role) {
          case 'user':
            handledRoles.push(message.role)
            break
          case 'assistant':
            handledRoles.push(message.role)
            break
          default:
            // This should never happen with a complete discriminated union
            const _exhaustiveCheck: never = message
            throw new Error(`Unhandled message role: ${JSON.stringify(_exhaustiveCheck)}`)
        }
      }

      expect(handledRoles).toHaveLength(2)
      expect(handledRoles).toContain('user')
      expect(handledRoles).toContain('assistant')
    })
  })
})
