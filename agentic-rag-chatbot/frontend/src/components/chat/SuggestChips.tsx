const SUGGEST_QUESTIONS = [
  '初期設定の方法は？',
  'パスワードリセットの手順',
  '料金プランについて',
  'ログインできない場合は？',
] as const

interface SuggestChipsProps {
  readonly onSelect: (question: string) => void
}

export function SuggestChips({ onSelect }: SuggestChipsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 mt-4">
      {SUGGEST_QUESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          onClick={() => onSelect(question)}
          className="px-3 py-1.5 rounded-full border border-border bg-background text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
        >
          {question}
        </button>
      ))}
    </div>
  )
}
