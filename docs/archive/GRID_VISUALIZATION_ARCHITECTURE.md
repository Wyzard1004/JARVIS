# JARVIS Grid-Based Visualization Architecture

**Version**: 1.0  
**Date**: April 18, 2026  
**Status**: Implementation Plan  

---

## Executive Summary

This document outlines a complete rewrite of the visualization system, replacing D3 force-graph with a custom Canvas-based grid coordinate system. Drones operate on a 26×26 NATO-phonetic grid (Alpha-Zulu × 1-26), move at discrete cell-based velocities, and communicate within range-limited transmission zones. The backend (`swarm_logic.py`) enforces transmission ranges and uses a spanning tree gossip protocol for message propagation.

---

## 1. Grid System & Coordinate Model

### 1.1 Grid Architecture

- **Dimensions**: 26×26 grid = 676 total cells
- **Row Labels**: NATO Phonetic Alphabet (Alpha, Bravo, Charlie, ... Zulu)
- **Column Labels**: Numbers 1-26
- **Grid Notation**: `Alpha-1`, `Bravo-12`, `Zulu-26`, etc.
- **Canvas Size**: 780×780 pixels (30px cells, scalable with zoom)
- **Cell Indexing**: 0-indexed internally, displayed as 1-indexed to operators

### 1.2 Coordinate Translation Layer

**GridCoordinateSystem** utility class:

```
Grid Position (A, 1) ↔ Pixel Position (0, 0)
Grid Position (Z, 26) ↔ Pixel Position (750, 750)
Grid-to-Pixel: x_px = col * cell_width, y_px = row * cell_height
Pixel-to-Grid: col = x_px / cell_width, row = y_px / cell_height
```

**Distance Calculations**:
- Euclidean: `sqrt((x2-x1)² + (y2-y1)²)`
- Manhattan: `|x2-x1| + |y2-y1|`
- Used for transmission range checks and pathfinding

### 1.3 Transmission Ranges (Radio Propagation)

**Drone Type → Max Transmission Range**:

| Drone Type | Range (Cells) | Notes |
|------------|---------------|-------|
| Recon Drone | 3 cells | Limited by antenna size, high altitude helps |
| Attack Drone | 3 cells | Similar to recon, combat-oriented |
| Soldier Operator | 5 cells | Mobile relay station, larger antenna |
| Compute Drone | 12 cells | Primary hub; long-range repeater |
| Gateway | 10 cells | Base station (if implemented) |

**Range Enforcement**:
- Only nodes within max range can establish direct links
- Gossip protocol respects these physical constraints
- Out-of-range nodes must relay through intermediate nodes

---

## 2. Entity Representation & Behavior

### 2.1 Drone States & Types

**Node Data Structure** (in swarm_logic.py):

```python
{
    "id": "recon-1",
    "label": "Recon Drone 1",
    "role": "recon-drone",
    "grid_position": {"row": "Alpha", "col": 5},     # Current cell
    "pixel_position": {"x": 150, "y": 150},          # Current pixel (for rendering)
    "behavior": "patrol" | "lurk" | "transit",       # Current behavior
    "behavior_state": {
        "waypoints": [{"row": "A", "col": 5}, ...],  # For patrol/transit
        "current_waypoint_index": 0,
        "speed": 1.0,  # cells per second
        "progress": 0.35  # 0.0-1.0 through current cell
    },
    "transmission_range": 3,                          # Max range in cells
    "status": "active" | "idle" | "damaged",
    "health": 0.95,
    "fuel_percent": 85,
    "render": {
        "radius": 12,                                 # Pixel circle radius
        "color": "#FF6B6B",                          # Recon color
        "opacity": 1.0,                              # For fade effects
        "glow": false                                # Highlighting
    }
}
```

**Entity Type Encodings**:

Enemies:
```python
{
    "id": "enemy-tank-1",
    "entity_type": "enemy",
    "subtype": "tank",
    "grid_position": {"row": "Bravo", "col": 12},
    "status": "active" | "destroyed",
    "render": {
        "shape": "square",
        "size": 16,
        "color": "#FF0000",
        "opacity": 1.0
    }
}
```

Structures/Landmarks:
```python
{
    "id": "structure-building-1",
    "entity_type": "structure",
    "subtype": "building" | "bridge" | "warehouse" | "downed-plane",
    "grid_position": {"row": "Charlie", "col": 8},
    "status": "intact" | "damaged" | "destroyed",
    "render": {
        "shape": "circle" | "square" | "triangle",
        "size": 20,
        "color": "#4A5568",
        "opacity": 1.0
    }
}
```

### 2.2 Drone Behaviors

**Lurk** (stationary):
- Drone remains at current grid cell
- Subtle breathing animation (scale ±5%)
- Participation: Full network comms, listening for commands

**Patrol** (multi-waypoint):
- Given waypoint list: `[A-5, B-8, B-12, C-9, A-5]` (returns to start)
- Moves 1 cell per second between waypoints
- Linear interpolation between grid centers
- Participation: Continuous range checks as it moves; gossip updates during transit

**Transit** (point-to-point):
- Direct path from current position to target
- Speed: 1 cell per second (variable by drone type TBD)
- Arrival: Transitions to `lurk` unless given new orders

**Swarming** (coordinated clustering):
- All participating drones move toward target grid cell
- Formation-preserving: Maintain relative spacing
- Arrival at cell: Spread formation around target (don't stack on same cell)

### 2.3 Drone Lifecycle

1. **Spawning**: Fade in (opacity 0 → 1) over 500ms
2. **Active**: Movement, comms, mission execution
3. **Damaged/Degraded**: Opacity reduced, color shift (red tint), movement slowed
4. **Destroyed**: Rapid fade out (1000ms), stop transmitting
5. **Recovered**: Fade in from destroyed state, resume operations

---

## 3. Gossip Protocol & Transmission System

### 3.1 Spanning Tree Gossip with Range Constraints

**Consensus Algorithm** (in swarm_logic.py):

1. **Build Connectivity Graph**:
   - For each drone, identify all neighbors within transmission range
   - Edge weight = link quality (0.9-1.0) × (1 - path_loss_factor)
   - Asymmetric links possible (A can reach B, but B cannot reach A)

2. **Spanning Tree Construction**:
   - Use Prim's or Kruskal's algorithm on neighbor graph
   - Root at primary compute drone or soldier-1
   - Ensures minimal redundancy while covering all reachable nodes

3. **Message Propagation**:
   - Root initiates message with `timestamp` and `TTL=3`
   - Each node retransmits to all spanning tree children
   - Children acknowledge parent to confirm receipt
   - If ACK timeout within 150ms: parent retries (max 2 retries)

4. **Out-of-Range Recovery**:
   - Drone moving into range: Discovers tree, joins at nearest node
   - Drone moving out of range: Marked as isolated, waits for re-entry
   - Isolated nodes can still operate locally; state syncs on re-connection

### 3.2 Propagation Animation

**Visual Feedback** (in Canvas renderer):

- **Pulse Effect**: Lines connecting nodes light up sequentially as message propagates
- **Timing**: Each node pulses 100ms after receiving (simulates processing)
- **Color Gradient**: Green (sent) → Yellow (processing) → Dim (delivered)
- **Duration**: Pulse lasts 200ms, then returns to idle state (thin gray line)

---

## 4. Backend Integration (swarm_logic.py Remapping)

### 4.1 SwarmCoordinator Refactoring

**New Methods**:

```python
def add_node(self, drone_id, grid_position, drone_type, behavior="lurk"):
    """Add drone to swarm with grid coordinates and behavior"""
    pass

def set_drone_waypoints(self, drone_id, waypoints):
    """Set patrol path as list of grid positions"""
    pass

def calculate_transmission_graph(self):
    """Build neighbor graph respecting transmission ranges"""
    pass

def compute_spanning_tree(self, root_node=None):
    """Construct spanning tree for gossip propagation"""
    pass

def broadcast_message(self, sender_id, message, priority="high"):
    """Initiate message propagation through spanning tree"""
    pass

def update_drone_positions(self, delta_time_ms):
    """Update all drone positions based on behavior and waypoints"""
    pass

def get_grid_state(self):
    """Export current state: drones, enemies, structures, transmission edges"""
    pass
```

**New Data Structures**:

```python
class DroneState:
    grid_position: tuple  # (row_idx, col_idx) 0-indexed
    behavior: str  # "lurk", "patrol", "transit", "swarm"
    waypoints: List[tuple]  # For patrol/transit
    speed: float  # cells/second (1.0 default)
    transmission_range: int  # cells
    health: float  # 0.0-1.0
    fuel: float  # 0-100%

class MissionEvent:
    timestamp: int  # ms since start
    drone_id: str
    event_type: str  # "discovered", "destroyed", "comms_lost", etc.
    grid_position: tuple  # Where event occurred
    details: str  # "tank spotted at Alpha-9", etc.
    severity: str  # "critical", "info", "warning"
```

### 4.2 Swarm Config File Format

**Location**: `base_station/config/swarm_initial_state.json`

```json
{
  "scenario": "Alpha Village Reconnaissance",
  "grid_size": 26,
  "drones": [
    {
      "id": "recon-1",
      "type": "recon-drone",
      "grid_position": {"row": 0, "col": 5},
      "behavior": "patrol",
      "waypoints": [
        {"row": 0, "col": 5},
        {"row": 2, "col": 8},
        {"row": 5, "col": 10},
        {"row": 0, "col": 5}
      ],
      "speed": 1.0,
      "health": 0.95,
      "fuel": 85
    },
    {
      "id": "compute-1",
      "type": "compute-drone",
      "grid_position": {"row": 13, "col": 13},
      "behavior": "lurk",
      "transmission_range": 12,
      "health": 1.0,
      "fuel": 100
    },
    {
      "id": "attack-1",
      "type": "attack-drone",
      "grid_position": {"row": 10, "col": 15},
      "behavior": "lurk",
      "health": 0.95,
      "fuel": 90
    }
  ],
  "enemies": [
    {
      "id": "enemy-tank-1",
      "subtype": "tank",
      "grid_position": {"row": 5, "col": 10},
      "status": "active"
    },
    {
      "id": "enemy-infantry-1",
      "subtype": "infantry",
      "grid_position": {"row": 6, "col": 11},
      "status": "active"
    }
  ],
  "structures": [
    {
      "id": "building-1",
      "subtype": "building",
      "grid_position": {"row": 7, "col": 12},
      "status": "intact"
    },
    {
      "id": "downed-plane-1",
      "subtype": "downed-plane",
      "grid_position": {"row": 3, "col": 4},
      "status": "active"
    }
  ]
}
```

### 4.3 State Output for React (WebSocket Payload)

```json
{
  "timestamp": 1234567890,
  "drones": [
    {
      "id": "recon-1",
      "grid_position": {"row": "Alpha", "col": 5},
      "pixel_position": {"x": 150, "y": 150},
      "behavior": "patrol",
      "health": 0.95,
      "transmission_range": 3,
      "render": {
        "radius": 12,
        "color": "#FF6B6B",
        "opacity": 1.0
      }
    }
  ],
  "transmission_graph": [
    {"source": "recon-1", "target": "compute-1", "distance": 2.5}
  ],
  "propagation_events": [
    {
      "timestamp": 1234567892,
      "message_id": "msg-42",
      "source": "soldier-1",
      "path": ["soldier-1", "compute-1", "recon-1"],
      "pulses": [
        {"node": "soldier-1", "start_ms": 0},
        {"node": "compute-1", "start_ms": 100},
        {"node": "recon-1", "start_ms": 200}
      ]
    }
  ],
  "enemies": [...],
  "structures": [...]
}
```

---

## 5. React UI Components (Canvas-Based)

### 5.1 SwarmCanvas Component (replaces SwarmGraph.jsx)

**Props**:
```jsx
<SwarmCanvas
  state={swarmState}           // Full swarm state from WebSocket
  cellSize={30}                 // Pixels per grid cell
  showGrid={true}               // Display grid overlay
  showLabels={true}             // Display row/col labels
  selectedDrone={droneId}       // Highlight drone
  onDroneClick={(droneId) => {}}
/>
```

**Features**:
- HTML5 Canvas rendering (2D context)
- Grid background with labeled rows (Alpha-Zulu) and cols (1-26)
- Efficient dirty-region redraws (only update changed areas)
- requestAnimationFrame loop (~60 FPS)
- Mouse interaction: click drones, hover for tooltips

**Rendering Pipeline**:

1. **Clear & Setup** (every frame):
   - Clear canvas
   - Draw grid overlay (light gray lines)
   - Draw labels (row/col headers)

2. **Draw Stationary Entities**:
   - Structures & enemies (don't move)
   - Render as squares/triangles at grid positions

3. **Draw Transmission Graph**:
   - Lines between drones within range
   - Pulsing animation for active gossip propagation
   - Opacity = link quality (0.3-1.0)

4. **Draw Drones**:
   - Circles at interpolated pixel positions
   - Color-coded by type
   - Glow for selected drone
   - Opacity = health/status

5. **Debug Overlay** (optional):
   - Transmission range circles (dashed)
   - Waypoint paths (dotted lines)
   - Coordinate display on hover

### 5.2 EventConsole Component (new)

**Props**:
```jsx
<EventConsole
  events={missionEvents}       // Array of MissionEvent objects
  maxVisible={20}              // Max events shown (oldest scrolls off)
  autoScroll={true}            // Scroll to newest event
  colorize={true}              // Color-code by severity
/>
```

**Features**:
- Scrollable div with event list
- Auto-scroll to newest (bottom)
- No auto-clear (events persist until scrolled off)
- Timestamps (HH:MM:SS.ms)
- Color coding: red (critical, destroyed), yellow (warning), green (info)

**Event Format Displayed**:
```
[00:01:32.456] Recon-1: Discovered enemy tank at Alpha-9
[00:01:45.123] Compute-1: Processing image data from Recon-1
[00:02:10.789] Attack-1: Destroyed tank at Alpha-9
[00:02:11.012] Recon-2: Confirmed tank destruction at Alpha-9
```

### 5.3 Grid Legend Component (new)

**Sections**:
- **NATO Phonetic Chart**: A-Z with phonetic spelled out
- **Drone Types & Colors**:
  - Recon: #FF6B6B (red)
  - Attack: #FF0000 (bright red)
  - Compute: #4A90E2 (blue)
  - Soldier: #9B59B6 (purple)
- **Entity Types**:
  - Enemy Tank: #FF0000 (red square)
  - Enemy Infantry: #FF6B6B (red circle)
  - Building: #4A5568 (gray square)
  - Downed Plane: #FFD93D (yellow triangle)
- **Active Drones List**: Table with ID, position, health, status

### 5.4 DroneStatusCard Component (new)

**Displays**:
- Drone ID & type
- Current grid position
- Behavior (Lurk/Patrol/Transit)
- Health & fuel
- Transmission range
- Next waypoint (if patrolling)
- Comms status (in-range/out-of-range)

---

## 6. Movement & Animation System

### 6.1 Movement Physics

**1 Cell = 1 Second Travel Time**

**Linear Interpolation Between Cells**:

```
progress = (current_time - cell_start_time) / 1000  // 0.0 to 1.0
pixel_x = start_x + (end_x - start_x) * progress
pixel_y = start_y + (end_y - start_y) * progress
```

**Easing Functions** (optional smoothing):
- Ease-In-Out: Smooth acceleration/deceleration at cell boundaries
- Formula: `ease(t) = t < 0.5 ? 2t² : 1 - 2(1-t)²`

### 6.2 Fade In/Out

**Spawning** (fade in):
```
opacity = 0 + (1 - 0) * (time_elapsed / 500)  // 500ms
```

**Destruction** (fade out):
```
opacity = 1 - (1 - 0) * (time_elapsed / 1000)  // 1000ms
```

### 6.3 Idle Animation (Breathe)

**For lurking drones**:
```
scale = 1.0 + 0.05 * sin(time * 2π / 2000)  // 2-second cycle
```

---

## 7. AI Bridge Integration

### 7.1 Command Parsing

**Llama 3 Output** (existing):
```json
{
  "intent": "swarm_redeploy",
  "target_location": "Grid Alpha",
  "action_code": "RED_ALERT",
  "confidence": 0.95
}
```

**Translation Layer** (new):
```python
def parse_llm_command(llm_output):
    intent = llm_output["intent"]
    target = llm_output["target_location"]
    
    # Convert "Grid Alpha" → row index 0
    row_index = convert_nato_to_row(target.split()[-1])
    
    # Generate waypoints based on intent
    if intent == "swarm_redeploy":
        # Gather all drones toward (row_index, 13) center
        for drone in swarm.drones:
            swarm.set_drone_waypoints(drone.id, 
                generate_converge_path(drone.pos, (row_index, 13)))
    
    return swarm.get_grid_state()
```

### 7.2 Event Publishing to MQTT

**Topic Structure**:
```
jarvis/events/{event_type}/{drone_id}
jarvis/swarm/state
jarvis/command/response
```

**Payload Example**:
```json
{
  "topic": "jarvis/events/discovery/recon-1",
  "payload": {
    "timestamp": 1234567890,
    "drone_id": "recon-1",
    "event_type": "enemy_discovered",
    "target_type": "tank",
    "grid_position": {"row": "Alpha", "col": 9},
    "confidence": 0.92
  }
}
```

---

## 8. Implementation Sequence

### Phase 1: Core Utilities & Backend (Week 1)

- [ ] **GridCoordinateSystem class** (utility)
  - Row/col ↔ pixel conversion
  - Distance calculations
  - Waypoint generation (4 points/cell for smooth paths)

- [ ] **Update SwarmCoordinator** (swarm_logic.py)
  - Add grid_position to all nodes
  - Implement transmission range constraints
  - Build spanning tree gossip propagation
  - Add behavior state tracking
  - Implement update_drone_positions() with movement physics
  - Add swarm config file loader

- [ ] **MissionEvent & EventBus classes**
  - Event type enumeration
  - Event serialization for WebSocket

### Phase 2: Canvas Renderer (Week 1-2)

- [ ] **SwarmCanvas component**
  - Grid overlay rendering
  - Drone circle rendering with movement
  - Transmission line rendering
  - Gossip pulse animation
  - Performance optimization (dirty regions)

- [ ] **EventConsole component**
  - Scrollable event list
  - Auto-scroll to bottom
  - Color-coded severity

- [ ] **Grid Legend component**
  - NATO phonetic reference
  - Drone type colors & markers
  - Entity type reference

### Phase 3: Integration & Testing (Week 2)

- [ ] **WebSocket payload update**
  - Include grid positions, transmission graph, propagation events

- [ ] **AI Bridge → Grid commands**
  - Parse LLM intent to grid coordinates
  - Generate waypoint lists

- [ ] **Testing scenarios**
  - Load swarm_initial_state.json
  - Simulate patrols, gossip propagation, comms loss

---

## 9. Performance Targets

| Metric | Target |
|--------|---------|
| Canvas render FPS | 50-60 FPS (26×26 grid, 20 drones) |
| Network update latency | <50ms (WebSocket) |
| Gossip propagation time | <500ms (full swarm) |
| Drone movement smoothness | Linear interpolation, no stuttering |
| Event console scroll | <16ms per frame (60 FPS) |

---

## 10. Testing Checklist

- [ ] Grid coordinate conversion (pixel ↔ grid) accuracy
- [ ] Transmission range enforcement (3-cell radius for recon, 12-cell for compute)
- [ ] Spanning tree correctness (no cycles, all reachable nodes included)
- [ ] Movement speed (drones traverse 1 cell in ~1000ms)
- [ ] Gossip pulse animation (100ms processing delay, 200ms pulse duration)
- [ ] Event console scrolling & formatting
- [ ] Load swarm_initial_state.json correctly
- [ ] Draw enemies/structures at correct grid positions
- [ ] Fade in/out animations smoothly
- [ ] Hover tooltips display drone info
- [ ] Click drone to select/highlight
- [ ] Out-of-range recovery (drone re-joined spanning tree)

---

## 11. File Structure

```
base_station/
  config/
    swarm_initial_state.json     ← NEW
  core/
    grid_coordinate_system.py    ← NEW
    swarm_logic.py               ← REFACTORED
    mission_event_bus.py         ← NEW

command_center/
  src/
    components/
      SwarmCanvas.jsx            ← NEW (replaces SwarmGraph.jsx)
      EventConsole.jsx           ← NEW
      GridLegend.jsx             ← NEW
      DroneStatusCard.jsx        ← NEW
    utils/
      gridUtils.js               ← NEW (client-side grid helpers)
      canvasRenderer.js          ← NEW (canvas drawing functions)
```

---

## Next Steps

1. **Create GridCoordinateSystem** in swarm_logic.py
2. **Design swarm_initial_state.json** with test scenarios
3. **Build SwarmCanvas** component with grid overlay
4. **Implement drone movement** physics & interpolation
5. **Add gossip pulse animation** to transmission lines
6. **Build EventConsole** and integrate with WebSocket feeds
7. **Test end-to-end** with AI Bridge commands
