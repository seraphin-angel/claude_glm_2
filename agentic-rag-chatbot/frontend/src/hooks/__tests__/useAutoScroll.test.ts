import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAutoScroll } from '../useAutoScroll'

describe('useAutoScroll', () => {
  let container: HTMLDivElement

  beforeEach(() => {
    container = document.createElement('div')
    Object.defineProperty(container, 'scrollHeight', { value: 1000, writable: true })
    Object.defineProperty(container, 'clientHeight', { value: 500, writable: true })
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true })
    container.scrollTo = vi.fn()
    document.body.appendChild(container)
  })

  afterEach(() => {
    document.body.removeChild(container)
  })

  it('should return containerRef, isNearBottom, scrollToBottom, and handleScroll', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))

    expect(result.current.containerRef).toBeDefined()
    expect(result.current.isNearBottom).toBe(true)
    expect(typeof result.current.scrollToBottom).toBe('function')
    expect(typeof result.current.handleScroll).toBe('function')
  })

  it('should have isNearBottom initially true', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))
    expect(result.current.isNearBottom).toBe(true)
  })

  it('scrollToBottom should call scrollTo with correct options', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))

    // Set the ref to our mock container
    result.current.containerRef.current = container

    act(() => {
      result.current.scrollToBottom('smooth')
    })

    expect(container.scrollTo).toHaveBeenCalledWith({
      top: 1000,
      behavior: 'smooth',
    })
  })

  it('scrollToBottom should default to smooth behavior', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))

    // Set the ref to our mock container
    result.current.containerRef.current = container

    act(() => {
      result.current.scrollToBottom()
    })

    expect(container.scrollTo).toHaveBeenCalledWith({
      top: 1000,
      behavior: 'smooth',
    })
  })

  it('handleScroll should update isNearBottom to false when scrolled up', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))

    // Set the ref to our mock container
    result.current.containerRef.current = container

    // Simulate scrolling up (500px from bottom, which is > 100px threshold)
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true })
    Object.defineProperty(container, 'scrollHeight', { value: 1000, writable: true })
    Object.defineProperty(container, 'clientHeight', { value: 400, writable: true })

    act(() => {
      result.current.handleScroll()
    })

    expect(result.current.isNearBottom).toBe(false)
  })

  it('handleScroll should keep isNearBottom true when near bottom', () => {
    const { result } = renderHook(() => useAutoScroll<HTMLDivElement>([]))

    // Set the ref to our mock container
    result.current.containerRef.current = container

    // Simulate being near bottom (50px from bottom, which is < 100px threshold)
    Object.defineProperty(container, 'scrollTop', { value: 450, writable: true })
    Object.defineProperty(container, 'scrollHeight', { value: 1000, writable: true })
    Object.defineProperty(container, 'clientHeight', { value: 500, writable: true })

    act(() => {
      result.current.handleScroll()
    })

    expect(result.current.isNearBottom).toBe(true)
  })

  it('should use custom threshold from options', () => {
    const { result } = renderHook(() =>
      useAutoScroll<HTMLDivElement>([], { threshold: 50 }),
    )

    // Set the ref to our mock container
    result.current.containerRef.current = container

    // 80px from bottom - should be near bottom with default 100, but not with 50
    Object.defineProperty(container, 'scrollTop', { value: 420, writable: true })
    Object.defineProperty(container, 'scrollHeight', { value: 1000, writable: true })
    Object.defineProperty(container, 'clientHeight', { value: 500, writable: true })

    act(() => {
      result.current.handleScroll()
    })

    expect(result.current.isNearBottom).toBe(false)
  })
})
