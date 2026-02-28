/**
 * MessageFeedbackコンポーネントのテスト
 *
 * TDD: Issue #4 - MessageFeedback Silent Failure
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MessageFeedback } from '../MessageFeedback'

// sendFeedbackをモック
vi.mock('@/lib/api', () => ({
  sendFeedback: vi.fn(),
}))

import { sendFeedback } from '@/lib/api'

const mockSendFeedback = vi.mocked(sendFeedback)

describe('MessageFeedback', () => {
  beforeEach(() => {
    mockSendFeedback.mockReset()
  })

  describe('基本的なフィードバック機能', () => {
    it('ポジティブフィードバックボタンがクリックできる', async () => {
      mockSendFeedback.mockResolvedValueOnce({ success: true, data: undefined })

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(mockSendFeedback).toHaveBeenCalledWith('test-msg-1', 'positive')
      })
    })

    it('ネガティブフィードバックボタンがクリックできる', async () => {
      mockSendFeedback.mockResolvedValueOnce({ success: true, data: undefined })

      render(<MessageFeedback messageId="test-msg-1" />)

      const negativeButton = screen.getByRole('button', { name: '役に立たなかった' })
      fireEvent.click(negativeButton)

      await waitFor(() => {
        expect(mockSendFeedback).toHaveBeenCalledWith('test-msg-1', 'negative')
      })
    })

    it('選択状態が視覚的に反映される', async () => {
      mockSendFeedback.mockResolvedValueOnce({ success: true, data: undefined })

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(positiveButton).toHaveAttribute('aria-pressed', 'true')
      })
    })
  })

  describe('エラーハンドリング (Issue #4)', () => {
    it('送信失敗時にエラーメッセージを表示する', async () => {
      mockSendFeedback.mockRejectedValueOnce(new Error('Network error'))

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(screen.getByText(/送信に失敗しました/)).toBeInTheDocument()
      })
    })

    it('送信失敗時にリトライボタンを表示する', async () => {
      mockSendFeedback.mockRejectedValueOnce(new Error('Network error'))

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /再試行/ })).toBeInTheDocument()
      })
    })

    it('リトライボタンクリックで再送信する', async () => {
      mockSendFeedback
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ success: true, data: undefined })

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /再試行/ })).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /再試行/ })
      fireEvent.click(retryButton)

      await waitFor(() => {
        expect(mockSendFeedback).toHaveBeenCalledTimes(2)
      })
    })

    it('リトライ成功時にエラー表示が消える', async () => {
      mockSendFeedback
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ success: true, data: undefined })

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      await waitFor(() => {
        expect(screen.getByText(/送信に失敗しました/)).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: /再試行/ })
      fireEvent.click(retryButton)

      await waitFor(() => {
        expect(screen.queryByText(/送信に失敗しました/)).not.toBeInTheDocument()
      })
    })
  })

  describe('アクセシビリティ', () => {
    it('フィードバックエリアに適切なaria-labelが設定されている', () => {
      render(<MessageFeedback messageId="test-msg-1" />)

      const feedbackArea = screen.getByRole('group', { name: 'メッセージへのフィードバック' })
      expect(feedbackArea).toBeInTheDocument()
    })

    it('送信中はボタンが無効化される', async () => {
      // 遅延レスポンスをシミュレート
      mockSendFeedback.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      )

      render(<MessageFeedback messageId="test-msg-1" />)

      const positiveButton = screen.getByRole('button', { name: '役に立った' })
      fireEvent.click(positiveButton)

      // 送信中はボタンが無効化される
      await waitFor(() => {
        expect(positiveButton).toBeDisabled()
      })
    })
  })
})
