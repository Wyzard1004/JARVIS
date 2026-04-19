# Visualization Flickering Fix - SwarmGraph.jsx

## Problem
The swarm visualization was flickering - nodes appeared to jump around instead of moving smoothly between positions. This was caused by the SVG being completely cleared and redrawn on every state update.

## Root Cause
The original code was calling `d3.select(svgRef.current).selectAll('*').remove()` on each useEffect, which destroyed all D3 elements. This caused:
- Loss of D3 force simulation state
- Nodes losing momentum and position context
- Complete visual reset on each frame

## Solution: Persistent Element Pattern

### Key Changes to `command_center/src/components/SwarmGraph.jsx`

#### 1. Added Persistent State Reference
```javascript
const svgElementsRef = useRef(null)  // Store SVG selections for reuse
const enemies = state?.enemies || state?.data?.enemies || []
const signalAnimations = state?.signal_animations || state?.data?.signal_animations || []
```

#### 2. Removed Complete Redraw
- **Before:** `d3.select(svgRef.current).selectAll('*').remove()`
- **After:** Uses conditional first-time setup with persistent elements

#### 3. One-Time Initialization Pattern
```javascript
if (svgElementsRef.current === null) {
  // Create simulation, links, nodes, labels ONCE
  // Store references for reuse
  svgElementsRef.current = {
    simulation,
    linkGroup,
    nodeGroup,
    pulseGroup,
    labelGroup,
    nodes,
    links
  }
} else {
  // UPDATE: Only modify colors, opacity, and positions
}
```

#### 4. Smart Edge Visibility
- Added logic to track active signals from `signalAnimations` state
- Edges now hidden by default: `attr('opacity', 0)`
- Edges only visible when signals traverse them: `attr('opacity', (d, i) => activeSignalEdges.has(i) ? 0.6 : 0)`
- Edge opacity set based on: `links.findIndex(l => (l.source === sig.from_node && l.target === sig.to_node) ...)`

#### 5. Proper Enter/Update/Exit Pattern
```javascript
const linkGroup = svg.selectAll('.link-group')
  .data(links, (d, i) => i)
  .join(
    enter => enter.append('g')
      .attr('class', 'link-group')
      .append('line')
      .attr('opacity', 0)  // Hidden until signal active
  )
```

#### 6. Smooth Position Updates
- Position updates happen via `simulation.on('tick', updatePositions())`
- D3 force simulation naturally animates node movement
- Nodes positions come from backend: `node.x, node.y` (not hardcoded)
- Links positions computed from node coordinates: `d.source.x, d.source.y, d.target.x, d.target.y`

#### 7. Canvas Size Improvements
- Increased from `800x384` to `1000x600` for better visibility
- Matches expanded 15-node swarm layout (2 soldiers, 2 compute, 5 recon, 6 attack)

### Updated Dependencies
Changed from:
```javascript
}, [state, propagationTimings])
```

To:
```javascript
}, [state, propagationTimings, currentTime])
```

This enables smooth animation of node colors and pulse effects as time advances.

## Benefits

✅ **Smooth Movement**: Nodes move naturally with D3 force simulation instead of jumping  
✅ **No Flickering**: SVG elements persist; only data updates  
✅ **Smart Edges**: Edges only visible when signals transit them  
✅ **Data-Driven**: No hardcoded positions or connections  
✅ **Performance**: Single D3 simulation vs. recreating each frame  
✅ **Visual Stability**: Anchor forces keep soldiers/gateway/compute drones stable  

## Technical Details

### Links Visibility Logic
- Each edge starts with `opacity: 0` (invisible)
- When `signalAnimations` contains a signal for an edge, that edge becomes visible: `opacity: 0.6`
- Signal presence calculated by matching `signal.from_node` and `signal.to_node` with link source/target

### Position Updates
- Nodes: Positioned via `attr('transform', d => \`translate(${d.x},${d.y})\`)`
- Links: Drawn from `d.source.x, d.source.y` to `d.target.x, d.target.y`
- All positions computed from state data and force simulation, never hardcoded

### Drone Type Support
- Updated anchor strength for **compute drones** (alongside existing gateway support)
- Soldiers get strongest anchor (0.8) to keep them stationary at home
- Gateway/compute get medium anchor (0.5) for stability with some movement
- Recon/attack drones use dynamic anchoring (0.35 for active, 0.1 for inactive)

## Testing Recommendations

1. **Smooth Movement**: Watch nodes move - should see natural arcs, not jumpy jumps
2. **Edge Visibility**: Launch a signal and verify edges light up only along the path
3. **Multiple Signals**: Test with overlapping signals - edges should correctly show/hide
4. **Responsive Updates**: Change node state and verify colors update without position jumps
5. **Drag Interaction**: Click and drag nodes - should work smoothly with force simulation

## Files Modified

- `command_center/src/components/SwarmGraph.jsx` - Complete visualization refactor

## Related Changes

This fix complements:
- AI LLM pipeline strictness fix (handles 12-sector location parsing)
- Compute drone rebrand (supports compute drone types in visualization)
- Expanded 15-node topology (15 nodes displayed with proper spacing)
