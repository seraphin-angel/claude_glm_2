import { useCallback, useEffect, useRef, useState } from 'react'

interface UseAutoScrollOptions {
  /** Distance from bottom in pixels to consider "near bottom". Default: 100 */
  readonly threshold?: number
}

interface UseAutoScrollReturn<T> {
  /** Ref to attach to the scrollable container */
  readonly containerRef: React.RefObject<T | null>
  /** Whether the user is near the bottom of the scrollable area */
  readonly isNearBottom: boolean
  /** Function to programmatically scroll to bottom */
  readonly scrollToBottom: (behavior?: ScrollBehavior) => void
  /** Handler to attach to onScroll event */
  readonly handleScroll: () => void
}

/**
 * Hook for intelligent auto-scrolling behavior.
 * Only auto-scrolls when user is near the bottom of the container.
 *
 * @param dependencies - Array of values that should trigger auto-scroll when changed
 * @param options - Configuration options
 * @returns Object containing ref, state, and handlers
 */
export function useAutoScroll<T extends HTMLElement>(
  dependencies: unknown[],
  options?: UseAutoScrollOptions,
): UseAutoScrollReturn<T> {
  const { threshold = 100 } = options ?? {}
  const containerRef = useRef<T>(null)
  const [isNearBottom, setIsNearBottom] = useState(true)

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const container = containerRef.current
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      })
    }
  }, [])

  const handleScroll = useCallback(() => {
    const container = containerRef.current
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight
    const nearBottom = distanceFromBottom < threshold

    setIsNearBottom(nearBottom)
  }, [threshold])

  // Auto-scroll when dependencies change and user is near bottom
  useEffect(() => {
    if (isNearBottom && containerRef.current) {
      // Use 'auto' for instant scroll during streaming to avoid lag
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, dependencies)

  return {
    containerRef,
    isNearBottom,
    scrollToBottom,
    handleScroll,
  }
}
