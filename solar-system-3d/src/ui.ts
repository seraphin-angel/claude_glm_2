import type { PlanetData } from './data/planetData'
import { setSpeed, togglePause, resetCamera, toggleOrbits, focusOnPlanet } from './main'

export function setupUI(): void {
  // Speed slider
  const speedSlider = document.getElementById('speed-slider')
  const speedValue = document.getElementById('speed-value')
  if (speedSlider instanceof HTMLInputElement && speedValue instanceof HTMLSpanElement) {
    speedSlider.addEventListener('input', () => {
      const speed = parseFloat(speedSlider.value)
      speedValue.textContent = `${speed.toFixed(1)}x`
      setSpeed(speed)
    })
  }

  // Pause button
  const pauseBtn = document.getElementById('pause-btn')
  if (pauseBtn instanceof HTMLButtonElement) {
    pauseBtn.addEventListener('click', () => {
      const isPaused = togglePause()
      pauseBtn.textContent = isPaused ? 'Play' : 'Pause'
    })
  }

  // Reset button
  const resetBtn = document.getElementById('reset-btn')
  if (resetBtn instanceof HTMLButtonElement) {
    resetBtn.addEventListener('click', () => {
      resetCamera()
    })
  }

  // Show orbits checkbox
  const showOrbitsCheckbox = document.getElementById('show-orbits')
  if (showOrbitsCheckbox instanceof HTMLInputElement) {
    showOrbitsCheckbox.addEventListener('change', () => {
      const visible = toggleOrbits()
      showOrbitsCheckbox.checked = visible
    })
  }

  // Add planet selection buttons
  addPlanetButtons()
}

function addPlanetButtons(): void {
  const controls = document.getElementById('controls')
  if (!controls) return

  const planetList = document.createElement('div')
  planetList.className = 'planet-list'
  planetList.innerHTML = '<label>Focus on Planet:</label>'

  const planets = [
    { name: 'Mercury', color: '#8c7853' },
    { name: 'Venus', color: '#ffc649' },
    { name: 'Earth', color: '#6b93d6' },
    { name: 'Mars', color: '#c1440e' },
    { name: 'Jupiter', color: '#d8ca9d' },
    { name: 'Saturn', color: '#ead6b8' },
    { name: 'Uranus', color: '#d1e7e7' },
    { name: 'Neptune', color: '#5b5ddf' }
  ]

  planets.forEach((planet) => {
    const btn = document.createElement('button')
    btn.className = 'planet-btn'
    btn.innerHTML = `<span class="planet-color" style="background: ${planet.color}"></span>${planet.name}`
    btn.addEventListener('click', () => {
      focusOnPlanet(planet.name)
    })
    planetList.appendChild(btn)
  })

  controls.appendChild(planetList)
}

export function showPlanetInfo(data: PlanetData): void {
  const infoPanel = document.getElementById('planet-info')
  const planetName = document.getElementById('planet-name')
  const planetDetails = document.getElementById('planet-details')

  if (!infoPanel || !planetName || !planetDetails) return

  planetName.textContent = `${data.name} (${data.nameJapanese})`

  planetDetails.innerHTML = `
    <p>${data.description}</p>
    <p><strong>Diameter:</strong> ${data.facts.diameter}</p>
    <p><strong>Distance from Sun:</strong> ${data.facts.distanceFromSun}</p>
    <p><strong>Day Length:</strong> ${data.facts.dayLength}</p>
    <p><strong>Year Length:</strong> ${data.facts.yearLength}</p>
    <p><strong>Moons:</strong> ${data.facts.moons}</p>
  `

  infoPanel.classList.remove('hidden')
}
