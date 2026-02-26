/**
 * ChatInputコンポーネントのテスト
 * 
 * TDD GREEN フェーズ: 画像添付機能のテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ChatInput } from '../ChatInput'

// react-dropzoneをモック
vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({ role: 'form' }),
    getInputProps: () => ({ type: 'file' }),
    isDragActive: false,
  }),
}))

describe('ChatInput', () => {
  const mockOnSend = vi.fn()
  
  beforeEach(() => {
    mockOnSend.mockClear()
  })

  describe('基本的な機能', () => {
    it('メッセージを入力して送信できる', () => {
      render(<ChatInput onSend={mockOnSend} disabled={false} />)
      
      const textarea = screen.getByRole('textbox', { name: /メッセージ入力/i })
      fireEvent.change(textarea, { target: { value: 'テストメッセージ' } })
      
      const sendButton = screen.getByRole('button', { name: /送信/i })
      fireEvent.click(sendButton)
      
      // 新しいシグネチャ: (message, imageData?)
      expect(mockOnSend).toHaveBeenCalledWith('テストメッセージ', undefined)
    })

    it('disabledの場合、送信ボタンが無効になる', () => {
      render(<ChatInput onSend={mockOnSend} disabled={true} />)
      
      const sendButton = screen.getByRole('button', { name: /送信/i })
      expect(sendButton).toBeDisabled()
    })
  })

  describe('画像添付機能', () => {
    it('画像選択ボタンが表示される', () => {
      render(<ChatInput onSend={mockOnSend} disabled={false} />)
      
      // 画像添付ボタンが存在することを確認
      const attachButton = screen.getByRole('button', { name: /画像添付/i })
      expect(attachButton).toBeInTheDocument()
    })

    it('フォームがドロップゾーンとして機能する', () => {
      render(<ChatInput onSend={mockOnSend} disabled={false} />)
      
      // フォーム（ドロップゾーン）が存在することを確認
      const form = screen.getByRole('form')
      expect(form).toBeInTheDocument()
    })
  })
})
