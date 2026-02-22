import { Button } from '@/components/ui/button'

interface ClarificationButtonsProps {
  readonly options: readonly string[]
  readonly onSelect: (option: string) => void
  readonly disabled: boolean
}

export function ClarificationButtons({ options, onSelect, disabled }: ClarificationButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <Button
          key={option}
          variant="outline"
          size="sm"
          onClick={() => onSelect(option)}
          disabled={disabled}
          className="text-sm"
        >
          {option}
        </Button>
      ))}
    </div>
  )
}
