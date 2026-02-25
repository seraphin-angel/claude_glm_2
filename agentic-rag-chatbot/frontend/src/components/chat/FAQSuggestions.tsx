import { useEffect, useState } from 'react'

interface FAQ {
  id: string
  question: string
  answer: string
  keywords: string[]
  page_patterns: string[]
  category: string
  view_count: number
}

interface FAQSuggestionsProps {
  readonly onPageSelect?: (question: string) => void
}

const API_BASE = '/api'

async function fetchFAQSuggestions(pageUrl: string, limit: number = 3): Promise<FAQ[]> {
  try {
    const response = await fetch(
      `${API_BASE}/faq/suggestions?page_url=${encodeURIComponent(pageUrl)}&limit=${limit}`,
    )
    if (!response.ok) {
      return []
    }
    const data = await response.json()
    return data.faqs ?? []
  } catch {
    return []
  }
}

async function fetchTopFAQs(limit: number = 5): Promise<FAQ[]> {
  try {
    const response = await fetch(`${API_BASE}/faq/top?limit=${limit}`)
    if (!response.ok) {
      return []
    }
    const data = await response.json()
    return data.faqs ?? []
  } catch {
    return []
  }
}

async function recordFAQClick(faqId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/faq/click`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ faq_id: faqId }),
    })
  } catch {
    // Ignore errors for click tracking
  }
}

export function FAQSuggestions({ onPageSelect }: FAQSuggestionsProps) {
  const [pageFaqs, setPageFaqs] = useState<FAQ[]>([])
  const [topFaqs, setTopFaqs] = useState<FAQ[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadFAQs = async () => {
      setLoading(true)
      const currentPath = window.location.pathname

      // Load both page-specific and top FAQs
      const [pageResults, topResults] = await Promise.all([
        fetchFAQSuggestions(currentPath, 3),
        fetchTopFAQs(5),
      ])

      setPageFaqs(pageResults)
      setTopFaqs(topResults)
      setLoading(false)
    }

    loadFAQs()
  }, [])

  const handleFAQClick = (faq: FAQ) => {
    recordFAQClick(faq.id)
    onPageSelect?.(faq.question)
  }

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-4 bg-muted rounded w-24" />
        <div className="h-8 bg-muted rounded" />
        <div className="h-8 bg-muted rounded" />
      </div>
    )
  }

  // Combine page-specific FAQs with top FAQs, avoiding duplicates
  const pageFaqIds = new Set(pageFaqs.map((f) => f.id))
  const additionalTopFaqs = topFaqs.filter((f) => !pageFaqIds.has(f.id)).slice(0, 2)
  const displayFaqs = [...pageFaqs, ...additionalTopFaqs]

  if (displayFaqs.length === 0) {
    return null
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-medium text-muted-foreground">よくある質問</h3>
        {topFaqs.length > 0 && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
            {topFaqs.length}件
          </span>
        )}
      </div>
      <div className="space-y-2">
        {displayFaqs.map((faq) => (
          <button
            key={faq.id}
            type="button"
            onClick={() => handleFAQClick(faq)}
            className="w-full text-left p-3 rounded-lg border border-border bg-background hover:bg-muted hover:border-primary/50 transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-foreground group-hover:text-primary transition-colors">
                {faq.question}
              </span>
              {faq.view_count > 0 && (
                <span className="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-xs text-muted-foreground bg-muted">
                  {faq.view_count}回
                </span>
              )}
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{faq.category}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
