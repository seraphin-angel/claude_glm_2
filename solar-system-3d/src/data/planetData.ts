export interface PlanetData {
  name: string
  nameJapanese: string
  radius: number
  distance: number
  orbitalSpeed: number
  rotationSpeed: number
  color: number
  emissive: number
  emissiveIntensity: number
  description: string
  facts: {
    diameter: string
    distanceFromSun: string
    dayLength: string
    yearLength: string
    moons: number
  }
}

export const PLANET_DATA: PlanetData[] = [
  {
    name: 'Mercury',
    nameJapanese: '水星',
    radius: 1.5,
    distance: 20,
    orbitalSpeed: 4.15,
    rotationSpeed: 0.017,
    color: 0xa8a8a8,
    emissive: 0x666666,
    emissiveIntensity: 0.15,
    description: 'Mercury is the smallest planet and closest to the Sun.',
    facts: {
      diameter: '4,879 km',
      distanceFromSun: '57.9 million km',
      dayLength: '59 Earth days',
      yearLength: '88 Earth days',
      moons: 0
    }
  },
  {
    name: 'Venus',
    nameJapanese: '金星',
    radius: 2.5,
    distance: 30,
    orbitalSpeed: 1.62,
    rotationSpeed: -0.004,
    color: 0xffd54f,
    emissive: 0xff9800,
    emissiveIntensity: 0.2,
    description: 'Venus is the hottest planet with a thick toxic atmosphere.',
    facts: {
      diameter: '12,104 km',
      distanceFromSun: '108.2 million km',
      dayLength: '243 Earth days',
      yearLength: '225 Earth days',
      moons: 0
    }
  },
  {
    name: 'Earth',
    nameJapanese: '地球',
    radius: 2.6,
    distance: 42,
    orbitalSpeed: 1.0,
    rotationSpeed: 1.0,
    color: 0x4fc3f7,
    emissive: 0x0288d1,
    emissiveIntensity: 0.25,
    description: 'Earth is our home planet, the only known planet with life.',
    facts: {
      diameter: '12,742 km',
      distanceFromSun: '149.6 million km',
      dayLength: '24 hours',
      yearLength: '365.25 days',
      moons: 1
    }
  },
  {
    name: 'Mars',
    nameJapanese: '火星',
    radius: 2.0,
    distance: 55,
    orbitalSpeed: 0.53,
    rotationSpeed: 0.97,
    color: 0xff7043,
    emissive: 0xd84315,
    emissiveIntensity: 0.2,
    description: 'Mars is the Red Planet, a cold desert world with polar ice caps.',
    facts: {
      diameter: '6,779 km',
      distanceFromSun: '227.9 million km',
      dayLength: '24.6 hours',
      yearLength: '687 Earth days',
      moons: 2
    }
  },
  {
    name: 'Jupiter',
    nameJapanese: '木星',
    radius: 8,
    distance: 85,
    orbitalSpeed: 0.084,
    rotationSpeed: 2.4,
    color: 0xffb74d,
    emissive: 0xe65100,
    emissiveIntensity: 0.15,
    description: 'Jupiter is the largest planet, a gas giant with the Great Red Spot.',
    facts: {
      diameter: '139,820 km',
      distanceFromSun: '778.5 million km',
      dayLength: '9.9 hours',
      yearLength: '11.9 Earth years',
      moons: 95
    }
  },
  {
    name: 'Saturn',
    nameJapanese: '土星',
    radius: 7,
    distance: 115,
    orbitalSpeed: 0.034,
    rotationSpeed: 2.2,
    color: 0xffe082,
    emissive: 0xffa000,
    emissiveIntensity: 0.15,
    description: 'Saturn is famous for its stunning ring system.',
    facts: {
      diameter: '116,460 km',
      distanceFromSun: '1.4 billion km',
      dayLength: '10.7 hours',
      yearLength: '29.4 Earth years',
      moons: 146
    }
  },
  {
    name: 'Uranus',
    nameJapanese: '天王星',
    radius: 4,
    distance: 145,
    orbitalSpeed: 0.012,
    rotationSpeed: -1.4,
    color: 0x4dd0e1,
    emissive: 0x00acc1,
    emissiveIntensity: 0.25,
    description: 'Uranus rotates on its side, making it unique among planets.',
    facts: {
      diameter: '50,724 km',
      distanceFromSun: '2.9 billion km',
      dayLength: '17.2 hours',
      yearLength: '84 Earth years',
      moons: 28
    }
  },
  {
    name: 'Neptune',
    nameJapanese: '海王星',
    radius: 3.8,
    distance: 175,
    orbitalSpeed: 0.006,
    rotationSpeed: 1.5,
    color: 0x5c6bc0,
    emissive: 0x303f9f,
    emissiveIntensity: 0.3,
    description: 'Neptune is the windiest planet with supersonic wind storms.',
    facts: {
      diameter: '49,244 km',
      distanceFromSun: '4.5 billion km',
      dayLength: '16.1 hours',
      yearLength: '164.8 Earth years',
      moons: 16
    }
  }
]

export const SUN_DATA = {
  radius: 10,
  color: 0xffee00,
  emissive: 0xffaa00
}
