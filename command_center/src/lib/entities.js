/**
 * Entity System (Base Class Architecture)
 * 
 * Unified entity management for all swarm elements:
 * - Soldiers/Drones (allied)
 * - Enemies (hostile)
 * - Structures (neutral/blocking)
 * - Points of Interest (terrain features)
 * 
 * All entities use continuous 1000×1000 coordinate system
 * with Euclidean distance for transmission ranges.
 */

import { getMapSymbolDescriptor } from './natoSymbols'
import {
  doesAnyFootprintBlockSegment,
  getFootprintCenter,
  getStructureFootprint,
  normalizeRectFootprint,
  pointInRect
} from './mapGeometry'

/**
 * Base Entity Class
 * All entities inherit from this base
 */
export class Entity {
  constructor(id, type, position, options = {}) {
    this.id = id
    this.type = type // 'drone', 'enemy', 'structure', 'poi'
    this.position = position // [x, y] in continuous 1000×1000 coordinate system
    this.label = options.label || id
    this.allegiance = options.allegiance || 'neutral' // 'allied', 'enemy', 'neutral'
    this.status = options.status || 'active' // 'active', 'destroyed', 'inactive'
    this.size = options.size || 1 // Relative size (1 = normal)
    this.shape = options.shape || 'circle' // 'circle', 'square', 'diamond', 'triangle', 'star', 'rectangle'
    this.color = options.color || '#999999'
    this.renderSize = options.renderSize || 12
    this.opacity = options.opacity ?? 1
    this.blocksLoS = options.blocksLoS || false // Does this entity block line of sight?
    this.transmissionRange = options.transmissionRange || 0 // Euclidean distance in 1000×1000 space
    this.detectionRadius = options.detectionRadius || 0
    this.revealed = options.revealed !== false // For hidden entities
    this.symbolKey = options.symbolKey || null
    this.symbolUrl = options.symbolUrl || null
    this.atakSymbolUrl = options.atakSymbolUrl || null
    this.symbolScale = options.symbolScale || 0
    this.atakBadge = options.atakBadge !== false
    this.footprint = options.footprint ? normalizeRectFootprint(options.footprint) : null
  }

  /**
   * Get Euclidean distance to another entity or position
   * @param {Entity|Array} target - Entity or [x, y] position
   * @returns {number} Distance in coordinate space
   */
  distanceTo(target) {
    const targetPos = Array.isArray(target) ? target : target.position
    const dx = this.position[0] - targetPos[0]
    const dy = this.position[1] - targetPos[1]
    return Math.sqrt(dx * dx + dy * dy)
  }

  /**
   * Check if target is in transmission range
   * @param {Entity|Array} target - Entity or [x, y] position
   * @returns {boolean}
   */
  canTransmitTo(target) {
    if (this.transmissionRange === 0) return false
    if (this.status === 'destroyed') return false
    return this.distanceTo(target) <= this.transmissionRange
  }

  /**
   * Check if this entity blocks line of sight between two points
   * @param {number} x1 - Start X
   * @param {number} y1 - Start Y
   * @param {number} x2 - End X
   * @param {number} y2 - End Y
   * @returns {boolean}
   */
  blocksLineOfSight(x1, y1, x2, y2) {
    if (!this.blocksLoS || this.status === 'destroyed') return false

    if (this.footprint) {
      return doesAnyFootprintBlockSegment([x1, y1], [x2, y2], [this.footprint])
    }
    
    // Get entity center in coordinate space
    const entityX = this.position[0]
    const entityY = this.position[1]
    
    // Check if line passes near entity
    const dx = x2 - x1
    const dy = y2 - y1
    const lineLen = Math.sqrt(dx * dx + dy * dy)
    
    if (lineLen === 0) return false
    
    // Project entity position onto line
    const t = ((entityX - x1) * dx + (entityY - y1) * dy) / (lineLen * lineLen)
    
    if (t < 0 || t > 1) return false // Entity not on line segment
    
    // Find closest point on line to entity
    const closestX = x1 + t * dx
    const closestY = y1 + t * dy
    
    // Distance from entity to line
    const distance = Math.sqrt(
      Math.pow(entityX - closestX, 2) +
      Math.pow(entityY - closestY, 2)
    )
    
    // Check based on entity size/shape
    const blockRadius = this.getBlockingRadius()
    return distance < blockRadius
  }

  /**
   * Get radius of LoS blocking area for this entity in continuous space
   */
  getBlockingRadius() {
    // Maps size to a blocking radius in continuous 1000×1000 space
    // Normal size (1.0) blocks ~100 units
    return this.size * 100
  }

  /**
   * Get display position scaled to 8×8 grid from 1000×1000 coordinates
   * Scale factor: 1000 / 8 = 125 units per grid cell
   */
  getScaledPosition() {
    const SCALE = 1000 / 8
    return [
      Math.floor(this.position[0] / SCALE),
      Math.floor(this.position[1] / SCALE)
    ]
  }

  containsPoint(point) {
    if (this.footprint) {
      return pointInRect(point, this.footprint)
    }
    return this.distanceTo(point) <= this.getBlockingRadius()
  }
}

/**
 * Drone Entity (Allied)
 * Transmission ranges use Euclidean distance in 1000×1000 coordinate space
 * Scale: 1000/8 = 125 units per grid cell (8×8 grid)
 */
export class Drone extends Entity {
  constructor(id, droneType, position, options = {}) {
    const defaultSymbol = getMapSymbolDescriptor({
      type: 'drone',
      droneType,
      ...options
    })
    const defaultShape = {
      soldier: 'square',
      compute: 'diamond',
      recon: 'triangle',
      attack: 'star'
    }[droneType] || 'circle'
    const defaultColor = {
      soldier: '#8B5CF6',
      compute: '#1E3A8A',
      recon: '#7DD3FC',
      attack: '#7DD3FC'
    }[droneType] || '#999999'
    const defaultRenderSize = {
      soldier: 14,
      compute: 16,
      recon: 13,
      attack: 15
    }[droneType] || 12
    const defaultTransmissionRange = {
      soldier: 190,
      compute: 420,
      recon: 170,
      attack: 160
    }[droneType] || 250

    super(id, 'drone', position, {
      allegiance: 'allied',
      ...options,
      shape: options.shape ?? defaultShape,
      color: options.color ?? defaultColor,
      renderSize: options.renderSize ?? defaultRenderSize,
      transmissionRange: options.transmissionRange ?? defaultTransmissionRange,
      symbolKey: options.symbolKey ?? defaultSymbol?.key ?? null,
      symbolUrl: options.symbolUrl ?? defaultSymbol?.url ?? null,
      atakSymbolUrl: options.atakSymbolUrl ?? defaultSymbol?.atakIconUrl ?? null,
      symbolScale: options.symbolScale ?? defaultSymbol?.canvasScale ?? 0,
      atakBadge: options.atakBadge ?? defaultSymbol?.atakBadge ?? true
    })
    this.droneType = droneType
    this.behavior = options.behavior || 'lurk'
  }
}

/**
 * Enemy Entity (Hostile)
 */
export class Enemy extends Entity {
  constructor(id, enemyType, position, options = {}) {
    const defaultSymbol = getMapSymbolDescriptor({
      type: 'enemy',
      enemyType,
      ...options
    })
    const defaultShape = {
      infantry: 'circle',
      tank: 'square',
      helicopter: 'triangle',
      vehicle: 'diamond'
    }[enemyType] || 'circle'
    const defaultColor = {
      infantry: '#FF6B6B',
      tank: '#FF4500',
      helicopter: '#FB7185',
      vehicle: '#F97316'
    }[enemyType] || '#FF0000'
    const defaultRenderSize = {
      infantry: 12,
      tank: 18,
      helicopter: 16,
      vehicle: 14
    }[enemyType] || 12

    super(id, 'enemy', position, {
      allegiance: 'enemy',
      ...options,
      shape: options.shape ?? defaultShape,
      color: options.color ?? defaultColor,
      renderSize: options.renderSize ?? defaultRenderSize,
      revealed: options.revealed !== undefined ? options.revealed : false,
      symbolKey: options.symbolKey ?? defaultSymbol?.key ?? null,
      symbolUrl: options.symbolUrl ?? defaultSymbol?.url ?? null,
      atakSymbolUrl: options.atakSymbolUrl ?? defaultSymbol?.atakIconUrl ?? null,
      symbolScale: options.symbolScale ?? defaultSymbol?.canvasScale ?? 0,
      atakBadge: options.atakBadge ?? defaultSymbol?.atakBadge ?? true
    })
    this.enemyType = enemyType
  }
}

/**
 * Structure Entity (Neutral, usually blocking)
 */
export class Structure extends Entity {
  constructor(id, structureType, position, options = {}) {
    const defaultSymbol = getMapSymbolDescriptor({
      type: 'structure',
      structureType,
      ...options
    })
    const defaultShape = {
      'building': 'rectangle',
      'warehouse': 'rectangle',
      'mountain': 'square',
      'bridge': 'rectangle'
    }[structureType] || 'rectangle'
    const defaultColor = {
      'building': '#4A4A4A',
      'warehouse': '#3A3A3A',
      'mountain': '#8B7355',
      'bridge': '#666666'
    }[structureType] || '#4A4A4A'

    super(id, 'structure', position, {
      allegiance: 'neutral',
      blocksLoS: true, // Structures block line of sight by default
      ...options,
      shape: options.shape ?? defaultShape,
      color: options.color ?? defaultColor,
      size: options.size || 0.8,
      renderSize: options.renderSize || 18,
      footprint: options.footprint || getStructureFootprint({
        ...options,
        subtype: structureType,
        position
      }),
      symbolKey: options.symbolKey ?? defaultSymbol?.key ?? null,
      symbolUrl: options.symbolUrl ?? defaultSymbol?.url ?? null,
      atakSymbolUrl: options.atakSymbolUrl ?? defaultSymbol?.atakIconUrl ?? null,
      symbolScale: options.symbolScale ?? defaultSymbol?.canvasScale ?? 0,
      atakBadge: options.atakBadge ?? defaultSymbol?.atakBadge ?? false
    })
    this.structureType = structureType
    if (this.footprint) {
      const center = getFootprintCenter(this.footprint)
      if (center) {
        this.position = center
      }
    }
  }

  /**
   * Structures have rectangular blocking for better LoS
   */
  getBlockingRadius() {
    if (this.shape === 'rectangle') {
      const CELL_SIZE = 100
      return (this.size * CELL_SIZE) * 0.6 // Wider blocking area for rectangles
    }
    return super.getBlockingRadius()
  }
}

/**
 * Point of Interest Entity (Various non-blocking features)
 */
export class PointOfInterest extends Entity {
  constructor(id, poiType, position, options = {}) {
    const defaultSymbol = getMapSymbolDescriptor({
      type: 'poi',
      poiType,
      ...options
    })
    const defaultShape = {
      'downed_aircraft': 'triangle',
      'cache': 'square',
      'checkpoint': 'circle',
      'crash_site': 'diamond'
    }[poiType] || 'circle'
    const defaultColor = {
      'downed_aircraft': '#FFD93D',
      'cache': '#FFB347',
      'checkpoint': '#87CEEB',
      'crash_site': '#F59E0B'
    }[poiType] || '#CCCCCC'

    super(id, 'poi', position, {
      allegiance: 'neutral',
      blocksLoS: false,
      ...options,
      shape: options.shape ?? defaultShape,
      color: options.color ?? defaultColor,
      renderSize: options.renderSize || 14,
      revealed: options.revealed !== undefined ? options.revealed : false,
      symbolKey: options.symbolKey ?? defaultSymbol?.key ?? null,
      symbolUrl: options.symbolUrl ?? defaultSymbol?.url ?? null,
      atakSymbolUrl: options.atakSymbolUrl ?? defaultSymbol?.atakIconUrl ?? null,
      symbolScale: options.symbolScale ?? defaultSymbol?.canvasScale ?? 0,
      atakBadge: options.atakBadge ?? defaultSymbol?.atakBadge ?? true
    })
    this.poiType = poiType
  }
}

/**
 * Helper: Convert old state format to new Entity objects
 */
export function stateToEntities(state) {
  const entities = []
  const isFiniteNumber = (value) => Number.isFinite(Number(value))

  const clampPosition = (position) => {
    if (!Array.isArray(position) || position.length !== 2) return [500, 500]
    return [
      Math.max(0, Math.min(1000, Number(position[0]) || 0)),
      Math.max(0, Math.min(1000, Number(position[1]) || 0))
    ]
  }

  const resolvePosition = (entity, fallbackPosition) => {
    if (Array.isArray(entity?.position)) return clampPosition(entity.position)
    if (Array.isArray(fallbackPosition)) return clampPosition(fallbackPosition)
    return [500, 500]
  }

  const resolveRenderOptions = (entity) => {
    const render = entity?.render || {}
    const options = {}

    if (typeof render.shape === 'string' && render.shape.length > 0) {
      options.shape = render.shape
    }
    if (typeof render.color === 'string' && render.color.length > 0) {
      options.color = render.color
    }
    const renderSymbolKey = render.symbolKey || render.symbol_key
    if (typeof renderSymbolKey === 'string' && renderSymbolKey.length > 0) {
      options.symbolKey = renderSymbolKey
    }
    const renderSymbolUrl = render.symbolUrl || render.symbol_url
    if (typeof renderSymbolUrl === 'string' && renderSymbolUrl.length > 0) {
      options.symbolUrl = renderSymbolUrl
    }
    const renderAtakSymbolUrl = render.atakSymbolUrl || render.atak_symbol_url
    if (typeof renderAtakSymbolUrl === 'string' && renderAtakSymbolUrl.length > 0) {
      options.atakSymbolUrl = renderAtakSymbolUrl
    }
    const renderSymbolScale = render.symbolScale ?? render.symbol_scale
    if (isFiniteNumber(renderSymbolScale)) {
      options.symbolScale = Number(renderSymbolScale)
    }
    if (typeof render.atakBadge === 'boolean') {
      options.atakBadge = render.atakBadge
    }
    if (typeof render.atak_badge === 'boolean') {
      options.atakBadge = render.atak_badge
    }

    const renderSize = isFiniteNumber(render.radius)
      ? Number(render.radius)
      : isFiniteNumber(render.size)
        ? Number(render.size)
        : null
    if (renderSize !== null) {
      options.renderSize = renderSize
    }

    if (isFiniteNumber(render.opacity)) {
      options.opacity = Number(render.opacity)
    }

    return options
  }

  const resolveFootprint = (entity) => normalizeRectFootprint(entity?.footprint)

  // Add drones from Phase 4 format
  if (state.nodes && state.nodes.length > 0) {
    for (const node of state.nodes) {
      const pos = resolvePosition(node, state.drone_positions?.[node.id])
      const droneType = node.type || (
                        node.role?.includes('compute') ? 'compute' :
                        node.role?.includes('soldier') ? 'soldier' :
                        node.id?.includes('recon') ? 'recon' :
                        node.id?.includes('attack') ? 'attack' : 'soldier')
      const render = resolveRenderOptions(node)

      entities.push(new Drone(node.id, droneType, pos, {
        label: node.label,
        status: node.status || 'active',
        behavior: node.behavior || state.drone_behaviors?.[node.id]?.current || 'lurk',
        transmissionRange: node.transmission_range,
        detectionRadius: Number(node.detection_radius) || 0,
        ...render
      }))
    }
  } else if (state.drones) {
    for (const drone of state.drones) {
      const pos = resolvePosition(drone)
      const render = resolveRenderOptions(drone)
      entities.push(new Drone(
        drone.id,
        drone.type,
        pos,
        {
          label: drone.label,
          status: drone.status,
          behavior: drone.behavior,
          transmissionRange: drone.transmission_range,
          detectionRadius: Number(drone.detection_radius) || 0,
          ...render
        }
      ))
    }
  }

  // Add enemies
  if (state.enemies) {
    for (const enemy of state.enemies) {
      const pos = resolvePosition(enemy)
      const render = resolveRenderOptions(enemy)
      entities.push(new Enemy(
        enemy.id,
        enemy.subtype || enemy.type,
        pos,
        {
          label: enemy.label,
          status: enemy.status,
          revealed: enemy.revealed,
          ...render
        }
      ))
    }
  }

  // Add structures
  if (state.structures) {
    for (const struct of state.structures) {
      const pos = resolvePosition(struct)
      const render = resolveRenderOptions(struct)
      entities.push(new Structure(
        struct.id,
        struct.subtype || struct.type,
        pos,
        {
          label: struct.label,
          status: struct.status,
          size: isFiniteNumber(struct.blocking_size) ? Number(struct.blocking_size) : undefined,
          footprint: resolveFootprint(struct),
          ...render
        }
      ))
    }
  }

  // Add special entities / points of interest
  if (state.special_entities) {
    for (const entity of state.special_entities) {
      const pos = resolvePosition(entity)
      const render = resolveRenderOptions(entity)
      entities.push(new PointOfInterest(
        entity.id,
        entity.subtype || entity.type,
        pos,
        {
          label: entity.label,
          status: entity.status,
          revealed: entity.revealed,
          ...render
        }
      ))
    }
  }

  return entities
}

/**
 * Helper: Get entities of specific type/allegiance
 */
export function filterEntities(entities, predicate) {
  return entities.filter(predicate)
}

export function getDronesByAllegiance(entities, allegiance) {
  return filterEntities(entities, e => e.allegiance === allegiance && e.type === 'drone')
}

export function getEnemies(entities) {
  return filterEntities(entities, e => e.allegiance === 'enemy')
}

export function getStructures(entities) {
  return filterEntities(entities, e => e.type === 'structure')
}

export function getLoSBlockingEntities(entities) {
  return filterEntities(entities, e => e.blocksLoS && e.status !== 'destroyed')
}
