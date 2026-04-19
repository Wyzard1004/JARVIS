/**
 * SwarmCanvas renders the 1000x1000 continuous world onto an 8x8 tactical grid.
 * The UI grid is a projection only; all entity positions and radii remain continuous.
 */

import React, { useEffect, useRef, useState } from 'react'
import { stateToEntities } from '../lib/entities'

const CELL_SIZE = 75
const GRID_SIZE = 8
const CANVAS_WIDTH = GRID_SIZE * CELL_SIZE
const CANVAS_HEIGHT = GRID_SIZE * CELL_SIZE
const WORLD_SIZE = 1000
const PIXEL_SCALE = CANVAS_WIDTH / WORLD_SIZE
const NATO_PHONETIC_SHORT = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel']

function SwarmCanvas({ state = {}, selectedDrone = null, onDroneClick = () => {} }) {
  const canvasRef = useRef(null)
  const animationFrameRef = useRef(null)
  const [hoveredDrone, setHoveredDrone] = useState(null)
  const [revealedEnemies, setRevealedEnemies] = useState(new Set())
  const [revealedSpecialEntities, setRevealedSpecialEntities] = useState(new Set())

  const entities = stateToEntities(state)
  const drones = entities.filter(entity => entity.type === 'drone')
  const enemies = entities.filter(entity => entity.type === 'enemy')
  const structures = entities.filter(entity => entity.type === 'structure')
  const specialEntities = entities.filter(entity => entity.type === 'poi')
  const reconDrones = drones.filter(drone => drone.droneType === 'recon' && drone.status !== 'destroyed' && drone.detectionRadius > 0)
  const droneMap = new Map(drones.map(drone => [drone.id, drone]))
  const transmissionGraph = (state.edges || []).map(edge => ({
    source: edge.source,
    target: edge.target,
    quality: edge.quality || 0.5,
    inSpanningTree: edge.in_spanning_tree || false
  }))
  const blockingEntities = entities.filter(entity => entity.blocksLoS && entity.status !== 'destroyed')

  const coordsToPixel = (x, y) => [x * PIXEL_SCALE, y * PIXEL_SCALE]
  const pixelToWorld = (pixel) => pixel / PIXEL_SCALE
  const getHitRadius = (entity, minimumWorldRadius = 18) => Math.max(minimumWorldRadius, pixelToWorld((entity.renderSize || 12) * 0.9))

  const mergeDetectedIds = (setter, ids) => {
    if (ids.length === 0) return
    setter((previous) => {
      let changed = false
      const next = new Set(previous)
      for (const id of ids) {
        if (!next.has(id)) {
          next.add(id)
          changed = true
        }
      }
      return changed ? next : previous
    })
  }

  useEffect(() => {
    const detectTargets = (targets) => (
      targets
        .filter((target) => target.revealed || reconDrones.some((drone) => drone.distanceTo(target) <= drone.detectionRadius))
        .map((target) => target.id)
    )

    mergeDetectedIds(setRevealedEnemies, detectTargets(enemies))
    mergeDetectedIds(setRevealedSpecialEntities, detectTargets(specialEntities))
  }, [enemies, reconDrones, specialEntities])

  const isLineOfSightBlocked = (x1, y1, x2, y2) => {
    for (const entity of blockingEntities) {
      if (entity.blocksLineOfSight(x1, y1, x2, y2)) {
        return true
      }
    }
    return false
  }

  const drawStarPath = (ctx, cx, cy, spikes, outerRadius, innerRadius) => {
    let rotation = Math.PI / 2 * 3
    const step = Math.PI / spikes

    ctx.beginPath()
    ctx.moveTo(cx, cy - outerRadius)
    for (let i = 0; i < spikes; i++) {
      ctx.lineTo(cx + Math.cos(rotation) * outerRadius, cy + Math.sin(rotation) * outerRadius)
      rotation += step
      ctx.lineTo(cx + Math.cos(rotation) * innerRadius, cy + Math.sin(rotation) * innerRadius)
      rotation += step
    }
    ctx.closePath()
  }

  const drawEntityShape = (ctx, x, y, shape, size, options = {}) => {
    const {
      fillStyle,
      strokeStyle = null,
      lineWidth = 1,
      opacity = 1
    } = options
    const normalizedShape = shape || 'circle'
    const half = size / 2

    ctx.save()
    ctx.globalAlpha = opacity

    if (normalizedShape === 'square') {
      if (fillStyle) {
        ctx.fillStyle = fillStyle
        ctx.fillRect(x - half, y - half, size, size)
      }
      if (strokeStyle) {
        ctx.strokeStyle = strokeStyle
        ctx.lineWidth = lineWidth
        ctx.strokeRect(x - half, y - half, size, size)
      }
      ctx.restore()
      return
    }

    if (normalizedShape === 'rectangle') {
      const width = size * 1.45
      const height = size * 0.9
      if (fillStyle) {
        ctx.fillStyle = fillStyle
        ctx.fillRect(x - width / 2, y - height / 2, width, height)
      }
      if (strokeStyle) {
        ctx.strokeStyle = strokeStyle
        ctx.lineWidth = lineWidth
        ctx.strokeRect(x - width / 2, y - height / 2, width, height)
      }
      ctx.restore()
      return
    }

    if (normalizedShape === 'diamond') {
      ctx.beginPath()
      ctx.moveTo(x, y - half)
      ctx.lineTo(x + half, y)
      ctx.lineTo(x, y + half)
      ctx.lineTo(x - half, y)
      ctx.closePath()
    } else if (normalizedShape === 'triangle') {
      ctx.beginPath()
      ctx.moveTo(x, y - half)
      ctx.lineTo(x + half, y + half)
      ctx.lineTo(x - half, y + half)
      ctx.closePath()
    } else if (normalizedShape === 'star') {
      drawStarPath(ctx, x, y, 5, half, half * 0.45)
    } else {
      ctx.beginPath()
      ctx.arc(x, y, half, 0, Math.PI * 2)
      ctx.closePath()
    }

    if (fillStyle) {
      ctx.fillStyle = fillStyle
      ctx.fill()
    }
    if (strokeStyle) {
      ctx.strokeStyle = strokeStyle
      ctx.lineWidth = lineWidth
      ctx.stroke()
    }
    ctx.restore()
  }

  const drawGrid = (ctx) => {
    ctx.fillStyle = '#1A1A1A'
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    ctx.strokeStyle = '#333333'
    ctx.lineWidth = 1

    for (let col = 0; col <= GRID_SIZE; col += 1) {
      const x = col * CELL_SIZE
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, CANVAS_HEIGHT)
      ctx.stroke()
    }

    for (let row = 0; row <= GRID_SIZE; row += 1) {
      const y = row * CELL_SIZE
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(CANVAS_WIDTH, y)
      ctx.stroke()
    }
  }

  const drawLabels = (ctx) => {
    ctx.font = 'bold 12px monospace'
    ctx.fillStyle = '#666666'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    for (let row = 0; row < GRID_SIZE; row += 1) {
      const y = row * CELL_SIZE + CELL_SIZE / 2
      const label = NATO_PHONETIC_SHORT[row].substring(0, 3)
      ctx.save()
      ctx.translate(-18, y)
      ctx.rotate(-Math.PI / 2)
      ctx.fillText(label, 0, 0)
      ctx.restore()
    }

    for (let col = 0; col < GRID_SIZE; col += 1) {
      const x = col * CELL_SIZE + CELL_SIZE / 2
      ctx.fillText(col + 1, x, -8)
    }
  }

  const drawTerrain = (ctx) => {
    for (const structure of structures) {
      const [x, y] = coordsToPixel(structure.position[0], structure.position[1])
      drawEntityShape(ctx, x, y, structure.shape, structure.renderSize || 18, {
        fillStyle: structure.color,
        strokeStyle: '#555555',
        lineWidth: 1,
        opacity: structure.opacity ?? 0.75
      })
    }
  }

  const drawTransmissionLines = (ctx) => {
    for (const edge of transmissionGraph) {
      const sourceDrone = droneMap.get(edge.source)
      const targetDrone = droneMap.get(edge.target)
      if (!sourceDrone || !targetDrone) continue

      const x1 = sourceDrone.position[0]
      const y1 = sourceDrone.position[1]
      const x2 = targetDrone.position[0]
      const y2 = targetDrone.position[1]
      if (isLineOfSightBlocked(x1, y1, x2, y2)) continue

      const [px1, py1] = coordsToPixel(x1, y1)
      const [px2, py2] = coordsToPixel(x2, y2)
      const quality = edge.quality || 0.5

      ctx.save()
      ctx.strokeStyle = edge.inSpanningTree ? '#FFD700' : '#4A4A4A'
      ctx.lineWidth = edge.inSpanningTree ? 2 : 1
      ctx.globalAlpha = quality * 0.6
      ctx.beginPath()
      ctx.moveTo(px1, py1)
      ctx.lineTo(px2, py2)
      ctx.stroke()
      ctx.restore()
    }
  }

  const drawReconDetectionRings = (ctx) => {
    for (const drone of reconDrones) {
      const [x, y] = coordsToPixel(drone.position[0], drone.position[1])
      const detectionRadius = drone.detectionRadius * PIXEL_SCALE

      ctx.save()
      ctx.setLineDash([6, 6])
      ctx.strokeStyle = '#7DD3FC'
      ctx.fillStyle = '#7DD3FC'
      ctx.lineWidth = 1.5
      ctx.globalAlpha = 0.12
      ctx.beginPath()
      ctx.arc(x, y, detectionRadius, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 0.45
      ctx.stroke()
      ctx.restore()
    }
  }

  const drawDrones = (ctx) => {
    for (const drone of drones) {
      const [x, y] = coordsToPixel(drone.position[0], drone.position[1])
      const size = drone.renderSize || 14

      drawEntityShape(ctx, x, y, drone.shape, size, {
        fillStyle: drone.color || '#999999',
        opacity: drone.opacity ?? 0.95
      })

      if (drone.id === selectedDrone) {
        ctx.save()
        ctx.strokeStyle = '#FDE047'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(x, y, size / 2 + 7, 0, Math.PI * 2)
        ctx.stroke()
        ctx.restore()
      }

      if (drone.id === hoveredDrone) {
        ctx.save()
        ctx.strokeStyle = '#FFFFFF'
        ctx.lineWidth = 1.5
        ctx.globalAlpha = 0.75
        ctx.beginPath()
        ctx.arc(x, y, size / 2 + 4, 0, Math.PI * 2)
        ctx.stroke()
        ctx.restore()
      }
    }
  }

  const drawEnemies = (ctx) => {
    for (const enemy of enemies) {
      if (enemy.status === 'destroyed') continue
      if (!enemy.revealed && !revealedEnemies.has(enemy.id)) continue

      const [x, y] = coordsToPixel(enemy.position[0], enemy.position[1])
      drawEntityShape(ctx, x, y, enemy.shape, enemy.renderSize || 12, {
        fillStyle: enemy.color,
        opacity: enemy.opacity ?? 0.95
      })
    }
  }

  const drawSpecialEntities = (ctx) => {
    for (const entity of specialEntities) {
      if (entity.status === 'destroyed') continue
      if (!entity.revealed && !revealedSpecialEntities.has(entity.id)) continue

      const [x, y] = coordsToPixel(entity.position[0], entity.position[1])
      drawEntityShape(ctx, x, y, entity.shape, entity.renderSize || 14, {
        fillStyle: entity.color,
        strokeStyle: '#FDE68A',
        lineWidth: 1,
        opacity: entity.opacity ?? 0.95
      })
    }
  }

  const render = (ctx) => {
    drawGrid(ctx)
    drawLabels(ctx)
    drawTerrain(ctx)
    drawTransmissionLines(ctx)
    drawReconDetectionRings(ctx)
    drawSpecialEntities(ctx)
    drawEnemies(ctx)
    drawDrones(ctx)
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined
    const ctx = canvas.getContext('2d')
    if (!ctx) return undefined

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
  }, [enemies, hoveredDrone, reconDrones, revealedEnemies, revealedSpecialEntities, selectedDrone, specialEntities, structures, transmissionGraph, drones])

  const handleMouseMove = (event) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const coordX = pixelToWorld(event.clientX - rect.left)
    const coordY = pixelToWorld(event.clientY - rect.top)

    const hovered = drones.find((drone) => drone.distanceTo([coordX, coordY]) <= getHitRadius(drone))
    setHoveredDrone(hovered?.id || null)
  }

  const handleClick = (event) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const coordX = pixelToWorld(event.clientX - rect.left)
    const coordY = pixelToWorld(event.clientY - rect.top)

    const clickedDrone = drones.find((drone) => drone.distanceTo([coordX, coordY]) <= getHitRadius(drone))
    if (clickedDrone) {
      onDroneClick(clickedDrone.id)
      return
    }

    const hiddenEnemy = enemies.find((enemy) => !revealedEnemies.has(enemy.id) && enemy.distanceTo([coordX, coordY]) <= getHitRadius(enemy))
    if (hiddenEnemy) {
      setRevealedEnemies((current) => new Set([...current, hiddenEnemy.id]))
      return
    }

    const hiddenSpecialEntity = specialEntities.find((entity) => !revealedSpecialEntities.has(entity.id) && entity.distanceTo([coordX, coordY]) <= getHitRadius(entity))
    if (hiddenSpecialEntity) {
      setRevealedSpecialEntities((current) => new Set([...current, hiddenSpecialEntity.id]))
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
