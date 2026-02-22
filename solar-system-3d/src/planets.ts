import * as THREE from 'three'
import { PLANET_DATA, type PlanetData } from './data/planetData'

export interface Planet {
  mesh: THREE.Mesh
  group: THREE.Group
  data: PlanetData
}

export function createPlanets(scene: THREE.Scene): Planet[] {
  const planets: Planet[] = []

  PLANET_DATA.forEach((data) => {
    const planet = createPlanet(data)
    planets.push(planet)
    scene.add(planet.group)
  })

  return planets
}

function createPlanet(data: PlanetData): Planet {
  // Create a group to hold the planet and its orbit
  const group = new THREE.Group()

  // Create planet geometry
  const geometry = new THREE.SphereGeometry(data.radius, 32, 32)

  // Create material with emissive glow effect
  const material = new THREE.MeshStandardMaterial({
    color: data.color,
    emissive: data.emissive,
    emissiveIntensity: data.emissiveIntensity,
    roughness: 0.6,
    metalness: 0.1
  })

  const mesh = new THREE.Mesh(geometry, material)

  // Position planet at its orbital distance
  mesh.position.x = data.distance

  // Add planet to the group
  group.add(mesh)

  // Special case: Add rings to Saturn
  if (data.name === 'Saturn') {
    const ringGeometry = new THREE.RingGeometry(
      data.radius * 1.4,
      data.radius * 2.2,
      64
    )

    // Adjust ring UVs for better texture mapping
    const pos = ringGeometry.attributes.position
    const v3 = new THREE.Vector3()
    for (let i = 0; i < pos.count; i++) {
      v3.fromBufferAttribute(pos, i)
      ringGeometry.attributes.uv.setXY(
        i,
        v3.length() < data.radius * 1.8 ? 0 : 1,
        1
      )
    }

    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0xf5deb3,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85
    })

    const ring = new THREE.Mesh(ringGeometry, ringMaterial)
    ring.rotation.x = Math.PI / 2
    ring.position.x = data.distance
    group.add(ring)
  }

  // Special case: Add moon to Earth
  if (data.name === 'Earth') {
    const moonGeometry = new THREE.SphereGeometry(0.5, 16, 16)
    const moonMaterial = new THREE.MeshStandardMaterial({
      color: 0xcccccc,
      emissive: 0x444444,
      emissiveIntensity: 0.1,
      roughness: 0.9
    })
    const moon = new THREE.Mesh(moonGeometry, moonMaterial)
    moon.position.set(data.distance + 5, 0, 0)
    group.add(moon)
  }

  return { mesh, group, data }
}
