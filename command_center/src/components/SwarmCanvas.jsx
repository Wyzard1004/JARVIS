/**
+ * SwarmCanvas Component (Urban Combat Edition - Phase 4)
 * 
 * Renders an 8x8 NATO grid for urban combat scenarios with:
 * - 8x8 grid (Alpha-Hotel, 1-8) with 125 coordinate units per cell
 * - Dynamic drone circles (7px radius)
 * - Symbolic shapes within circles (drone type indicators)
 * - Dynamic transmission lines with proper line-of-sight blocking
 * - Hidden enemies/destroyed aircraft until revealed
 * - Urban terrain features (buildings blocking line of sight)
 * - Gossip protocol visualization in urban environment
 * 
 * Uses HTML5 Canvas for high-performance rendering with dark theme.
 * Entity system provides unified state management for all game objects.
 */

import React, { useEffect, useRef, useState } from 'react'
import { stateToEntities, getLoSBlockingEntities } from '../lib/entities'

// 8x8 URBAN COMBAT GRID (Alpha-Halo, 1-8) - 125 units per cell
const CELL_SIZE = 75 // 75px per grid cell (600px / 8 cells)
const GRID_SIZE = 8 // 8x8 (A-H, 1-8) - clean 125 coordinate units per cell
const CANVAS_WIDTH = GRID_SIZE * CELL_SIZE // 600px
const CANVAS_HEIGHT = GRID_SIZE * CELL_SIZE // 600px

const NATO_PHONETIC_SHORT = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel']

// Drone type symbols (shapes inside circles)
const DRONE_SYMBOLS = {
  soldier: 'square',      // operator in command center
  compute: 'diamond',     // computational processing
  recon: 'triangle',      // scout/reconnaissance 
  attack: 'star',         // offensive capability
}

// Entity colors (hidden until revealed)
const ENTITY_COLORS = {
  enemy_soldier: '#FF6B6B',    // Red circle
  enemy_tank: '#8B0000',       // Dark red square
  downed_aircraft: '#FFD93D',  // Yellow triangle (hidden)
  building: '#4A4A4A',         // Dark grey (terrain)
  warehouse: '#3A3A3A',        // Darker grey
}

function SwarmCanvas({ state = {}, selectedDrone = null, onDroneClick = () => {} }) {
  const canvasRef = useRef(null)
  const [hoveredDrone, setHoveredDrone] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [revealedEnemies, setRevealedEnemies] = useState(new Set())
  const animationFrameRef = useRef(null)

  // Convert state to unified entity system (1000×1000 coordinates)
  const entities = stateToEntities(state)
  
  // Extract entities by type
  const drones = entities.filter(e => e.type === 'drone')
  const droneMap = new Map(drones.map(d => [d.id, d]))
  
  // Transmission graph from Phase 4 state
  const transmissionGraph = (state.edges || []).map(edge => ({
    source: edge.source,
    target: edge.target,
    quality: edge.quality || 0.5,
    in_spanning_tree: edge.in_spanning_tree || false
  }))
  
  // Blocking entities for line of sight
  const blockingEntities = entities.filter(e => e.blocksLoS && e.status !== 'destroyed')

  // Convert 1000×1000 coordinates to canvas pixels (600×600)
  const coordsToPixel = (x, y) => {
    // Scale: 600 / 1000 = 0.6
    return [x * 0.6, y * 0.6]
  }

  // Check if line of sight is blocked by terrain and structures
  const isLineOfSightBlocked = (x1, y1, x2, y2, blockingEntities) => {
    // Check each blocking entity (buildings, mountains, etc.)
    for (const entity of blockingEntities) {
      if (entity.blocksLineOfSight(x1, y1, x2, y2)) {
        return true
      }
    }
    return false
  }

  // Render grid background with dark theme
  const drawGrid = (ctx) => {
    ctx.fillStyle = '#1A1A1A'
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    ctx.strokeStyle = '#333333'
    ctx.lineWidth = 1
    for (let col = 0; col <= GRID_SIZE; col++) {
      const x = col * CELL_SIZE
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, CANVAS_HEIGHT)
      ctx.stroke()
    }
    for (let row = 0; row <= GRID_SIZE; row++) {
      const y = row * CELL_SIZE
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(CANVAS_WIDTH, y)
      ctx.stroke()
    }
  }

  // Draw row/column labels
  const drawLabels = (ctx) => {
    ctx.font = 'bold 12px monospace'
    ctx.fillStyle = '#666666'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    for (let row = 0; row < GRID_SIZE; row++) {
      const y = row * CELL_SIZE + CELL_SIZE / 2
      const label = NATO_PHONETIC_SHORT[row].substring(0, 3)
      ctx.save()
      ctx.translate(-18, y)
      ctx.rotate(-Math.PI / 2)
      ctx.fillText(label, 0, 0)
      ctx.restore()
    }
    for (let col = 0; col < GRID_SIZE; col++) {
      const x = col * CELL_SIZE + CELL_SIZE / 2
      ctx.fillText(col + 1, x, -8)
    }
  }

  // Draw terrain features (buildings, etc.)
  const drawTerrain = (ctx) => {
    const structures = entities.filter(e => e.type === 'structure')
    for (const struct of structures) {
      const [x, y] = coordsToPixel(struct.position[0], struct.position[1])
      const color = struct.color
      const size = struct.size * 40 // Scale by entity size
      ctx.fillStyle = color
      ctx.globalAlpha = 0.6
      
      if (struct.shape === 'triangle') {
        ctx.beginPath()
        ctx.moveTo(x, y - size / 2)
        ctx.lineTo(x + size / 2, y + size / 2)
        ctx.lineTo(x - size / 2, y + size / 2)
        ctx.closePath()
        ctx.fill()
      } else if (struct.shape === 'rectangle') {
        // Rectangles are wider
        ctx.fillRect(x - size * 0.75, y - size / 2, size * 1.5, size)
        ctx.strokeStyle = '#555555'
        ctx.lineWidth = 1
        ctx.strokeRect(x - size * 0.75, y - size / 2, size * 1.5, size)
      } else {
        // Default square
        ctx.fillRect(x - size / 2, y - size / 2, size, size)
        ctx.strokeStyle = '#555555'
        ctx.lineWidth = 1
        ctx.strokeRect(x - size / 2, y - size / 2, size, size)
      }
      ctx.globalAlpha = 1.0
    }
  }

  // Draw transmission lines
  const drawTransmissionLines = (ctx) => {
    for (const edge of transmissionGraph) {
      const sourceDrone = droneMap.get(edge.source)
      const targetDrone = droneMap.get(edge.target)
      if (!sourceDrone || !targetDrone) continue
      
      // Use raw coordinates for LoS checking
      const x1 = sourceDrone.position[0]
      const y1 = sourceDrone.position[1]
      const x2 = targetDrone.position[0]
      const y2 = targetDrone.position[1]
      
      // Check line of sight with blocking entities
      if (isLineOfSightBlocked(x1, y1, x2, y2, blockingEntities)) continue
      
      // Convert to pixel coordinates for rendering
      const [px1, py1] = coordsToPixel(x1, y1)
      const [px2, py2] = coordsToPixel(x2, y2)
      
      const isSpanningTreeEdge = edge.in_spanning_tree
      const quality = edge.quality || 0.5
      ctx.strokeStyle = isSpanningTreeEdge ? '#FFD700' : '#4A4A4A'
      ctx.lineWidth = isSpanningTreeEdge ? 2 : 1
      ctx.globalAlpha = quality * 0.6
      ctx.beginPath()
      ctx.moveTo(px1, py1)
      ctx.lineTo(px2, py2)
      ctx.stroke()
      ctx.globalAlpha = 1.0
    }
  }

  // Draw drone symbols
  const drawDroneSymbol = (ctx, x, y, type, size) => {
    const symbol = DRONE_SYMBOLS[type] || 'circle'
    switch (symbol) {
      case 'square':
        ctx.fillRect(x - size / 2, y - size / 2, size, size)
        break
      case 'diamond':
        ctx.beginPath()
        ctx.moveTo(x, y - size / 2)
        ctx.lineTo(x + size / 2, y)
        ctx.lineTo(x, y + size / 2)
        ctx.lineTo(x - size / 2, y)
        ctx.closePath()
        ctx.fill()
        break
      case 'triangle':
        ctx.beginPath()
        ctx.moveTo(x, y - size / 2)
        ctx.lineTo(x + size / 2, y + size / 2)
        ctx.lineTo(x - size / 2, y + size / 2)
        ctx.closePath()
        ctx.fill()
        break
      case 'star':
        drawStar(ctx, x, y, 5, size / 2, size / 4)
        break
      default:
        ctx.beginPath()
        ctx.arc(x, y, size / 2, 0, Math.PI * 2)
        ctx.fill()
    }
  }

  // Draw star shape
  const drawStar = (ctx, cx, cy, spikes, outerRadius, innerRadius) => {
    let rot = Math.PI / 2 * 3
    let step = Math.PI / spikes
    ctx.beginPath()
    ctx.moveTo(cx, cy - outerRadius)
    for (let i = 0; i < spikes; i++) {
      ctx.lineTo(cx + Math.cos(rot) * outerRadius, cy + Math.sin(rot) * outerRadius)
      rot += step
      ctx.lineTo(cx + Math.cos(rot) * innerRadius, cy + Math.sin(rot) * innerRadius)
      rot += step
    }
    ctx.lineTo(cx, cy - outerRadius)
    ctx.closePath()
    ctx.fill()
  }

  // Draw drones
  const drawDrones = (ctx) => {
    for (const drone of drones) {
      const [x, y] = coordsToPixel(drone.position[0], drone.position[1])
      const radius = 7
      const color = drone.color || '#999999'
      ctx.fillStyle = color
      ctx.globalAlpha = 0.9
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = color
      ctx.globalAlpha = 1.0
      drawDroneSymbol(ctx, x, y, drone.droneType, radius * 1.2)
      if (drone.id === selectedDrone) {
        ctx.strokeStyle = '#FFFF00'
        ctx.lineWidth = 2
        ctx.globalAlpha = 1.0
        ctx.beginPath()
        ctx.arc(x, y, radius + 5, 0, Math.PI * 2)
        ctx.stroke()
      }
      if (drone.id === hoveredDrone) {
        ctx.strokeStyle = '#FFFFFF'
        ctx.lineWidth = 1.5
        ctx.globalAlpha = 0.7
        ctx.beginPath()
        ctx.arc(x, y, radius + 3, 0, Math.PI * 2)
        ctx.stroke()
      }
      ctx.globalAlpha = 1.0
    }
  }

  // Draw enemies
  const drawEnemies = (ctx) => {
    const enemies = entities.filter(e => e.type === 'enemy')
    for (const enemy of enemies) {
      if (enemy.status === 'destroyed') continue
      if (!revealedEnemies.has(enemy.id)) continue
      
      const [x, y] = coordsToPixel(enemy.position[0], enemy.position[1])
      const color = enemy.color
      const size = 5 * enemy.size
      ctx.fillStyle = color
      ctx.globalAlpha = 0.95
      
      if (enemy.shape === 'square') {
        ctx.fillRect(x - size / 2, y - size / 2, size, size)
      } else {
        ctx.beginPath()
        ctx.arc(x, y, size / 2, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1.0
    }
  }

  // Main render
  const render = (ctx) => {
    drawGrid(ctx)
    drawLabels(ctx)
    drawTerrain(ctx)
    drawTransmissionLines(ctx, blockingEntities)
    drawDrones(ctx)
    drawEnemies(ctx)
  }

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const animate = () => {
      render(ctx)
      animationFrameRef.current = requestAnimationFrame(animate)
    }
    animate()
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [entities, drones, transmissionGraph, hoveredDrone, selectedDrone, revealedEnemies])

  // Mouse move handler
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const pixelX = e.clientX - rect.left
    const pixelY = e.clientY - rect.top
    setMousePos({ x: pixelX, y: pixelY })
    
    // Convert pixel coordinates to entity space (1000×1000)
    const coordX = pixelX / 0.6
    const coordY = pixelY / 0.6
    
    let hoveredId = null
    for (const drone of drones) {
      const distance = drone.distanceTo([coordX, coordY])
      if (distance < 50) { // ~3 grid cells in old terms
        hoveredId = drone.id
        break
      }
    }
    setHoveredDrone(hoveredId)
  }

  // Click handler
  const handleClick = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const pixelX = e.clientX - rect.left
    const pixelY = e.clientY - rect.top
    
    // Convert pixel coordinates to entity space (1000×1000)
    const coordX = pixelX / 0.6
    const coordY = pixelY / 0.6
    
    // Check for drone clicks
    for (const drone of drones) {
      const distance = drone.distanceTo([coordX, coordY])
      if (distance < 50) { // ~3 grid cells in old terms
        onDroneClick(drone.id)
        return
      }
    }
    
    // Check for enemy clicks
    const enemies = entities.filter(e => e.type === 'enemy')
    for (const enemy of enemies) {
      if (revealedEnemies.has(enemy.id)) continue
      const distance = enemy.distanceTo([coordX, coordY])
      if (distance < 50) { // ~3 grid cells
        setRevealedEnemies(new Set([...revealedEnemies, enemy.id]))
        return
      }
    }
  }

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      onMouseMove={handleMouseMove}
      onClick={handleClick}
      style={{
        border: '2px solid #4A4A4A',
        backgroundColor: '#1A1A1A',
        cursor: hoveredDrone ? 'pointer' : 'default',
        display: 'block',
        maxWidth: '100%',
        height: 'auto'
      }}
    />
  )
}

export default SwarmCanvas
