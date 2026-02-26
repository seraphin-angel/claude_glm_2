import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock i18n before any imports
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: vi.fn(),
      language: 'ja',
    },
  }),
}))

vi.mock('../../i18n', () => ({
  changeLanguage: vi.fn((lng: string) => {
    localStorage.setItem('language', lng)
  }),
  getCurrentLanguage: vi.fn(() => localStorage.getItem('language') || 'ja'),
  supportedLanguages: ['ja', 'en'] as const,
}))

vi.mock('../../hooks/useLanguage', () => ({
  useLanguage: () => ({
    currentLanguage: 'ja',
    changeLanguage: vi.fn((lng: string) => {
      localStorage.setItem('language', lng)
    }),
    supportedLanguages: ['ja', 'en'] as const,
  }),
}))

import { render, screen, fireEvent } from '@testing-library/react'
import { LanguageSwitcher } from '../../components/LanguageSwitcher'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('useLanguage', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  describe('LanguageSwitcher', () => {
    it('renders language buttons', () => {
      render(<LanguageSwitcher />)
      expect(screen.getByRole('button', { name: '日本語' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'English' })).toBeInTheDocument()
    })

    it('shows current language as selected', () => {
      render(<LanguageSwitcher />)
      const jaButton = screen.getByRole('button', { name: '日本語' })
      expect(jaButton).toHaveAttribute('aria-pressed', 'true')
    })

    it('calls onLanguageChange when language is changed', async () => {
      const mockOnLanguageChange = vi.fn()
      render(<LanguageSwitcher onLanguageChange={mockOnLanguageChange} />)

      const enButton = screen.getByRole('button', { name: 'English' })
      fireEvent.click(enButton)

      expect(mockOnLanguageChange).toHaveBeenCalledWith('en')
    })

    it('updates localStorage when language changes', () => {
      render(<LanguageSwitcher />)

      const enButton = screen.getByRole('button', { name: 'English' })
      fireEvent.click(enButton)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('language', 'en')
    })
  })
})
