import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { createSun } from './sun'
import { createPlanets, type Planet } from './planets'
import { createOrbits, updateOrbitVisibility } from './orbits'
import { setupUI, showPlanetInfo } from './ui'
import { PLANET_DATA } from './data/planetData'
import { advanceSimulationElapsed } from './simulation'

// Global state
export interface AppState {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  renderer: THREE.WebGLRenderer
  labelRenderer: CSS2DRenderer
  controls: OrbitControls
  planets: Planet[]
  sun: THREE.Mesh
  orbits: THREE.Line[]
  isPaused: boolean
  speedMultiplier: number
  showOrbits: boolean
  clock: THREE.Clock
  simulationElapsed: number
}

const state: Partial<AppState> = {}

function init(): void {
  const canvas = document.getElementById('scene')
  const app = document.getElementById('app')
  if (!(canvas instanceof HTMLCanvasElement) || !app) {
    console.error('Missing required DOM elements: #scene canvas or #app container')
    return
  }

  // Create scene
  const scene = new THREE.Scene()
  state.scene = scene

  // Create camera
  const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    10000
  )
  camera.position.set(0, 100, 200)
  state.camera = camera

  // Create WebGL renderer
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true
  })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  state.renderer = renderer

  // Create CSS2D renderer for labels
  const labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(window.innerWidth, window.innerHeight)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0px'
  labelRenderer.domElement.style.pointerEvents = 'none'
  app.appendChild(labelRenderer.domElement)
  state.labelRenderer = labelRenderer

  // Add OrbitControls
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.minDistance = 30
  controls.maxDistance = 800
  state.controls = controls

  // Add starfield background
  createStarfield(scene)

  // Create Sun
  const sun = createSun(scene)
  state.sun = sun

  // Add sun label
  const sunLabel = createLabel('太陽', 'sun-label')
  sun.add(sunLabel)

  // Create planets with labels
  const planets = createPlanets(scene)
  planets.forEach(planet => {
    const label = createLabel(planet.data.nameJapanese, 'planet-label')
    label.position.set(0, planet.data.radius + 2, 0)
    planet.mesh.add(label)
  })
  state.planets = planets

  // Create orbits
  const orbits = createOrbits(scene, PLANET_DATA)
  state.orbits = orbits

  // Setup UI controls
  setupUI()

  // Handle window resize
  window.addEventListener('resize', onWindowResize)

  // Initialize clock
  state.clock = new THREE.Clock()
  state.simulationElapsed = 0
  state.isPaused = false
  state.speedMultiplier = 1
  state.showOrbits = true

  // Start animation loop
  animate()
}

function createLabel(text: string, className: string): CSS2DObject {
  const div = document.createElement('div')
  div.className = className
  div.textContent = text
  return new CSS2DObject(div)
}

function createStarfield(scene: THREE.Scene): void {
  const starsGeometry = new THREE.BufferGeometry()
  const starCount = 10000
  const positions = new Float32Array(starCount * 3)

  for (let i = 0; i < starCount * 3; i += 3) {
    const radius = 2000 + Math.random() * 3000
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)

    positions[i] = radius * Math.sin(phi) * Math.cos(theta)
    positions[i + 1] = radius * Math.sin(phi) * Math.sin(theta)
    positions[i + 2] = radius * Math.cos(phi)
  }

  starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  const starsMaterial = new THREE.PointsMaterial({
    color: 0xffffff,
    size: 1,
    sizeAttenuation: true
  })

  const stars = new THREE.Points(starsGeometry, starsMaterial)
  scene.add(stars)
}

function onWindowResize(): void {
  const camera = state.camera!
  const renderer = state.renderer!
  const labelRenderer = state.labelRenderer!

  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
  labelRenderer.setSize(window.innerWidth, window.innerHeight)
}

function animate(): void {
  requestAnimationFrame(animate)

  const delta = state.clock?.getDelta() ?? 0
  const isPaused = state.isPaused ?? true
  state.simulationElapsed = advanceSimulationElapsed(
    state.simulationElapsed ?? 0,
    delta,
    isPaused
  )

  if (!isPaused) {
    // Update planet positions
    updatePlanets(state.simulationElapsed, delta)
  }

  // Update controls
  state.controls!.update()

  // Render WebGL
  state.renderer!.render(state.scene!, state.camera!)

  // Render labels
  state.labelRenderer!.render(state.scene!, state.camera!)
}

function updatePlanets(elapsed: number, delta: number): void {
  const planets = state.planets
  if (!planets) return

  planets.forEach((planet) => {
    // Orbital rotation
    const orbitalSpeed = planet.data.orbitalSpeed * state.speedMultiplier!
    planet.group.rotation.y = elapsed * orbitalSpeed

    // Self rotation
    planet.mesh.rotation.y += planet.data.rotationSpeed * state.speedMultiplier! * delta * 0.6
  })
}

// Export functions for UI
export function togglePause(): boolean {
  state.isPaused = !state.isPaused
  return state.isPaused
}

export function setSpeed(speed: number): void {
  state.speedMultiplier = speed
}

export function toggleOrbits(): boolean {
  state.showOrbits = !state.showOrbits
  updateOrbitVisibility(state.orbits!, state.showOrbits)
  return state.showOrbits
}

export function resetCamera(): void {
  const camera = state.camera!
  camera.position.set(0, 100, 200)
  state.controls!.target.set(0, 0, 0)
  state.controls!.update()
}

export function focusOnPlanet(planetName: string): void {
  const planet = state.planets?.find(p => p.data.name === planetName)
  if (!planet) return

  const position = new THREE.Vector3()
  planet.mesh.getWorldPosition(position)

  state.controls!.target.copy(position)

  const distance = planet.data.radius * 8
  state.camera!.position.set(
    position.x + distance,
    position.y + distance * 0.5,
    position.z + distance
  )

  showPlanetInfo(planet.data)
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init)
