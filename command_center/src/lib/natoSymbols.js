const baseUrl = import.meta.env.BASE_URL || '/'

const buildPublicPath = (relativePath) => {
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
  const normalizedRelative = relativePath.replace(/^\/+/, '')
  return `${normalizedBase}${normalizedRelative}`
}

const customSvg = (fileName) => buildPublicPath(`symbology/custom/${fileName}`)

export const NATO_SYMBOLS = {
  'allied-soldier-operator': {
    key: 'allied-soldier-operator',
    url: buildPublicPath('symbology/generated/allied-soldier-operator.svg'),
    atakIconUrl: customSvg('silhouette-soldier.svg'),
    canvasScale: 3.55,
    badgeColor: '#8B5CF6',
    atakBadge: true,
    label: 'Soldier Operator',
    legendNote: 'Friendly infantry / operator node',
    range: '400u / 3.2 sectors'
  },
  'allied-compute-drone': {
    key: 'allied-compute-drone',
    url: buildPublicPath('symbology/generated/allied-compute-drone.svg'),
    atakIconUrl: customSvg('silhouette-compute-drone.svg'),
    canvasScale: 3.2,
    badgeColor: '#1E3A8A',
    atakBadge: true,
    label: 'Compute Drone',
    legendNote: 'Friendly UAV / airborne command relay',
    range: '420u / 3.4 sectors'
  },
  'allied-recon-drone': {
    key: 'allied-recon-drone',
    url: buildPublicPath('symbology/generated/allied-recon-drone.svg'),
    atakIconUrl: customSvg('silhouette-recon-drone.svg'),
    canvasScale: 3.2,
    badgeColor: '#7DD3FC',
    atakBadge: true,
    label: 'Recon Drone',
    legendNote: 'Friendly UAV / reconnaissance',
    range: '170u / 1.4 sectors'
  },
  'allied-attack-drone': {
    key: 'allied-attack-drone',
    url: buildPublicPath('symbology/generated/allied-attack-drone.svg'),
    atakIconUrl: customSvg('silhouette-attack-drone.svg'),
    canvasScale: 3.2,
    badgeColor: '#7DD3FC',
    atakBadge: true,
    label: 'Attack Drone',
    legendNote: 'Friendly UAV / attack',
    range: '160u / 1.3 sectors'
  },
  'hostile-infantry': {
    key: 'hostile-infantry',
    url: buildPublicPath('symbology/generated/hostile-infantry.svg'),
    atakIconUrl: customSvg('silhouette-soldier.svg'),
    canvasScale: 3.55,
    badgeColor: '#FF6B6B',
    atakBadge: true,
    label: 'Enemy Infantry',
    legendNote: 'Hostile infantry unit',
    range: null
  },
  'hostile-tank': {
    key: 'hostile-tank',
    url: buildPublicPath('symbology/generated/hostile-tank.svg'),
    atakIconUrl: customSvg('silhouette-tank.svg'),
    canvasScale: 3.55,
    badgeColor: '#FF4500',
    atakBadge: true,
    label: 'Enemy Tank',
    legendNote: 'Hostile tracked armor',
    range: null
  },
  'hostile-vehicle': {
    key: 'hostile-vehicle',
    url: buildPublicPath('symbology/generated/hostile-vehicle.svg'),
    atakIconUrl: customSvg('silhouette-vehicle.svg'),
    canvasScale: 3.55,
    badgeColor: '#F97316',
    atakBadge: true,
    label: 'Enemy Vehicle',
    legendNote: 'Hostile scout / armored vehicle',
    range: null
  }
}

export const MAP_SYMBOLS = {
  ...NATO_SYMBOLS,
  'neutral-building': {
    key: 'neutral-building',
    url: customSvg('structure-building.svg'),
    atakIconUrl: customSvg('structure-building.svg'),
    canvasScale: 2.05,
    badgeColor: '#8B7355',
    atakBadge: false,
    label: 'Building',
    legendNote: 'Direct SVG marker',
    range: null
  },
  'neutral-warehouse': {
    key: 'neutral-warehouse',
    url: customSvg('structure-warehouse.svg'),
    atakIconUrl: customSvg('structure-warehouse.svg'),
    canvasScale: 2.25,
    badgeColor: '#7A6B5A',
    atakBadge: false,
    label: 'Warehouse',
    legendNote: 'Direct SVG marker',
    range: null
  },
  'neutral-bridge': {
    key: 'neutral-bridge',
    url: customSvg('structure-bridge.svg'),
    atakIconUrl: customSvg('structure-bridge.svg'),
    canvasScale: 2.15,
    badgeColor: '#666666',
    atakBadge: false,
    label: 'Bridge',
    legendNote: 'Direct SVG marker',
    range: null
  },
  'poi-downed-aircraft': {
    key: 'poi-downed-aircraft',
    url: customSvg('poi-downed-aircraft.svg'),
    atakIconUrl: customSvg('silhouette-downed-aircraft.svg'),
    canvasScale: 1.95,
    badgeColor: '#FACC15',
    atakBadge: true,
    label: 'Downed Aircraft',
    legendNote: 'Recovery / crash site',
    range: null
  },
  'poi-cache': {
    key: 'poi-cache',
    url: customSvg('poi-supply-cache.svg'),
    atakIconUrl: customSvg('silhouette-supply-cache.svg'),
    canvasScale: 1.55,
    badgeColor: '#F59E0B',
    atakBadge: true,
    label: 'Supply Cache',
    legendNote: 'Hidden logistics node',
    range: null
  }
}

const DRONE_TYPE_TO_SYMBOL = {
  soldier: 'allied-soldier-operator',
  compute: 'allied-compute-drone',
  recon: 'allied-recon-drone',
  attack: 'allied-attack-drone'
}

const ENEMY_TYPE_TO_SYMBOL = {
  infantry: 'hostile-infantry',
  tank: 'hostile-tank',
  vehicle: 'hostile-vehicle'
}

const STRUCTURE_TYPE_TO_SYMBOL = {
  building: 'neutral-building',
  warehouse: 'neutral-warehouse',
  bridge: 'neutral-bridge'
}

const POI_TYPE_TO_SYMBOL = {
  downed_aircraft: 'poi-downed-aircraft',
  cache: 'poi-cache'
}

export function resolveMapSymbolKey(entity) {
  if (!entity) return null

  if (entity.type === 'drone') {
    return DRONE_TYPE_TO_SYMBOL[entity.droneType] || null
  }

  if (entity.type === 'enemy') {
    return ENEMY_TYPE_TO_SYMBOL[entity.enemyType] || null
  }

  if (entity.type === 'structure') {
    return STRUCTURE_TYPE_TO_SYMBOL[entity.structureType] || null
  }

  if (entity.type === 'poi') {
    return POI_TYPE_TO_SYMBOL[entity.poiType] || null
  }

  return null
}

export function getMapSymbolDescriptor(entity) {
  if (!entity) return null

  const symbolKey = entity.symbolKey || resolveMapSymbolKey(entity)
  if (!symbolKey) {
    if (!entity.symbolUrl) return null
    return {
      key: entity.symbolKey || 'custom',
      url: entity.symbolUrl,
      atakIconUrl: entity.atakSymbolUrl || entity.symbolUrl,
      canvasScale: entity.symbolScale || 2,
      badgeColor: entity.color || '#94A3B8',
      atakBadge: entity.atakBadge !== false,
      label: entity.label || 'Custom Symbol',
      legendNote: null,
      range: null
    }
  }

  return MAP_SYMBOLS[symbolKey] || null
}

export const NATO_UNIT_LEGEND_ITEMS = [
  MAP_SYMBOLS['allied-soldier-operator'],
  MAP_SYMBOLS['allied-compute-drone'],
  MAP_SYMBOLS['allied-recon-drone'],
  MAP_SYMBOLS['allied-attack-drone'],
  MAP_SYMBOLS['hostile-infantry'],
  MAP_SYMBOLS['hostile-tank'],
  MAP_SYMBOLS['hostile-vehicle']
]

export const MAP_MARKER_LEGEND_ITEMS = [
  MAP_SYMBOLS['neutral-building'],
  MAP_SYMBOLS['neutral-warehouse'],
  MAP_SYMBOLS['neutral-bridge'],
  MAP_SYMBOLS['poi-downed-aircraft'],
  MAP_SYMBOLS['poi-cache']
]

export function getNatoSymbolDescriptor(entity) {
  return getMapSymbolDescriptor(entity)
}
