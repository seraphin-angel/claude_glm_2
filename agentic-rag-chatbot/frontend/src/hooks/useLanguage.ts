import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  changeLanguage,
  getCurrentLanguage,
  supportedLanguages,
  type SupportedLanguage,
} from '../i18n'

export function useLanguage() {
  const { i18n } = useTranslation()
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>(
    getCurrentLanguage() as SupportedLanguage,
  )

  useEffect(() => {
    // Initialize language from localStorage on mount
    const savedLanguage = getCurrentLanguage()
    if (savedLanguage !== i18n.language) {
      i18n.changeLanguage(savedLanguage)
    }
  }, [i18n])

  const handleLanguageChange = useCallback(
    (lng: SupportedLanguage) => {
      changeLanguage(lng)
      setCurrentLanguage(lng)
    },
    [],
  )

  return {
    currentLanguage,
    changeLanguage: handleLanguageChange,
    supportedLanguages,
  }
}
