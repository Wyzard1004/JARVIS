/**
 * Grid Utilities for Client-Side Grid Calculations
 * 
 * Mirrors the Python GridCoordinateSystem for consistent behavior
 * on both backend and frontend.
 */

const NATO_PHONETIC = [
  'Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot',
  'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima',
  'Mike', 'November', 'Oscar', 'Papa', 'Quebec', 'Romeo',
  'Sierra', 'Tango', 'Uniform', 'Victor', 'Whiskey', 'X-ray',
  'Yankee', 'Zulu'
]

const GRID_SIZE = 26
const CELL_SIZE_PX = 30
const CANVAS_SIZE_PX = GRID_SIZE * CELL_SIZE_PX

/**
 * Convert row index (0-25) to NATO phonetic name
 */
export const rowIndexToNato = (rowIdx) => {
  if (rowIdx < 0 || rowIdx >= 26) {
    throw new Error(`Row index must be 0-25, got ${rowIdx}`)
  }
  return NATO_PHONETIC[rowIdx]
}

/**
 * Convert NATO phonetic name to row index
 */
export const natoToRowIndex = (natoName) => {
  const idx = NATO_PHONETIC.indexOf(natoName)
  if (idx === -1) {
    throw new Error(`Invalid NATO phonetic: ${natoName}`)
  }
  return idx
}

/**
 * Parse grid notation string to [rowIdx, colIdx]
 * Examples: "Alpha-1", "B-5", "Zulu-26"
 */
export const parseGridNotation = (gridStr) => {
  gridStr = gridStr.trim()
  
  // Try full NATO format: "Alpha-1"
  if (gridStr.includes('-')) {
    const [natoName, colStr] = gridStr.split('-')
    try {
      const rowIdx = natoToRowIndex(natoName.trim())
      const colIdx = parseInt(colStr.trim()) - 1 // Convert 1-indexed to 0-indexed
      if (colIdx < 0 || colIdx >= 26) {
        throw new Error(`Column must be 1-26, got ${colIdx + 1}`)
      }
      return [rowIdx, colIdx]
    } catch (e) {
      throw new Error(`Invalid grid notation: ${gridStr}`)
    }
  }

  // Try short format: "A1" or "Z26"
  if (gridStr.length >= 2) {
    const natoName = gridStr[0].toUpperCase()
    const colStr = gridStr.slice(1)
    try {
      const rowIdx = natoToRowIndex(natoName)
      const colIdx = parseInt(colStr) - 1
      if (colIdx < 0 || colIdx >= 26) {
        throw new Error(`Column must be 1-26, got ${colIdx + 1}`)
      }
      return [rowIdx, colIdx]
    } catch (e) {
      throw new Error(`Invalid grid notation: ${gridStr}`)
    }
  }

  throw new Error(`Invalid grid notation: ${gridStr}`)
}

/**
 * Build grid notation from [rowIdx, colIdx]
 * Examples: (0, 0) -> "Alpha-1", (25, 25) -> "Zulu-26"
 */
export const buildGridNotation = (rowIdx, colIdx) => {
  if (rowIdx < 0 || rowIdx >= 26 || colIdx < 0 || colIdx >= 26) {
    throw new Error(`Indices must be 0-25, got (${rowIdx}, ${colIdx})`)
  }
  const rowName = rowIndexToNato(rowIdx)
  const colNum = colIdx + 1
  return `${rowName}-${colNum}`
}

/**
 * Convert grid coordinates to pixel coordinates (cell center)
 */
export const gridToPixel = (rowIdx, colIdx, cellSize = CELL_SIZE_PX) => {
  const x = colIdx * cellSize + cellSize / 2
  const y = rowIdx * cellSize + cellSize / 2
  return [x, y]
}

/**
 * Convert pixel coordinates to grid coordinates
 */
export const pixelToGrid = (px, py, cellSize = CELL_SIZE_PX) => {
  let colIdx = Math.floor(px / cellSize)
  let rowIdx = Math.floor(py / cellSize)
  
  // Clamp to grid bounds
  colIdx = Math.max(0, Math.min(25, colIdx))
  rowIdx = Math.max(0, Math.min(25, rowIdx))
  
  return [rowIdx, colIdx]
}

/**
 * Calculate Euclidean distance between two grid positions
 */
export const euclideanDistance = (pos1, pos2) => {
  const [row1, col1] = pos1
  const [row2, col2] = pos2
  const dx = col2 - col1
  const dy = row2 - row1
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * Distance in cells between two grid positions
 */
export const distanceInCells = (gridPos1, gridPos2) => {
  return euclideanDistance(gridPos1, gridPos2)
}

/**
 * Check if target is within transmission range of source
 */
export const isInRange = (sourcePos, targetPos, rangeCells) => {
  const distance = distanceInCells(sourcePos, targetPos)
  return distance <= rangeCells
}

/**
 * Get all grid cells within transmission range
 */
export const getNeighborsInRange = (sourcePos, rangeCells, excludeSelf = true) => {
  const [sourceRow, sourceCol] = sourcePos
  const neighbors = []
  
  // Calculate bounding box for efficiency
  const minRow = Math.max(0, Math.floor(sourceRow - rangeCells))
  const maxRow = Math.min(25, Math.floor(sourceRow + rangeCells) + 1)
  const minCol = Math.max(0, Math.floor(sourceCol - rangeCells))
  const maxCol = Math.min(25, Math.floor(sourceCol + rangeCells) + 1)
  
  for (let row = minRow; row < maxRow; row++) {
    for (let col = minCol; col < maxCol; col++) {
      if (excludeSelf && row === sourceRow && col === sourceCol) continue
      if (isInRange(sourcePos, [row, col], rangeCells)) {
        neighbors.push([row, col])
      }
    }
  }
  
  return neighbors
}

/**
 * Generate smooth path from start to end as pixel coordinates
 */
export const generatePath = (startPos, endPos, pointsPerCell = 4, cellSize = CELL_SIZE_PX) => {
  const startPx = gridToPixel(startPos[0], startPos[1], cellSize)
  const endPx = gridToPixel(endPos[0], endPos[1], cellSize)
  
  const dx = endPx[0] - startPx[0]
  const dy = endPx[1] - startPx[1]
  const distance = Math.sqrt(dx * dx + dy * dy)
  
  if (distance === 0) {
    return [startPx]
  }
  
  const numPoints = Math.max(2, Math.round((distance / cellSize) * pointsPerCell))
  const path = []
  
  for (let i = 0; i < numPoints; i++) {
    const t = i / (numPoints - 1)
    const px = startPx[0] + (endPx[0] - startPx[0]) * t
    const py = startPx[1] + (endPx[1] - startPx[1]) * t
    path.push([px, py])
  }
  
  return path
}

/**
 * Generate patrol path through multiple waypoints
 */
export const generatePatrolPath = (waypoints, pointsPerCell = 4, cellSize = CELL_SIZE_PX) => {
  if (waypoints.length < 2) {
    return waypoints.length === 1 ? [gridToPixel(waypoints[0][0], waypoints[0][1], cellSize)] : []
  }
  
  let fullPath = []
  
  for (let i = 0; i < waypoints.length - 1; i++) {
    const segment = generatePath(waypoints[i], waypoints[i + 1], pointsPerCell, cellSize)
    
    // Skip first point of subsequent segments to avoid duplication
    if (i > 0) {
      segment.shift()
    }
    
    fullPath = fullPath.concat(segment)
  }
  
  return fullPath
}

/**
 * Clamp grid coordinates to valid range
 */
export const clampToGrid = (rowIdx, colIdx) => {
  return [
    Math.max(0, Math.min(25, rowIdx)),
    Math.max(0, Math.min(25, colIdx))
  ]
}

export default {
  NATO_PHONETIC,
  GRID_SIZE,
  CELL_SIZE_PX,
  CANVAS_SIZE_PX,
  rowIndexToNato,
  natoToRowIndex,
  parseGridNotation,
  buildGridNotation,
  gridToPixel,
  pixelToGrid,
  euclideanDistance,
  distanceInCells,
  isInRange,
  getNeighborsInRange,
  generatePath,
  generatePatrolPath,
  clampToGrid
}
