import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownRenderer } from '../MarkdownRenderer'

describe('MarkdownRenderer', () => {
  describe('通常のMarkdownレンダリング', () => {
    it('テキストコンテンツが正しくレンダリングされる', () => {
      render(<MarkdownRenderer content="Hello, world!" />)
      expect(screen.getByText('Hello, world!')).toBeInTheDocument()
    })

    it('https://リンクは正常に機能する', () => {
      render(<MarkdownRenderer content="[リンク](https://example.com)" />)
      const link = screen.getByRole('link', { name: 'リンク' })
      expect(link).toBeInTheDocument()
      expect(link).toHaveAttribute('href', 'https://example.com')
    })

    it('GFMテーブルが正しくレンダリングされる', () => {
      const tableMarkdown = `
| 名前 | 年齢 |
|------|------|
| 太郎 | 20   |
      `.trim()
      render(<MarkdownRenderer content={tableMarkdown} />)
      expect(screen.getByRole('table')).toBeInTheDocument()
      expect(screen.getByText('太郎')).toBeInTheDocument()
    })
  })

  describe('XSSサニタイズ', () => {
    it('javascript: スキームのリンクがサニタイズされる', () => {
      render(<MarkdownRenderer content="[click me](javascript:alert(1))" />)
      const allLinks = document.querySelectorAll('a[href]')
      allLinks.forEach((a) => {
        expect(a.getAttribute('href')).not.toMatch(/^javascript:/i)
      })
    })

    it('大文字小文字混在のJAVASCRIPT: スキームも防がれる', () => {
      render(<MarkdownRenderer content="[XSS](JAVASCRIPT:alert(1))" />)
      const allLinks = document.querySelectorAll('a[href]')
      allLinks.forEach((a) => {
        const href = a.getAttribute('href') ?? ''
        expect(href.toLowerCase()).not.toContain('javascript:')
      })
    })

    it('data: スキームも防がれる', () => {
      render(
        <MarkdownRenderer content="[XSS](data:text/html,<script>alert(1)</script>)" />,
      )
      const allLinks = document.querySelectorAll('a[href]')
      allLinks.forEach((a) => {
        const href = a.getAttribute('href') ?? ''
        expect(href.toLowerCase()).not.toMatch(/^data:/)
      })
    })

    it('サニタイズ後もhttps://リンクは正常に機能する', () => {
      render(
        <MarkdownRenderer content="[安全なリンク](https://example.com/page)" />,
      )
      const link = screen.getByRole('link', { name: '安全なリンク' })
      expect(link).toHaveAttribute('href', 'https://example.com/page')
    })
  })
})
