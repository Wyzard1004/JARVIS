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

/**
 * Base Entity Class
 * All entities inherit from this base
 */
export class Entity {
  constructor(id, type, position, options = {}) {
    this.id = id
    this.type = type // 'drone', 'enemy', 'structure', 'poi'
    this.position = position // [x, y] in continuous 1000×1000 coordinate system
    this.allegiance = options.allegiance || 'neutral' // 'allied', 'enemy', 'neutral'
    this.status = options.status || 'active' // 'active', 'destroyed', 'inactive'
    this.size = options.size || 1 // Relative size (1 = normal)
    this.shape = options.shape || 'circle' // 'circle', 'square', 'diamond', 'triangle', 'star', 'rectangle'
    this.color = options.color || '#999999'
    this.blocksLoS = options.blocksLoS || false // Does this entity block line of sight?
    this.transmissionRange = options.transmissionRange || 0 // Euclidean distance in 1000×1000 space
    this.revealed = options.revealed !== false // For hidden entities
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
   * Get display position scaled to 6×6 grid from 1000×1000 coordinates
   * Scale factor: 1000 / 6 ≈ 166.67 units per grid cell
   */
  getScaledPosition() {
    const SCALE = 1000 / 6
    return [
      Math.floor(this.position[0] / SCALE),
      Math.floor(this.position[1] / SCALE)
    ]
  }
}

/**
 * Drone Entity (Allied)
 * Transmission ranges use Euclidean distance in 1000×1000 coordinate space
 * Scale: 1000/6 ≈ 166.67 units per grid cell
 */
export class Drone extends Entity {
  constructor(id, droneType, position, options = {}) {
    super(id, 'drone', position, {
      allegiance: 'allied',
      shape: {
        soldier: 'square',
        compute: 'diamond',
        recon: 'triangle',
        attack: 'star'
      }[droneType] || 'circle',
      color: {
        soldier: '#9B59B6',
        compute: '#4A90E2',
        recon: '#FF6B6B',
        attack: '#FF0000'
      }[droneType] || '#999999',
      transmissionRange: {
        soldier: 750,      // ~4.5 cells, Euclidean distance
        compute: 1800,     // ~10.8 cells, long-range relay
        recon: 500,        // ~3 cells, short range
        attack: 500        // ~3 cells, short range
      }[droneType] || 500,
      ...options
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
    super(id, 'enemy', position, {
      allegiance: 'enemy',
      shape: {
        'enemy_soldier': 'circle',
        'enemy_tank': 'square',
        'enemy_helicopter': 'triangle'
      }[enemyType] || 'circle',
      color: {
        'enemy_soldier': '#FF6B6B',
        'enemy_tank': '#8B0000',
        'enemy_helicopter': '#FF4500'
      }[enemyType] || '#FF0000',
      revealed: options.revealed !== undefined ? options.revealed : false,
      ...options
    })
    this.enemyType = enemyType
  }
}

/**
 * Structure Entity (Neutral, usually blocking)
 */
export class Structure extends Entity {
  constructor(id, structureType, position, options = {}) {
    super(id, 'structure', position, {
      allegiance: 'neutral',
      blocksLoS: true, // Structures block line of sight by default
      shape: {
        'building': 'rectangle',
        'warehouse': 'rectangle',
        'mountain': 'square',
        'bridge': 'rectangle'
      }[structureType] || 'rectangle',
      color: {
        'building': '#4A4A4A',
        'warehouse': '#3A3A3A',
        'mountain': '#8B7355',
        'bridge': '#666666'
      }[structureType] || '#4A4A4A',
      size: options.size || 0.8,
      ...options
    })
    this.structureType = structureType
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
    super(id, 'poi', position, {
      allegiance: 'neutral',
      blocksLoS: false,
      shape: {
        'downed_aircraft': 'triangle',
        'cache': 'square',
        'checkpoint': 'circle'
      }[poiType] || 'circle',
      color: {
        'downed_aircraft': '#FFD93D',
        'cache': '#FFB347',
        'checkpoint': '#87CEEB'
      }[poiType] || '#CCCCCC',
      revealed: options.revealed !== undefined ? options.revealed : false,
      ...options
    })
    this.poiType = poiType
  }
}

/**
 * Helper: Convert old state format to new Entity objects
 */
export function stateToEntities(state) {
  const entities = []
  
  /**
   * Convert from 26×26 grid coordinates to 1000×1000 continuous space
   * Scale: 1000 / 26 ≈ 38.46 units per grid cell
   * Add small random offset for exact positioning (not grid-locked)
   */
  const gridToCoords = (gridPos) => {
    if (!gridPos || !Array.isArray(gridPos)) return [500, 500]
    const SCALE = 1000 / 26
    const offset = () => (Math.random() - 0.5) * SCALE * 0.5 // ±25% of cell size
    return [
      gridPos[0] * SCALE + offset(),
      gridPos[1] * SCALE + offset()
    ]
  }

  // Add drones from Phase 4 format
  if (state.nodes && state.nodes.length > 0) {
    for (const node of state.nodes) {
      const oldPos = state.drone_positions?.[node.id] || [3, 3]
      const pos = gridToCoords(oldPos)
      const droneType = node.role?.includes('compute') ? 'compute' :
                        node.role?.includes('soldier') ? 'soldier' :
                        node.id?.includes('recon') ? 'recon' :
                        node.id?.includes('attack') ? 'attack' : 'soldier'

      entities.push(new Drone(node.id, droneType, pos, {
        status: node.status || 'active',
        behavior: state.drone_behaviors?.[node.id]?.current || 'lurk'
      }))
    }
  } else if (state.drones) {
    // Legacy format
    for (const drone of state.drones) {
      const pos = gridToCoords(drone.grid_position)
      entities.push(new Drone(
        drone.id,
        drone.type,
        pos,
        { status: drone.status, behavior: drone.behavior }
      ))
    }
  }

  // Add enemies
  if (state.enemies) {
    for (const enemy of state.enemies) {
      const pos = gridToCoords(enemy.grid_position)
      entities.push(new Enemy(
        enemy.id,
        enemy.subtype,
        pos,
        { status: enemy.status, revealed: false }
      ))
    }
  }

  // Add structures
  if (state.structures) {
    for (const struct of state.structures) {
      const pos = gridToCoords(struct.grid_position)
      entities.push(new Structure(
        struct.id,
        struct.subtype,
        pos,
        { status: struct.status }
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
