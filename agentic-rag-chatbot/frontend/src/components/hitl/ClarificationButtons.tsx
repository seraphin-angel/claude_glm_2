import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ClarificationButtonsProps {
  readonly options: readonly string[]
  readonly onSelect: (option: string) => void
  readonly disabled: boolean
}

export function ClarificationButtons({ options, onSelect, disabled }: ClarificationButtonsProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null)

  const handleSelect = (option: string) => {
    setSelectedOption(option)
    onSelect(option)
  }

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="選択肢">
      {options.map((option) => {
        const isSelected = selectedOption === option
        const isOtherSelected = selectedOption !== null && !isSelected

        return (
          <Button
            key={option}
            variant={isSelected ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleSelect(option)}
            disabled={disabled || isOtherSelected}
            aria-pressed={isSelected}
            className={cn(
              'text-sm transition-all',
              isSelected && 'ring-2 ring-primary ring-offset-2',
              isOtherSelected && 'opacity-50',
            )}
          >
            {option}
          </Button>
        )
      })}
    </div>
  )
}
