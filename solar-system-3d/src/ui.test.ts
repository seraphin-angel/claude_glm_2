import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./main', () => ({
  setSpeed: vi.fn(),
  togglePause: vi.fn(() => false),
  resetCamera: vi.fn(),
  toggleOrbits: vi.fn(() => true),
  focusOnPlanet: vi.fn()
}))

import { setupUI } from './ui'

describe('setupUI', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('does not throw when expected DOM elements are missing', () => {
    expect(() => setupUI()).not.toThrow()
  })

  it('does not throw with partial DOM', () => {
    document.body.innerHTML = `
      <div id="controls"></div>
      <input id="speed-slider" type="range" value="1" />
    `
    expect(() => setupUI()).not.toThrow()
  })
})
