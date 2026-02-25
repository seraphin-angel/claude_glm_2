import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ScrollToBottomButtonProps {
  /** Whether the button should be visible */
  readonly isVisible: boolean
  /** Callback when button is clicked */
  readonly onClick: () => void
}

/**
 * Floating button that appears when user scrolls up,
 * allowing them to quickly scroll back to the latest messages.
 */
export function ScrollToBottomButton({ isVisible, onClick }: ScrollToBottomButtonProps) {
  return (
    <Button
      variant="secondary"
      size="icon"
      className={`
        absolute bottom-4 right-4 z-10
        rounded-full shadow-lg
        transition-all duration-200 ease-in-out
        ${isVisible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-2 pointer-events-none'
        }
      `}
      onClick={onClick}
      aria-label="最新メッセージへスクロール"
    >
      <ChevronDown className="h-5 w-5" />
    </Button>
  )
}
