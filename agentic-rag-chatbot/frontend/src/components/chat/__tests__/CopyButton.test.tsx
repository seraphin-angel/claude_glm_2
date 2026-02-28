/**
 * CopyButtonコンポーネントのテスト
 *
 * TDD: Issue #3 - CopyButton Missing User Feedback
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CopyButton } from '../CopyButton'

// navigator.clipboard をモック
const mockClipboard = {
  writeText: vi.fn(),
}

Object.assign(navigator, {
  clipboard: mockClipboard,
})

describe('CopyButton', () => {
  beforeEach(() => {
    mockClipboard.writeText.mockReset()
    // execCommand をモック
    document.execCommand = vi.fn(() => true)
  })

  describe('基本的なコピー機能', () => {
    it('コピー成功時にチェックアイコンが表示される', async () => {
      mockClipboard.writeText.mockResolvedValueOnce(undefined)

      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button', { name: /コピー$/ })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /コピー完了/ })).toBeInTheDocument()
      })
    })
  })

  describe('フォールバック機能 (Issue #3)', () => {
    it('clipboard API失敗時にフォールバックコピーを試行する', async () => {
      mockClipboard.writeText.mockRejectedValueOnce(new Error('Permission denied'))

      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button', { name: /コピー$/ })
      fireEvent.click(button)

      await waitFor(() => {
        // フォールバックが成功した場合はコピー完了と表示
        expect(screen.getByRole('button', { name: /コピー完了/ })).toBeInTheDocument()
      })

      // execCommand が呼ばれたことを確認
      expect(document.execCommand).toHaveBeenCalledWith('copy')
    })

    it('フォールバックも失敗した場合、エラー状態を表示する', async () => {
      mockClipboard.writeText.mockRejectedValueOnce(new Error('Permission denied'))
      ;(document.execCommand as ReturnType<typeof vi.fn>).mockReturnValueOnce(false)

      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button', { name: /コピー$/ })
      fireEvent.click(button)

      await waitFor(() => {
        // エラー状態のボタンが表示されることを確認
        expect(screen.getByRole('button', { name: /コピー失敗/ })).toBeInTheDocument()
      })
    })
  })

  describe('アクセシビリティ', () => {
    it('ボタンに適切なaria-labelが設定されている', () => {
      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-label', 'コピー')
    })

    it('コピー成功時にaria-labelが更新される', async () => {
      mockClipboard.writeText.mockResolvedValueOnce(undefined)

      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button', { name: /コピー$/ })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'コピー完了')
      })
    })

    it('エラー状態では適切なaria-labelが設定される', async () => {
      mockClipboard.writeText.mockRejectedValueOnce(new Error('Permission denied'))
      ;(document.execCommand as ReturnType<typeof vi.fn>).mockReturnValueOnce(false)

      render(<CopyButton text="test text" />)

      const button = screen.getByRole('button', { name: /コピー$/ })
      fireEvent.click(button)

      await waitFor(() => {
        const errorButton = screen.getByRole('button')
        expect(errorButton).toHaveAttribute('aria-label', 'コピー失敗')
      })
    })
  })
})
