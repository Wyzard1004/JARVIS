export const WORLD_SIZE = 1000
export const DEFAULT_CANVAS_SIZE = 600
export const MIN_STRUCTURE_SIZE = 12
const EPSILON = 1e-6

export function clampWorldValue(value) {
  return Math.max(0, Math.min(WORLD_SIZE, Number(value) || 0))
}

export function clampWorldPoint(point) {
  if (!Array.isArray(point) || point.length !== 2) {
    return [WORLD_SIZE / 2, WORLD_SIZE / 2]
  }

  return [clampWorldValue(point[0]), clampWorldValue(point[1])]
}

export function worldToCanvasPoint(point, canvasSize = DEFAULT_CANVAS_SIZE) {
  const [x, y] = clampWorldPoint(point)
  const scale = canvasSize / WORLD_SIZE
  return [x * scale, y * scale]
}

export function canvasToWorldPoint(pixelPoint, canvasSize = DEFAULT_CANVAS_SIZE) {
  if (!Array.isArray(pixelPoint) || pixelPoint.length !== 2) {
    return [WORLD_SIZE / 2, WORLD_SIZE / 2]
  }

  const scale = WORLD_SIZE / canvasSize
  return clampWorldPoint([pixelPoint[0] * scale, pixelPoint[1] * scale])
}

export function normalizeRectFootprint(footprint) {
  if (!footprint || typeof footprint !== 'object') return null

  const width = Math.max(MIN_STRUCTURE_SIZE, Math.min(WORLD_SIZE, Number(footprint.width) || 0))
  const height = Math.max(MIN_STRUCTURE_SIZE, Math.min(WORLD_SIZE, Number(footprint.height) || 0))
  const x = Math.min(clampWorldValue(footprint.x), WORLD_SIZE - width)
  const y = Math.min(clampWorldValue(footprint.y), WORLD_SIZE - height)

  return {
    kind: 'rect',
    x,
    y,
    width,
    height
  }
}

export function createRectFootprint(startPoint, endPoint) {
  const [startX, startY] = clampWorldPoint(startPoint)
  const [endX, endY] = clampWorldPoint(endPoint)
  return normalizeRectFootprint({
    kind: 'rect',
    x: Math.min(startX, endX),
    y: Math.min(startY, endY),
    width: Math.abs(endX - startX),
    height: Math.abs(endY - startY)
  })
}

export function getFootprintCenter(footprint) {
  const rect = normalizeRectFootprint(footprint)
  if (!rect) return null
  return [rect.x + rect.width / 2, rect.y + rect.height / 2]
}

export function footprintToCanvasRect(footprint, canvasSize = DEFAULT_CANVAS_SIZE) {
  const rect = normalizeRectFootprint(footprint)
  if (!rect) return null
  const scale = canvasSize / WORLD_SIZE
  return {
    x: rect.x * scale,
    y: rect.y * scale,
    width: rect.width * scale,
    height: rect.height * scale
  }
}

export function pointInRect(point, footprint) {
  const [x, y] = clampWorldPoint(point)
  const rect = normalizeRectFootprint(footprint)
  if (!rect) return false
  return x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height
}

export function inferStructureFootprint(structure) {
  if (!structure || typeof structure !== 'object') return null
  const position = clampWorldPoint(structure.position)
  const render = structure.render || {}
  const renderSize = Number(render.size ?? render.radius ?? structure.renderSize ?? 18) || 18
  const blockingSize = Number(structure.blocking_size ?? structure.size ?? 0.8) || 0.8
  const width = Math.max(MIN_STRUCTURE_SIZE, renderSize * 3.6 * Math.max(0.65, blockingSize))
  const height = Math.max(
    MIN_STRUCTURE_SIZE,
    width * ((render.shape || structure.shape) === 'rectangle' ? 0.58 : 0.86)
  )
  return normalizeRectFootprint({
    kind: 'rect',
    x: position[0] - width / 2,
    y: position[1] - height / 2,
    width,
    height
  })
}

export function getStructureFootprint(structure) {
  return normalizeRectFootprint(structure?.footprint) || inferStructureFootprint(structure)
}

function cross(a, b) {
  return a[0] * b[1] - a[1] * b[0]
}

function subtract(a, b) {
  return [a[0] - b[0], a[1] - b[1]]
}

function segmentIntersection(a1, a2, b1, b2) {
  const r = subtract(a2, a1)
  const s = subtract(b2, b1)
  const denominator = cross(r, s)
  const qp = subtract(b1, a1)

  if (Math.abs(denominator) < EPSILON) return null

  const t = cross(qp, s) / denominator
  const u = cross(qp, r) / denominator
  if (t < 0 || t > 1 || u < 0 || u > 1) return null

  return {
    point: [a1[0] + r[0] * t, a1[1] + r[1] * t],
    distance: Math.hypot(r[0] * t, r[1] * t)
  }
}

export function getRectEdges(footprint) {
  const rect = normalizeRectFootprint(footprint)
  if (!rect) return []

  const topLeft = [rect.x, rect.y]
  const topRight = [rect.x + rect.width, rect.y]
  const bottomRight = [rect.x + rect.width, rect.y + rect.height]
  const bottomLeft = [rect.x, rect.y + rect.height]
  return [
    [topLeft, topRight],
    [topRight, bottomRight],
    [bottomRight, bottomLeft],
    [bottomLeft, topLeft]
  ]
}

export function segmentIntersectsRect(startPoint, endPoint, footprint) {
  const rect = normalizeRectFootprint(footprint)
  if (!rect) return false

  if (pointInRect(startPoint, rect) || pointInRect(endPoint, rect)) return true
  return getRectEdges(rect).some(([edgeStart, edgeEnd]) => segmentIntersection(startPoint, endPoint, edgeStart, edgeEnd))
}

export function doesAnyFootprintBlockSegment(startPoint, endPoint, footprints, ignorePredicate = null) {
  return (footprints || []).some((footprintEntry) => {
    if (!footprintEntry) return false
    if (ignorePredicate && ignorePredicate(footprintEntry)) return false
    const rect = footprintEntry.footprint || footprintEntry
    return segmentIntersectsRect(startPoint, endPoint, rect)
  })
}

function raySegmentIntersection(origin, direction, edgeStart, edgeEnd) {
  const edgeVector = subtract(edgeEnd, edgeStart)
  const denominator = cross(direction, edgeVector)
  if (Math.abs(denominator) < EPSILON) return null

  const offset = subtract(edgeStart, origin)
  const t = cross(offset, edgeVector) / denominator
  const u = cross(offset, direction) / denominator
  if (t < 0 || u < 0 || u > 1) return null

  return {
    point: [origin[0] + direction[0] * t, origin[1] + direction[1] * t],
    distance: t
  }
}

function getWorldBoundsFootprint() {
  return { kind: 'rect', x: 0, y: 0, width: WORLD_SIZE, height: WORLD_SIZE }
}

export function getNearestRayHit(originPoint, angle, maxDistance, footprints = []) {
  const origin = clampWorldPoint(originPoint)
  const direction = [Math.cos(angle), Math.sin(angle)]
  const maxDistancePoint = [
    origin[0] + direction[0] * maxDistance,
    origin[1] + direction[1] * maxDistance
  ]

  let nearest = {
    point: clampWorldPoint(maxDistancePoint),
    distance: maxDistance
  }

  for (const [edgeStart, edgeEnd] of getRectEdges(getWorldBoundsFootprint())) {
    const hit = raySegmentIntersection(origin, direction, edgeStart, edgeEnd)
    if (hit && hit.distance < nearest.distance) {
      nearest = hit
    }
  }

  for (const footprintEntry of footprints || []) {
    const rect = footprintEntry?.footprint || footprintEntry
    for (const [edgeStart, edgeEnd] of getRectEdges(rect)) {
      const hit = raySegmentIntersection(origin, direction, edgeStart, edgeEnd)
      if (hit && hit.distance < nearest.distance) {
        nearest = hit
      }
    }
  }

  return {
    point: clampWorldPoint(nearest.point),
    distance: nearest.distance
  }
}

export function computeVisibilityPolygon(originPoint, maxDistance, footprints = [], rayCount = 256) {
  const polygon = []
  for (let index = 0; index < rayCount; index += 1) {
    const angle = (Math.PI * 2 * index) / rayCount
    polygon.push(getNearestRayHit(originPoint, angle, maxDistance, footprints).point)
  }
  return polygon
}

export function translateFootprintToCenter(footprint, nextCenter) {
  const rect = normalizeRectFootprint(footprint)
  const center = clampWorldPoint(nextCenter)
  if (!rect) return null
  return normalizeRectFootprint({
    kind: 'rect',
    x: center[0] - rect.width / 2,
    y: center[1] - rect.height / 2,
    width: rect.width,
    height: rect.height
  })
}
