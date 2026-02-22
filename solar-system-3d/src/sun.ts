import * as THREE from 'three'
import { SUN_DATA } from './data/planetData'

export function createSun(scene: THREE.Scene): THREE.Mesh {
  const geometry = new THREE.SphereGeometry(SUN_DATA.radius, 64, 64)

  const material = new THREE.MeshBasicMaterial({
    color: SUN_DATA.color
  })

  const sun = new THREE.Mesh(geometry, material)
  scene.add(sun)

  // Add point light emanating from the sun (brighter)
  const sunLight = new THREE.PointLight(0xffffff, 3, 600)
  sunLight.position.set(0, 0, 0)
  scene.add(sunLight)

  // Add ambient light for overall illumination (brighter)
  const ambientLight = new THREE.AmbientLight(0x555566, 0.8)
  scene.add(ambientLight)

  // Add sun glow effect (inner corona - bright yellow)
  const glowGeometry = new THREE.SphereGeometry(SUN_DATA.radius * 1.15, 32, 32)
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0xffdd00,
    transparent: true,
    opacity: 0.4
  })
  const glow = new THREE.Mesh(glowGeometry, glowMaterial)
  scene.add(glow)

  // Add middle glow (orange)
  const middleGlowGeometry = new THREE.SphereGeometry(SUN_DATA.radius * 1.3, 32, 32)
  const middleGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xffaa00,
    transparent: true,
    opacity: 0.25
  })
  const middleGlow = new THREE.Mesh(middleGlowGeometry, middleGlowMaterial)
  scene.add(middleGlow)

  // Add outer glow (red-orange)
  const outerGlowGeometry = new THREE.SphereGeometry(SUN_DATA.radius * 1.5, 32, 32)
  const outerGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xff6600,
    transparent: true,
    opacity: 0.15
  })
  const outerGlow = new THREE.Mesh(outerGlowGeometry, outerGlowMaterial)
  scene.add(outerGlow)

  // Add far outer glow (subtle red)
  const farOuterGlowGeometry = new THREE.SphereGeometry(SUN_DATA.radius * 1.8, 32, 32)
  const farOuterGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xff4400,
    transparent: true,
    opacity: 0.08
  })
  const farOuterGlow = new THREE.Mesh(farOuterGlowGeometry, farOuterGlowMaterial)
  scene.add(farOuterGlow)

  return sun
}
