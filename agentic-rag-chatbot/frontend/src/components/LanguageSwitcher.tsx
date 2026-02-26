import { useLanguage, type SupportedLanguage } from '../hooks/useLanguage'

interface LanguageSwitcherProps {
  onLanguageChange?: (language: SupportedLanguage) => void
}

export function LanguageSwitcher({ onLanguageChange }: LanguageSwitcherProps) {
  const { currentLanguage, changeLanguage, supportedLanguages } = useLanguage()

  const handleChange = (lng: SupportedLanguage) => {
    changeLanguage(lng)
    onLanguageChange?.(lng)
  }

  return (
    <div className="flex items-center gap-2">
      {supportedLanguages.map((lng) => (
        <button
          key={lng}
          onClick={() => handleChange(lng)}
          className={`px-2 py-1 text-sm rounded transition-colors ${
            currentLanguage === lng
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80'
          }`}
          aria-label={lng === 'ja' ? '日本語' : 'English'}
          aria-pressed={currentLanguage === lng}
        >
          {lng === 'ja' ? '日本語' : 'EN'}
        </button>
      ))}
    </div>
  )
}
