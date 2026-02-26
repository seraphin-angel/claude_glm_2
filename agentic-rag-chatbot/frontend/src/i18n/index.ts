import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import ja from './locales/ja.json'
import en from './locales/en.json'

const resources = {
  ja: { translation: ja },
  en: { translation: en },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'ja', // default language
  fallbackLng: 'ja',
  interpolation: {
    escapeValue: false, // React already escapes values
  },
})

export default i18n

export const changeLanguage = (lng: string) => {
  i18n.changeLanguage(lng)
  localStorage.setItem('language', lng)
}

export const getCurrentLanguage = () => {
  return localStorage.getItem('language') || 'ja'
}

export const supportedLanguages = ['ja', 'en'] as const
export type SupportedLanguage = (typeof supportedLanguages)[number]
