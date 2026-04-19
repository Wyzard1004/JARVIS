# JARVIS Entity System Architecture

## Overview

The entity system provides a unified, object-oriented approach to managing all game objects in the swarm visualization:
- **Drones** (Allied units with transmission capabilities)
- **Enemies** (Hostile units)
- **Structures** (Buildings, terrain blocking LoS)
- **Points of Interest** (Downed aircraft, caches, checkpoints)

## Class Hierarchy

```
Entity (Base Class)
├── Drone extends Entity
├── Enemy extends Entity
├── Structure extends Entity
└── PointOfInterest extends Entity
```

## Core Features

### 1. Unified State Management
All entities share common properties:
- `id`: Unique identifier
- `type`: Entity type ('drone', 'enemy', 'structure', 'poi')
- `position`: [x, y] coordinates in 26×26 grid (pre-scaling)
- `allegiance`: 'allied', 'enemy', or 'neutral'
- `status`: 'active', 'destroyed', 'inactive'
- `shape`: Visual shape (circle, square, diamond, triangle, star, rectangle)
- `color`: Display color
- `blocksLoS`: Whether this entity blocks line of sight
- `revealed`: For hidden entities (enemies, POIs)

### 2. Line of Sight Blocking

Entities can block radio transmission between drones:

```javascript
entity.blocksLineOfSight(x1, y1, x2, y2)  // Returns boolean
```

This is used by `drawTransmissionLines()` to prevent drawing transmission links through obstacles:

```javascript
const blockingEntities = getLoSBlockingEntities(entities)
const isBlocked = isLineOfSightBlocked(x1, y1, x2, y2, blockingEntities)
```

### 3. Transmission Ranges

Each drone type has a transmission range (in cells):
- **Soldier**: 5 cells
- **Compute**: 12 cells  
- **Recon**: 3 cells
- **Attack**: 3 cells

Transmission lines are calculated server-side via the spanning tree algorithm but are visually blocked if terrain obstacles are in the way.

### 4. Entity Shapes

Different entity types display with different shapes:

| Type | Shape | Details |
|------|-------|---------|
| Soldier | Square | Command center operators |
| Compute | Diamond | Image processing nodes |
| Recon | Triangle | Scout drones |
| Attack | Star | Offensive drones |
| Enemy Tank | Square | Hostile armor |
| Enemy Soldier | Circle | Hostile infantry |
| Building | Rectangle | Urban structures, blocks LoS |
| Warehouse | Rectangle | Industrial structures, blocks LoS |
| Mountain | Square | Terrain features, blocks LoS |
| Downed Aircraft | Triangle | Recoverable asset |

### 5. Creating Entities

**From Phase 4 Backend State:**
```javascript
import { stateToEntities } from './lib/entities'

const entities = stateToEntities(swarmState)
```

**Manually:**
```javascript
import { Drone, Enemy, Structure, PointOfInterest } from './lib/entities'

// Create a drone
const drone = new Drone('soldier-1', 'soldier', [13, 7], {
  status: 'active',
  behavior: 'patrol'
})

// Create a building
const building = new Structure('building-1', 'building', [10, 10], {
  size: 1.2,  // 20% larger than normal
  blocksLoS: true
})

// Create an enemy
const enemy = new Enemy('tank-1', 'enemy_tank', [20, 20], {
  revealed: false  // Hidden until clicked
})
```

### 6. Filtering Entities

Helper functions for common queries:

```javascript
import { 
  getDronesByAllegiance, 
  getEnemies, 
  getStructures,
  getLoSBlockingEntities,
  filterEntities 
} from './lib/entities'

// Get all allied drones
const alliedDrones = getDronesByAllegiance(entities, 'allied')

// Get all enemies
const enemies = getEnemies(entities)

// Get structures
const structures = getStructures(entities)

// Get entities that block line of sight
const blockingObjects = getLoSBlockingEntities(entities)

// Custom filter
const activeDrones = filterEntities(
  entities, 
  e => e.type === 'drone' && e.status === 'active'
)
```

## Line of Sight System

### How It Works

1. **Identify Blocking Entities**: Find all entities with `blocksLoS: true` and `status !== 'destroyed'`

2. **Check Each Line**: For each transmission line (drone-to-drone):
   ```javascript
   const blocked = blockingEntities.some(entity =>
     entity.blocksLineOfSight(x1, y1, x2, y2)
   )
   if (blocked) skip this transmission line
   ```

3. **Geometric Calculation**:
   - Project entity position onto the transmission line
   - Calculate distance from entity to line
   - If distance < entity blocking radius, line is blocked

4. **Blocked Radius by Shape**:
   - Circles/Squares: `(size * 100px) / 2`
   - Rectangles: `(size * 100px) * 0.6` (wider blocking zone)

### Integration with SwarmCanvas

The `drawTransmissionLines()` function now:
1. Gets all blocking entities from structures
2. Checks each transmission link for LoS blockage
3. Only renders transmission lines that have clear line of sight
4. Spanning tree edges shown in golden (#FFD700) when unobstructed

## Future Enhancements

Potential extensions to the entity system:

1. **Entity Events**: `onDestroyed()`, `onRevealed()`, `onTransmission()`
2. **Terrain Costs**: Different entities have different traversal costs
3. **Entity Behaviors**: Move entities along paths, patrol routes
4. **Collision Detection**: Check if entities overlap
5. **Resource Management**: Ammo, fuel, battery levels via entity properties
6. **Faction System**: Different team colors/sizes
7. **Serialization**: Save/load entity state to backend

## Files

- `/src/lib/entities.js` - Core entity classes and helpers
- `/src/components/SwarmCanvas.jsx` - Visualization using entities
- `/src/components/DroneStatusCard.jsx` - Entity detail display

## Design Principles

1. **Single Responsibility**: Each class manages its own rendering/collision logic
2. **Immutability**: Create new entities rather than mutating existing ones
3. **Testability**: Entity logic is independent of React/Canvas
4. **Extensibility**: Easy to add new entity types via inheritance
5. **Performance**: Lazy evaluation of LoS blocking (only when needed)
