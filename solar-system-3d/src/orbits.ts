import * as THREE from 'three'
import type { PlanetData } from './data/planetData'

export function createOrbits(scene: THREE.Scene, planets: PlanetData[]): THREE.Line[] {
  const orbits: THREE.Line[] = []

  planets.forEach((planet) => {
    const orbit = createOrbitLine(planet.distance)
    orbits.push(orbit)
    scene.add(orbit)
  })

  return orbits
}

function createOrbitLine(radius: number): THREE.Line {
  const segments = 128
  const points: THREE.Vector3[] = []

  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2
    points.push(new THREE.Vector3(
      Math.cos(angle) * radius,
      0,
      Math.sin(angle) * radius
    ))
  }

  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({
    color: 0x444466,
    transparent: true,
    opacity: 0.5
  })

  return new THREE.Line(geometry, material)
}

export function updateOrbitVisibility(orbits: THREE.Line[], visible: boolean): void {
  orbits.forEach((orbit) => {
    orbit.visible = visible
  })
}
