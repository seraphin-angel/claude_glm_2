import { useEffect, useRef } from 'react'

export function useAutoScroll<T extends HTMLElement>(
  dependencies: unknown[],
): React.RefObject<T | null> {
  const ref = useRef<T>(null)

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, dependencies)

  return ref
}
