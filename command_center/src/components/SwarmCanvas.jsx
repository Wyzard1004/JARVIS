/**
 * SwarmCanvas renders the 1000x1000 continuous world onto an 8x8 tactical grid.
 * The UI grid is a projection only; all entity positions and footprints remain continuous.
 */

import React, { useEffect, useRef, useState } from 'react'
import { stateToEntities } from '../lib/entities'
import { getEntityDisplayLabel } from '../lib/displayNames'
import {
  computeVisibilityPolygon,
  createRectFootprint,
  doesAnyFootprintBlockSegment,
  getFootprintCenter,
  getStructureFootprint,
  normalizeRectFootprint,
  pointInRect,
  footprintToCanvasRect,
  translateFootprintToCenter
} from '../lib/mapGeometry'

const CELL_SIZE = 75
const GRID_SIZE = 8
const CANVAS_WIDTH = GRID_SIZE * CELL_SIZE
const CANVAS_HEIGHT = GRID_SIZE * CELL_SIZE
const WORLD_SIZE = 1000
const PIXEL_SCALE = CANVAS_WIDTH / WORLD_SIZE
const NATO_PHONETIC_SHORT = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel']
const DEFAULT_SYMBOL_ASPECT_RATIO = 612 / 792
const LABEL_MAX_TEXT_WIDTH = 108
const CANVAS_MARGIN = 6
const imageCache = new Map()

const getCachedImage = (url) => {
  if (!url || typeof Image === 'undefined') return null
  if (imageCache.has(url)) return imageCache.get(url)

  const image = new Image()
  image.decoding = 'async'
  image.src = url
  imageCache.set(url, image)
  return image
}

const getOverlayCacheKey = (overlay) => overlay?.asset_url || null

function SwarmCanvas({
  state = {},
  selectedDrone = null,
  selectedMapEntity = null,
  mapMode = 'nato',
  showEntityLabels = true,
  editMode = false,
  editorTool = 'select',
  onDroneClick = () => {},
  onMapEntitySelect = () => {},
  onMapEntityCreate = () => {},
  onMapEntityMove = () => {},
  onDroneMove = () => {}
}) {
  const canvasRef = useRef(null)
  const animationFrameRef = useRef(null)
  const pointerStateRef = useRef(null)
  const [hoveredDrone, setHoveredDrone] = useState(null)
  const [hoveredMapEntity, setHoveredMapEntity] = useState(null)
  const [revealedEnemies, setRevealedEnemies] = useState(new Set())
  const [revealedSpecialEntities, setRevealedSpecialEntities] = useState(new Set())
  const [dragPreview, setDragPreview] = useState(null)
  const [activeDrag, setActiveDrag] = useState(null)

  const entities = stateToEntities(state)
  const drones = entities.filter((entity) => entity.type === 'drone')
  const enemies = entities.filter((entity) => entity.type === 'enemy')
  const structures = entities.filter((entity) => entity.type === 'structure')
  const specialEntities = entities.filter((entity) => entity.type === 'poi')
  const mapOverlay = state.map_overlay || {}
  const overlayKey = getOverlayCacheKey(mapOverlay)
  const reconDrones = drones.filter((drone) => drone.droneType === 'recon' && drone.status !== 'destroyed' && drone.detectionRadius > 0)
  const droneMap = new Map(drones.map((drone) => [drone.id, drone]))
  const transmissionGraph = (state.edges || []).map((edge) => ({
    source: edge.source,
    target: edge.target,
    quality: edge.quality || 0.5,
    inSpanningTree: edge.in_spanning_tree || false
  }))

  const blockingFootprints = structures
    .filter((entity) => entity.blocksLoS && entity.status !== 'destroyed')
    .map((entity) => ({
      id: entity.id,
      footprint: getStructureFootprint(entity)
    }))
    .filter((entry) => entry.footprint)

  const reconVisibilityPolygons = reconDrones.map((drone) => ({
    droneId: drone.id,
    points: computeVisibilityPolygon(drone.position, drone.detectionRadius, blockingFootprints, 256)
  }))

  const pointToolActive = editMode && editorTool !== 'select' && editorTool !== 'building'

  const coordsToPixel = (x, y) => [x * PIXEL_SCALE, y * PIXEL_SCALE]
  const pixelToWorld = (pixel) => pixel / PIXEL_SCALE

  const getHitRadius = (entity, minimumWorldRadius = 18) => {
    const symbolMultiplier = entity.symbolScale ? entity.symbolScale * 0.5 : 0.9
    const atakMultiplier = mapMode === 'atak' ? 1.35 : 1
    return Math.max(
      minimumWorldRadius,
      pixelToWorld((entity.renderSize || 12) * Math.max(0.9, symbolMultiplier) * atakMultiplier)
    )
  }

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
    const canDroneSeeTarget = (drone, target) => (
      drone.distanceTo(target) <= drone.detectionRadius &&
      !doesAnyFootprintBlockSegment(drone.position, target.position, blockingFootprints)
    )

    const detectTargets = (targets) => (
      targets
        .filter((target) => target.revealed || reconDrones.some((drone) => canDroneSeeTarget(drone, target)))
        .map((target) => target.id)
    )

    mergeDetectedIds(setRevealedEnemies, detectTargets(enemies))
    mergeDetectedIds(setRevealedSpecialEntities, detectTargets(specialEntities))
  }, [blockingFootprints, enemies, reconDrones, specialEntities])

  const isLineOfSightBlocked = (x1, y1, x2, y2) => (
    doesAnyFootprintBlockSegment([x1, y1], [x2, y2], blockingFootprints)
  )

  const drawRoundedRectPath = (ctx, x, y, width, height, radius) => {
    const safeRadius = Math.min(radius, width / 2, height / 2)
    ctx.beginPath()
    ctx.moveTo(x + safeRadius, y)
    ctx.lineTo(x + width - safeRadius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + safeRadius)
    ctx.lineTo(x + width, y + height - safeRadius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height)
    ctx.lineTo(x + safeRadius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - safeRadius)
    ctx.lineTo(x, y + safeRadius)
    ctx.quadraticCurveTo(x, y, x + safeRadius, y)
    ctx.closePath()
  }

  const truncateText = (ctx, text, maxWidth) => {
    if (!text) return ''
    if (ctx.measureText(text).width <= maxWidth) return text

    let truncated = text
    while (truncated.length > 1 && ctx.measureText(`${truncated}...`).width > maxWidth) {
      truncated = truncated.slice(0, -1)
    }
    return `${truncated}...`
  }

  const getEntityLabelLines = (entity) => {
    return [getEntityDisplayLabel(entity)]
  }

  const shouldRenderEntityLabel = (entity) => {
    if (!entity) return false
    if (entity.type === 'structure' && entity.structureType === 'building') {
      return false
    }
    return true
  }

  const drawStarPath = (ctx, cx, cy, spikes, outerRadius, innerRadius) => {
    let rotation = Math.PI / 2 * 3
    const step = Math.PI / spikes

    ctx.beginPath()
    ctx.moveTo(cx, cy - outerRadius)
    for (let index = 0; index < spikes; index += 1) {
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

  const getImageAspectRatio = (image) => (
    image?.naturalWidth > 0 && image?.naturalHeight > 0
      ? image.naturalWidth / image.naturalHeight
      : DEFAULT_SYMBOL_ASPECT_RATIO
  )

  const getEntityMarkerUrl = (entity) => (
    mapMode === 'atak'
      ? entity.atakSymbolUrl || entity.symbolUrl
      : entity.symbolUrl
  )

  const drawNatoMarker = (ctx, entity, x, y, fallbackOptions = {}) => {
    const markerUrl = getEntityMarkerUrl(entity)
    if (markerUrl) {
      const image = getCachedImage(markerUrl)
      if (image?.complete && image.naturalWidth > 0) {
        const imageHeight = (entity.renderSize || 12) * (entity.symbolScale || 3.3)
        const metrics = {
          width: imageHeight * getImageAspectRatio(image),
          height: imageHeight,
          radius: Math.max((entity.renderSize || 12) / 2, imageHeight * 0.26),
          mode: 'nato'
        }
        ctx.save()
        ctx.globalAlpha = entity.opacity ?? fallbackOptions.opacity ?? 1
        ctx.drawImage(
          image,
          x - metrics.width / 2,
          y - metrics.height / 2,
          metrics.width,
          metrics.height
        )
        ctx.restore()
        return metrics
      }
    }

    const fallbackSize = entity.renderSize || 12
    drawEntityShape(ctx, x, y, entity.shape, fallbackSize, fallbackOptions)
    return {
      width: fallbackSize,
      height: fallbackSize,
      radius: fallbackSize / 2,
      mode: 'nato'
    }
  }

  const drawAtakMarker = (ctx, entity, x, y, fallbackOptions = {}) => {
    const markerSize = entity.renderSize || 12
    const radius = Math.max(12, Math.min(20, markerSize * 0.95))
    const badgeColor = entity.color || fallbackOptions.fillStyle || '#94A3B8'
    const markerOpacity = entity.opacity ?? fallbackOptions.opacity ?? 1

    if (entity.atakBadge !== false) {
      ctx.save()
      ctx.fillStyle = badgeColor
      ctx.globalAlpha = markerOpacity * 0.24
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()

      ctx.save()
      ctx.strokeStyle = badgeColor
      ctx.lineWidth = 1.5
      ctx.globalAlpha = markerOpacity * 0.92
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.stroke()
      ctx.restore()
    }

    const markerUrl = getEntityMarkerUrl(entity)
    if (markerUrl) {
      const image = getCachedImage(markerUrl)
      if (image?.complete && image.naturalWidth > 0) {
        const innerHeight = radius * 2.15
        const innerWidth = innerHeight * getImageAspectRatio(image)

        ctx.save()
        ctx.beginPath()
        ctx.arc(x, y, radius - 1.2, 0, Math.PI * 2)
        ctx.clip()
        ctx.globalAlpha = markerOpacity
        ctx.drawImage(
          image,
          x - innerWidth / 2,
          y - innerHeight / 2,
          innerWidth,
          innerHeight
        )
        ctx.restore()
      }
    } else {
      drawEntityShape(ctx, x, y, entity.shape, radius * 0.95, {
        fillStyle: '#F8FAFC',
        strokeStyle: 'rgba(15, 23, 42, 0.65)',
        lineWidth: 1.1,
        opacity: Math.min(1, markerOpacity)
      })
    }

    return {
      width: radius * 2,
      height: radius * 2,
      radius,
      mode: 'atak'
    }
  }

  const drawEntityMarker = (ctx, entity, x, y, fallbackOptions = {}) => (
    mapMode === 'atak'
      ? drawAtakMarker(ctx, entity, x, y, fallbackOptions)
      : drawNatoMarker(ctx, entity, x, y, fallbackOptions)
  )

  const drawEntityHalo = (ctx, x, y, markerMeta, { selected = false, hovered = false } = {}) => {
    if (!selected && !hovered) return

    if (selected) {
      ctx.save()
      ctx.strokeStyle = '#FDE047'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(x, y, markerMeta.radius + 7, 0, Math.PI * 2)
      ctx.stroke()
      ctx.restore()
    }

    if (hovered) {
      ctx.save()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 1.5
      ctx.globalAlpha = 0.75
      ctx.beginPath()
      ctx.arc(x, y, markerMeta.radius + 4, 0, Math.PI * 2)
      ctx.stroke()
      ctx.restore()
    }
  }

  const queueLabel = (labelEntries, entity, x, y, markerMeta, options = {}) => {
    if (!shouldRenderEntityLabel(entity)) return

    labelEntries.push({
      entity,
      x,
      y,
      markerMeta,
      selected: options.selected || false,
      hovered: options.hovered || false
    })
  }

  const drawEntityLabel = (ctx, { entity, x, y, markerMeta, selected = false, hovered = false }) => {
    if (!showEntityLabels) return
    if (!shouldRenderEntityLabel(entity)) return

    const lines = getEntityLabelLines(entity)
    if (lines.length === 0) return

    const boxPaddingX = 6
    const lineGap = 2
    const cornerRadius = 6

    ctx.save()
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'

    ctx.font = 'bold 9px monospace'
    const primary = truncateText(ctx, lines[0], LABEL_MAX_TEXT_WIDTH)
    const primaryWidth = ctx.measureText(primary).width

    let secondary = ''
    let secondaryWidth = 0
    if (lines[1]) {
      ctx.font = '9px sans-serif'
      secondary = truncateText(ctx, lines[1], LABEL_MAX_TEXT_WIDTH)
      secondaryWidth = ctx.measureText(secondary).width
    }

    const boxWidth = Math.max(primaryWidth, secondaryWidth) + boxPaddingX * 2
    const boxHeight = secondary ? 25 : 16
    const visualHalfHeight = markerMeta.mode === 'atak'
      ? markerMeta.radius
      : Math.max(markerMeta.radius, markerMeta.height * 0.42)
    let boxX = x - boxWidth / 2
    boxX = Math.max(CANVAS_MARGIN, Math.min(CANVAS_WIDTH - boxWidth - CANVAS_MARGIN, boxX))

    let boxY = y + visualHalfHeight + 8
    if (boxY + boxHeight > CANVAS_HEIGHT - CANVAS_MARGIN) {
      boxY = y - visualHalfHeight - boxHeight - 8
    }
    boxY = Math.max(CANVAS_MARGIN, Math.min(CANVAS_HEIGHT - boxHeight - CANVAS_MARGIN, boxY))

    ctx.fillStyle = selected ? 'rgba(15, 23, 42, 0.78)' : 'rgba(15, 23, 42, 0.48)'
    ctx.strokeStyle = selected
      ? 'rgba(253, 224, 71, 0.8)'
      : hovered
        ? 'rgba(255, 255, 255, 0.34)'
        : 'rgba(148, 163, 184, 0.16)'
    ctx.lineWidth = selected ? 1 : 0.8
    drawRoundedRectPath(ctx, boxX, boxY, boxWidth, boxHeight, cornerRadius)
    ctx.fill()
    ctx.stroke()

    ctx.font = 'bold 9px monospace'
    ctx.fillStyle = '#F8FAFC'
    ctx.fillText(primary, boxX + boxWidth / 2, boxY + 4)

    if (secondary) {
      ctx.font = '9px sans-serif'
      ctx.fillStyle = '#CBD5E1'
      ctx.fillText(secondary, boxX + boxWidth / 2, boxY + 4 + 9 + lineGap)
    }

    ctx.restore()
  }

  const drawDeferredLabels = (ctx, labelEntries) => {
    if (!showEntityLabels) return

    const priorityFor = (entry) => {
      if (entry.selected) return 3
      if (entry.hovered) return 2
      if (entry.entity.type === 'drone') return 1
      return 0
    }

    const sortedEntries = [...labelEntries].sort((left, right) => priorityFor(left) - priorityFor(right))
    for (const entry of sortedEntries) {
      drawEntityLabel(ctx, entry)
    }
  }

  const drawGridBase = (ctx) => {
    ctx.fillStyle = '#1A1A1A'
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
  }

  const drawMapOverlay = (ctx) => {
    if (!mapOverlay?.visible || !overlayKey) return
    const image = getCachedImage(overlayKey)
    if (!image?.complete || image.naturalWidth <= 0) return

    ctx.save()
    ctx.globalAlpha = Math.max(0, Math.min(1, mapOverlay.opacity ?? 0.72))
    ctx.drawImage(image, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    ctx.restore()
  }

  const drawGrid = (ctx) => {
    ctx.strokeStyle = 'rgba(51, 51, 51, 0.85)'
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

  const drawGridLabels = (ctx) => {
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

  const drawStructures = (ctx, labelEntries) => {
    for (const structure of structures) {
      if (structure.status === 'destroyed') continue

      const activeStructure = activeDrag?.type === 'move' && activeDrag.kind === 'structures' && activeDrag.id === structure.id
        ? { ...structure, footprint: activeDrag.previewFootprint, position: activeDrag.previewPosition }
        : structure
      const rect = footprintToCanvasRect(activeStructure.footprint, CANVAS_WIDTH)
      if (!rect) continue

      const selected = selectedMapEntity?.kind === 'structures' && selectedMapEntity?.id === structure.id
      const hovered = hoveredMapEntity?.kind === 'structures' && hoveredMapEntity?.id === structure.id

      ctx.save()
      ctx.globalAlpha = activeStructure.opacity ?? 0.5
      ctx.fillStyle = activeStructure.color || '#8B7355'
      ctx.fillRect(rect.x, rect.y, rect.width, rect.height)
      ctx.restore()

      ctx.save()
      ctx.strokeStyle = selected
        ? '#FDE047'
        : hovered
          ? 'rgba(255, 255, 255, 0.85)'
          : 'rgba(85, 85, 85, 0.95)'
      ctx.lineWidth = selected ? 2 : 1
      ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)
      ctx.restore()

      if (editMode && selected) {
        ctx.save()
        ctx.setLineDash([8, 6])
        ctx.strokeStyle = 'rgba(253, 224, 71, 0.85)'
        ctx.lineWidth = 1.2
        ctx.strokeRect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6)
        ctx.restore()
      }

      queueLabel(
        labelEntries,
        activeStructure,
        rect.x + rect.width / 2,
        rect.y + rect.height / 2,
        {
          width: rect.width,
          height: rect.height,
          radius: Math.max(rect.width, rect.height) / 2,
          mode: 'nato'
        },
        { selected, hovered }
      )
    }

    if (dragPreview) {
      const rect = footprintToCanvasRect(dragPreview.footprint, CANVAS_WIDTH)
      if (rect) {
        ctx.save()
        ctx.fillStyle = 'rgba(251, 191, 36, 0.18)'
        ctx.strokeStyle = 'rgba(251, 191, 36, 0.9)'
        ctx.setLineDash([8, 6])
        ctx.lineWidth = 1.5
        ctx.fillRect(rect.x, rect.y, rect.width, rect.height)
        ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)
        ctx.restore()
      }
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

  const drawReconVisibility = (ctx) => {
    for (const polygon of reconVisibilityPolygons) {
      if (!polygon.points.length) continue
      const [startX, startY] = coordsToPixel(polygon.points[0][0], polygon.points[0][1])

      ctx.save()
      ctx.beginPath()
      ctx.moveTo(startX, startY)
      for (let index = 1; index < polygon.points.length; index += 1) {
        const [px, py] = coordsToPixel(polygon.points[index][0], polygon.points[index][1])
        ctx.lineTo(px, py)
      }
      ctx.closePath()
      ctx.fillStyle = 'rgba(125, 211, 252, 0.12)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(125, 211, 252, 0.45)'
      ctx.lineWidth = 1
      ctx.setLineDash([6, 6])
      ctx.stroke()
      ctx.restore()
    }
  }

  const shouldRenderEnemy = (enemy) => editMode || enemy.revealed || revealedEnemies.has(enemy.id)
  const shouldRenderSpecialEntity = (entity) => editMode || entity.revealed || revealedSpecialEntities.has(entity.id)

  const drawEnemies = (ctx, labelEntries) => {
    for (const enemy of enemies) {
      if (enemy.status === 'destroyed') continue
      if (!shouldRenderEnemy(enemy)) continue

      const activeEnemy = activeDrag?.type === 'move' && activeDrag.kind === 'enemies' && activeDrag.id === enemy.id
        ? { ...enemy, position: activeDrag.previewPosition }
        : enemy
      const [x, y] = coordsToPixel(activeEnemy.position[0], activeEnemy.position[1])
      const selected = selectedMapEntity?.kind === 'enemies' && selectedMapEntity?.id === enemy.id
      const hovered = hoveredMapEntity?.kind === 'enemies' && hoveredMapEntity?.id === enemy.id
      const markerMeta = drawEntityMarker(ctx, activeEnemy, x, y, {
        fillStyle: activeEnemy.color,
        opacity: activeEnemy.opacity ?? 0.95
      })
      drawEntityHalo(ctx, x, y, markerMeta, { selected, hovered })
      queueLabel(labelEntries, activeEnemy, x, y, markerMeta, { selected, hovered })
    }
  }

  const drawSpecialEntities = (ctx, labelEntries) => {
    for (const entity of specialEntities) {
      if (entity.status === 'destroyed') continue
      if (!shouldRenderSpecialEntity(entity)) continue

      const activeEntity = activeDrag?.type === 'move' && activeDrag.kind === 'special_entities' && activeDrag.id === entity.id
        ? { ...entity, position: activeDrag.previewPosition }
        : entity
      const [x, y] = coordsToPixel(activeEntity.position[0], activeEntity.position[1])
      const selected = selectedMapEntity?.kind === 'special_entities' && selectedMapEntity?.id === entity.id
      const hovered = hoveredMapEntity?.kind === 'special_entities' && hoveredMapEntity?.id === entity.id
      const markerMeta = drawEntityMarker(ctx, activeEntity, x, y, {
        fillStyle: activeEntity.color,
        strokeStyle: '#FDE68A',
        lineWidth: 1,
        opacity: activeEntity.opacity ?? 0.95
      })
      drawEntityHalo(ctx, x, y, markerMeta, { selected, hovered })
      queueLabel(labelEntries, activeEntity, x, y, markerMeta, { selected, hovered })
    }
  }

  const drawDrones = (ctx, labelEntries) => {
    for (const drone of drones) {
      const activeDrone = activeDrag?.type === 'move' && activeDrag.kind === 'drones' && activeDrag.id === drone.id
        ? { ...drone, position: activeDrag.previewPosition }
        : drone
      const [x, y] = coordsToPixel(activeDrone.position[0], activeDrone.position[1])
      const markerMeta = drawEntityMarker(ctx, activeDrone, x, y, {
        fillStyle: activeDrone.color || '#999999',
        opacity: activeDrone.opacity ?? 0.95
      })
      const selected = drone.id === selectedDrone
      const hovered = drone.id === hoveredDrone

      drawEntityHalo(ctx, x, y, markerMeta, { selected, hovered })
      queueLabel(labelEntries, activeDrone, x, y, markerMeta, { selected, hovered })
    }
  }

  const render = (ctx) => {
    const labelEntries = []

    drawGridBase(ctx)
    drawMapOverlay(ctx)
    drawGrid(ctx)
    drawGridLabels(ctx)
    drawStructures(ctx, labelEntries)
    drawReconVisibility(ctx)
    drawTransmissionLines(ctx)
    drawSpecialEntities(ctx, labelEntries)
    drawEnemies(ctx, labelEntries)
    drawDrones(ctx, labelEntries)
    drawDeferredLabels(ctx, labelEntries)
  }

  useEffect(() => {
    const preloadUrls = [
      overlayKey,
      ...drones.map((entity) => entity.symbolUrl),
      ...drones.map((entity) => entity.atakSymbolUrl),
      ...enemies.map((entity) => entity.symbolUrl),
      ...enemies.map((entity) => entity.atakSymbolUrl),
      ...specialEntities.map((entity) => entity.symbolUrl),
      ...specialEntities.map((entity) => entity.atakSymbolUrl)
    ].filter(Boolean)

    for (const url of new Set(preloadUrls)) {
      getCachedImage(url)
    }
  }, [drones, enemies, overlayKey, specialEntities])

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
  }, [
    activeDrag,
    dragPreview,
    drones,
    editMode,
    enemies,
    hoveredDrone,
    hoveredMapEntity,
    mapMode,
    mapOverlay,
    reconVisibilityPolygons,
    revealedEnemies,
    revealedSpecialEntities,
    selectedDrone,
    selectedMapEntity,
    showEntityLabels,
    specialEntities,
    structures,
    transmissionGraph
  ])

  const getWorldPointFromEvent = (event) => {
    const canvas = canvasRef.current
    if (!canvas) return [WORLD_SIZE / 2, WORLD_SIZE / 2]
    const rect = canvas.getBoundingClientRect()
    const localX = ((event.clientX - rect.left) / rect.width) * CANVAS_WIDTH
    const localY = ((event.clientY - rect.top) / rect.height) * CANVAS_HEIGHT
    return [pixelToWorld(localX), pixelToWorld(localY)]
  }

  const getStructureHit = (worldPoint) => {
    for (let index = structures.length - 1; index >= 0; index -= 1) {
      const structure = structures[index]
      const footprint = getStructureFootprint(structure)
      if (footprint && pointInRect(worldPoint, footprint)) {
        return { kind: 'structures', entity: structure, footprint }
      }
    }
    return null
  }

  const getPointEntityHit = (worldPoint) => {
    const pointEntityGroups = [
      ...specialEntities.filter((entity) => editMode || shouldRenderSpecialEntity(entity)).map((entity) => ({ kind: 'special_entities', entity })),
      ...enemies.filter((entity) => editMode || shouldRenderEnemy(entity)).map((entity) => ({ kind: 'enemies', entity }))
    ]

    for (let index = pointEntityGroups.length - 1; index >= 0; index -= 1) {
      const { kind, entity } = pointEntityGroups[index]
      if (entity.distanceTo(worldPoint) <= getHitRadius(entity)) {
        return { kind, entity }
      }
    }
    return null
  }

  const getMapEntityHit = (worldPoint) => getPointEntityHit(worldPoint) || getStructureHit(worldPoint)

  const getDroneHit = (worldPoint) => (
    drones.find((drone) => drone.distanceTo(worldPoint) <= getHitRadius(drone)) || null
  )

  const beginMoveDrag = (selection, entity, worldPoint, footprint = null) => {
    if (selection.kind === 'structures') {
      const center = getFootprintCenter(footprint)
      if (!center) return
      setActiveDrag({
        type: 'move',
        kind: selection.kind,
        id: entity.id,
        offset: [center[0] - worldPoint[0], center[1] - worldPoint[1]],
        previewPosition: center,
        previewFootprint: footprint,
        moved: false
      })
      return
    }

    setActiveDrag({
      type: 'move',
      kind: selection.kind,
      id: entity.id,
      offset: [entity.position[0] - worldPoint[0], entity.position[1] - worldPoint[1]],
      previewPosition: entity.position,
      previewFootprint: null,
      moved: false
    })
  }

  const handlePointerDown = (event) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const worldPoint = getWorldPointFromEvent(event)
    pointerStateRef.current = {
      pointerId: event.pointerId,
      startPoint: worldPoint
    }

    if (editMode && editorTool === 'building') {
      canvas.setPointerCapture(event.pointerId)
      const footprint = createRectFootprint(worldPoint, worldPoint)
      setDragPreview({ startPoint: worldPoint, currentPoint: worldPoint, footprint })
      return
    }

    if (editMode && editorTool === 'select') {
      const mapHit = getMapEntityHit(worldPoint)
      if (mapHit) {
        onMapEntitySelect({ kind: mapHit.kind, id: mapHit.entity.id })
        onDroneClick(null)
        canvas.setPointerCapture(event.pointerId)
        beginMoveDrag({ kind: mapHit.kind }, mapHit.entity, worldPoint, mapHit.footprint)
        return
      }

      const droneHit = getDroneHit(worldPoint)
      if (droneHit) {
        onMapEntitySelect(null)
        onDroneClick(droneHit.id)
        canvas.setPointerCapture(event.pointerId)
        beginMoveDrag({ kind: 'drones' }, droneHit, worldPoint)
        return
      }

      onMapEntitySelect(null)
      onDroneClick(null)
    }
  }

  const handlePointerMove = (event) => {
    const worldPoint = getWorldPointFromEvent(event)

    if (dragPreview) {
      setDragPreview({
        startPoint: dragPreview.startPoint,
        currentPoint: worldPoint,
        footprint: createRectFootprint(dragPreview.startPoint, worldPoint)
      })
      return
    }

    if (activeDrag?.type === 'move') {
      if (activeDrag.kind === 'structures') {
        const nextCenter = [
          worldPoint[0] + activeDrag.offset[0],
          worldPoint[1] + activeDrag.offset[1]
        ]
        const nextFootprint = translateFootprintToCenter(activeDrag.previewFootprint, nextCenter)
        setActiveDrag({
          ...activeDrag,
          previewFootprint: nextFootprint,
          previewPosition: getFootprintCenter(nextFootprint),
          moved: true
        })
      } else {
        setActiveDrag({
          ...activeDrag,
          previewPosition: [
            worldPoint[0] + activeDrag.offset[0],
            worldPoint[1] + activeDrag.offset[1]
          ],
          moved: true
        })
      }
      return
    }

    const mapHit = getMapEntityHit(worldPoint)
    const droneHit = getDroneHit(worldPoint)

    setHoveredMapEntity(mapHit ? { kind: mapHit.kind, id: mapHit.entity.id } : null)
    setHoveredDrone(droneHit?.id || null)
  }

  const finishBuildingDrag = async () => {
    if (!dragPreview?.footprint) return
    const rawWidth = Math.abs((dragPreview.currentPoint?.[0] || 0) - (dragPreview.startPoint?.[0] || 0))
    const rawHeight = Math.abs((dragPreview.currentPoint?.[1] || 0) - (dragPreview.startPoint?.[1] || 0))
    if (rawWidth < 4 && rawHeight < 4) {
      setDragPreview(null)
      return
    }
    const footprint = normalizeRectFootprint(dragPreview.footprint)
    if (!footprint) return
    const center = getFootprintCenter(footprint)
    setDragPreview(null)
    await onMapEntityCreate({
      kind: 'structures',
      footprint,
      position: center
    })
  }

  const finishMoveDrag = async () => {
    if (!activeDrag) return
    const dragState = activeDrag
    setActiveDrag(null)

    if (!dragState.moved) return

    if (dragState.kind === 'drones') {
      await onDroneMove({
        id: dragState.id,
        position: dragState.previewPosition
      })
      return
    }

    await onMapEntityMove({
      kind: dragState.kind,
      id: dragState.id,
      position: dragState.previewPosition,
      footprint: dragState.previewFootprint
    })
  }

  const handlePointerUp = async (event) => {
    const canvas = canvasRef.current
    const worldPoint = getWorldPointFromEvent(event)

    if (canvas?.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId)
    }

    if (dragPreview) {
      await finishBuildingDrag()
      return
    }

    if (activeDrag) {
      await finishMoveDrag()
      return
    }

    if (pointToolActive) {
      await onMapEntityCreate({
        kind: 'point',
        tool: editorTool,
        position: worldPoint
      })
      return
    }

    const droneHit = getDroneHit(worldPoint)
    if (droneHit) {
      onDroneClick(droneHit.id)
      onMapEntitySelect(null)
      return
    }

    if (editMode && editorTool === 'select') {
      const mapHit = getMapEntityHit(worldPoint)
      if (mapHit) {
        onMapEntitySelect({ kind: mapHit.kind, id: mapHit.entity.id })
        onDroneClick(null)
        return
      }
      onMapEntitySelect(null)
      onDroneClick(null)
      return
    }

    const hiddenEnemy = enemies.find((enemy) => !revealedEnemies.has(enemy.id) && enemy.distanceTo(worldPoint) <= getHitRadius(enemy))
    if (hiddenEnemy) {
      setRevealedEnemies((current) => new Set([...current, hiddenEnemy.id]))
      return
    }

    const hiddenSpecialEntity = specialEntities.find((entity) => !revealedSpecialEntities.has(entity.id) && entity.distanceTo(worldPoint) <= getHitRadius(entity))
    if (hiddenSpecialEntity) {
      setRevealedSpecialEntities((current) => new Set([...current, hiddenSpecialEntity.id]))
    }
  }

  const handlePointerLeave = () => {
    if (dragPreview || activeDrag) return
    setHoveredDrone(null)
    setHoveredMapEntity(null)
  }

  const cursor = (() => {
    if (dragPreview || activeDrag) return 'grabbing'
    if (editMode && (editorTool === 'building' || pointToolActive)) return 'crosshair'
    if (hoveredMapEntity || hoveredDrone) return 'pointer'
    return 'default'
  })()

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      onPointerDown={(event) => {
        void handlePointerDown(event)
      }}
      onPointerMove={handlePointerMove}
      onPointerUp={(event) => {
        void handlePointerUp(event)
      }}
      onPointerLeave={handlePointerLeave}
      style={{
        border: '2px solid #4A4A4A',
        backgroundColor: '#1A1A1A',
        cursor,
        display: 'block',
        maxWidth: '100%',
        height: 'auto',
        touchAction: 'none'
      }}
    />
  )
}

export default SwarmCanvas
