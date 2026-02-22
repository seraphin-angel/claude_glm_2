import { describe, expect, it } from 'vitest'
import { advanceSimulationElapsed } from './simulation'

describe('advanceSimulationElapsed', () => {
  it('does not advance time while paused', () => {
    expect(advanceSimulationElapsed(10, 0.5, true)).toBe(10)
  })

  it('advances time while running', () => {
    expect(advanceSimulationElapsed(10, 0.5, false)).toBe(10.5)
  })
})
