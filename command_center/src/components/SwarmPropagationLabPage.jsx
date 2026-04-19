import React, { useEffect, useRef, useState } from 'react'

const BANDWIDTH_BPS = 2_000_000
const HISTORY_POINTS = 96
const MAX_TRANSMISSIONS = 220
const MAX_FLASHES = 48
const PROPAGATION_WAVE_DELAY = 0.42

const DEFAULT_SETTINGS = {
  drones: 36,
  branching: 3,
  ttl: 4,
  payload: 900,
  rate: 6
}

const DEFAULT_TELEMETRY = {
  latency: '0.0 ms',
  coverage: '0%',
  hop: '0',
  redundancy: '0 / 0',
  slot: 'IDLE',
  statusText: 'Mesh staged. Initiate dispersion to see how the current topology behaves under command and uplink pressure.'
}

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const lerp = (start, end, t) => start + (end - start) * t

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)

const randomBetween = (min, max) => min + Math.random() * (max - min)

const formatPercent = (value) => `${Math.round(value)}%`

const formatLatency = (value) => `${Number(value || 0).toFixed(1)} ms`

const roundRect = (ctx, x, y, width, height, radius) => {
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

const getRangeStyle = (value, min, max) => {
  const pct = ((value - min) / Math.max(1, max - min)) * 100
  return {
    background: `linear-gradient(90deg, rgba(139,176,255,0.95) 0%, rgba(139,176,255,0.95) ${pct}%, rgba(255,255,255,0.18) ${pct}%, rgba(255,255,255,0.18) 100%)`
  }
}

const buildClusterCenters = (count) => {
  const centers = []
  for (let index = 0; index < count; index += 1) {
    const angle = (index / Math.max(1, count)) * Math.PI * 2 + randomBetween(-0.32, 0.32)
    const radius = 0.26 + randomBetween(-0.03, 0.04)
    let xNorm = 0.5 + Math.cos(angle) * radius
    let yNorm = 0.48 + Math.sin(angle) * radius * 0.72

    if (Math.abs(xNorm - 0.5) < 0.11) {
      xNorm += xNorm < 0.5 ? -0.1 : 0.1
    }

    centers.push({
      xNorm: clamp(xNorm, 0.14, 0.86),
      yNorm: clamp(yNorm, 0.14, 0.8)
    })
  }
  return centers
}

const buildAnchorLayout = (count) => {
  const anchors = []
  const clusterCount = clamp(Math.round(count / 6), 4, 10)
  const centers = buildClusterCenters(clusterCount)

  for (let index = 0; index < count; index += 1) {
    const center = centers[index % centers.length]
    const angle = randomBetween(0, Math.PI * 2)
    const radius = randomBetween(0.02, 0.11)
    const xNorm = clamp(center.xNorm + Math.cos(angle) * radius, 0.08, 0.92)
    const yNorm = clamp(center.yNorm + Math.sin(angle) * radius, 0.1, 0.84)
    anchors.push({
      id: index + 1,
      label: `D${index + 1}`,
      xNorm,
      yNorm
    })
  }

  return anchors
}

const buildGraph = (width, height, anchors, settings) => {
  const nodes = [
    {
      id: 0,
      label: 'Gateway',
      x: width * 0.5,
      y: height * 0.46,
      anchorX: width * 0.5,
      anchorY: height * 0.46,
      isGateway: true,
      active: true,
      pulse: 1,
      hop: 0
    },
    ...anchors.map((anchor, index) => ({
      id: index + 1,
      label: anchor.label || `D${index + 1}`,
      x: anchor.xNorm * width,
      y: anchor.yNorm * height,
      anchorX: anchor.xNorm * width,
      anchorY: anchor.yNorm * height,
      isGateway: false,
      active: false,
      pulse: 0,
      hop: Number.POSITIVE_INFINITY
    }))
  ]

  const edges = []
  const degrees = new Array(nodes.length).fill(0)
  const edgeMap = new Map()

  const addEdge = (a, b, tree) => {
    const low = Math.min(a, b)
    const high = Math.max(a, b)
    const key = `${low}:${high}`

    if (edgeMap.has(key)) {
      if (tree) {
        edgeMap.get(key).tree = true
      }
      return edgeMap.get(key)
    }

    const edge = {
      id: edges.length,
      a: low,
      b: high,
      key,
      tree: Boolean(tree),
      length: distance(nodes[low], nodes[high]),
      activity: 0,
      collisionPulse: 0,
      reconfigurePulse: 0
    }

    edges.push(edge)
    edgeMap.set(key, edge)
    degrees[low] += 1
    degrees[high] += 1
    return edge
  }

  const orderedNodeIds = nodes
    .slice(1)
    .map((node) => node.id)
    .sort((left, right) => distance(nodes[left], nodes[0]) - distance(nodes[right], nodes[0]))

  const connected = [0]
  orderedNodeIds.forEach((nodeId) => {
    let bestParent = 0
    let bestScore = Number.POSITIVE_INFINITY

    connected.forEach((candidateId) => {
      const score = distance(nodes[nodeId], nodes[candidateId]) * (1 + degrees[candidateId] * 0.12)
      if (score < bestScore) {
        bestScore = score
        bestParent = candidateId
      }
    })

    addEdge(bestParent, nodeId, true)
    connected.push(nodeId)
  })

  const targetDegree = settings.branching + 1
  for (let nodeId = 1; nodeId < nodes.length; nodeId += 1) {
    const neighborCandidates = []

    for (let otherId = 1; otherId < nodes.length; otherId += 1) {
      if (otherId === nodeId) continue
      neighborCandidates.push({
        id: otherId,
        dist: distance(nodes[nodeId], nodes[otherId])
      })
    }

    neighborCandidates.sort((left, right) => left.dist - right.dist)

    for (const candidate of neighborCandidates) {
      if (degrees[nodeId] >= targetDegree + 1) break
      if (candidate.dist > width * 0.28) break
      if (degrees[candidate.id] > targetDegree + 2) continue
      addEdge(nodeId, candidate.id, false)
    }
  }

  const adjacency = Array.from({ length: nodes.length }, () => [])
  edges.forEach((edge) => {
    adjacency[edge.a].push({ node: edge.b, edgeId: edge.id })
    adjacency[edge.b].push({ node: edge.a, edgeId: edge.id })
  })

  const parents = new Array(nodes.length).fill(null)
  const hops = new Array(nodes.length).fill(Number.POSITIVE_INFINITY)
  const visited = new Set([0])
  const queue = [0]
  hops[0] = 0

  while (queue.length) {
    const current = queue.shift()
    adjacency[current].forEach((neighbor) => {
      if (visited.has(neighbor.node)) return
      visited.add(neighbor.node)
      parents[neighbor.node] = current
      hops[neighbor.node] = hops[current] + 1
      queue.push(neighbor.node)
    })
  }

  let coveredCount = 0
  let hopSum = 0
  let maxCoveredHop = 0
  let redundantCount = 0
  let activeRedundantCount = 0
  let backupNodeCount = 0

  for (let index = 1; index < nodes.length; index += 1) {
    const hop = hops[index]
    nodes[index].hop = hop
    if (Number.isFinite(hop) && hop <= settings.ttl) {
      coveredCount += 1
      hopSum += hop
      maxCoveredHop = Math.max(maxCoveredHop, hop)
    }
  }

  edges.forEach((edge) => {
    if (edge.tree) return
    redundantCount += 1
    const aHop = hops[edge.a]
    const bHop = hops[edge.b]
    const aReachable = edge.a === 0 || (Number.isFinite(aHop) && aHop <= settings.ttl)
    const bReachable = edge.b === 0 || (Number.isFinite(bHop) && bHop <= settings.ttl)
    if (aReachable && bReachable) {
      activeRedundantCount += 1
    }
  })

  for (let nodeId = 1; nodeId < nodes.length; nodeId += 1) {
    const currentHop = hops[nodeId]
    if (!Number.isFinite(currentHop) || currentHop > settings.ttl) continue
    const hasBackup = adjacency[nodeId].some((neighbor) => {
      const edge = edges[neighbor.edgeId]
      const neighborHop = hops[neighbor.node]
      return !edge.tree && Number.isFinite(neighborHop) && neighborHop < currentHop && neighborHop <= settings.ttl
    })
    if (hasBackup) {
      backupNodeCount += 1
    }
  }

  return {
    nodes,
    edges,
    adjacency,
    parents,
    hops,
    coveredCount,
    averageHop: coveredCount ? hopSum / coveredCount : 0,
    maxCoveredHop,
    redundantCount,
    activeRedundantCount,
    backupNodeCount
  }
}

const getBackupNeighbor = (graph, nodeId, ttl) => {
  if (nodeId <= 0 || !graph.adjacency[nodeId]) return null

  const currentHop = graph.hops[nodeId]
  let bestNeighbor = null
  let bestScore = Number.POSITIVE_INFINITY

  graph.adjacency[nodeId].forEach((neighborInfo) => {
    const edge = graph.edges[neighborInfo.edgeId]
    const neighborHop = graph.hops[neighborInfo.node]
    if (edge.tree) return
    if (!Number.isFinite(neighborHop) || neighborHop >= currentHop || neighborHop > ttl) return
    const score = neighborHop * 1000 + edge.length
    if (score < bestScore) {
      bestScore = score
      bestNeighbor = neighborInfo.node
    }
  })

  return bestNeighbor
}

const pathToGateway = (graph, sourceNodeId, ttl, preferBackup) => {
  const path = [sourceNodeId]
  let current = sourceNodeId

  if (preferBackup) {
    const backupNeighbor = getBackupNeighbor(graph, sourceNodeId, ttl)
    if (backupNeighbor !== null) {
      current = backupNeighbor
      path.push(current)
    }
  }

  while (current !== 0 && graph.parents[current] !== null) {
    current = graph.parents[current]
    path.push(current)
  }

  return path
}

const computeMetrics = (state) => {
  const graph = state.graph
  const attemptedBits = graph.coveredCount * state.settings.payload * 8 * state.settings.rate
  const baselineSaturation = (attemptedBits / BANDWIDTH_BPS) * 100
  const dynamicLoad = clamp(state.transmissions.length * 1.7 + state.recentCollisions * 18, 0, 42)
  const saturationPct = clamp(baselineSaturation + dynamicLoad, 0, 100)

  let lossPct = 0
  if (saturationPct < 30) {
    lossPct = 0
  } else if (saturationPct <= 60) {
    lossPct = ((saturationPct - 30) / 30) * 42
  } else {
    const overload = saturationPct - 60
    lossPct = Math.min(99, 42 + 56 * (1 - Math.exp(-overload / 15)))
  }

  const totalNodes = Math.max(1, graph.nodes.length - 1)
  const coveragePct = (graph.coveredCount / totalNodes) * 100
  const latencyMs = graph.averageHop * (4.2 + state.settings.payload / 520) * (1 + (saturationPct / 100) * 0.52)

  return {
    saturationPct,
    lossPct,
    coveragePct,
    latencyMs,
    visualRate: clamp(graph.coveredCount * state.settings.rate * 0.085, 2.5, 52)
  }
}

const buildStatusText = (state, metrics) => {
  if (state.adaptation.active && state.adaptation.removedNode) {
    return `${state.adaptation.removedNode.label} was removed from the mesh. Backup links are re-lighting and parent routes are being recomputed around the fault.`
  }

  if (state.phase === 'idle') {
    return 'Mesh staged. Initiate dispersion to see how the current topology behaves under command and uplink pressure.'
  }

  if (state.phase === 'propagating') {
    const currentHop = Math.min(
      state.settings.ttl,
      Math.max(0, Math.floor((state.time - state.propagation.startedAt) / PROPAGATION_WAVE_DELAY))
    )
    return `Propagating command wave through hop ${currentHop}. Coverage is bounded by the active TTL while backup links accumulate near the gateway.`
  }

  if (metrics.saturationPct > 60) {
    return 'Propagation complete. Gateway-adjacent links are now the bottleneck, and CSMA-like contention is driving visible pressure onto the redundant mesh.'
  }

  if (metrics.coveragePct < 100) {
    return 'Propagation complete. Some drones remain outside the TTL envelope, leaving dark edge nodes even though backup links remain available inside the covered mesh.'
  }

  return 'Propagation complete. The mesh is covered, uplinks are returning through the gateway, and backup routes are visible without overwhelming the channel.'
}

const getTelemetry = (state) => {
  const metrics = computeMetrics(state)
  const currentHop = state.phase === 'propagating'
    ? Math.min(
        state.settings.ttl,
        Math.max(0, Math.floor((state.time - state.propagation.startedAt) / PROPAGATION_WAVE_DELAY))
      )
    : state.graph.maxCoveredHop
  const slotLabel = state.transmissions.length < 2
    ? 'IDLE'
    : `S${(Math.floor(state.time * (state.settings.rate * 0.7)) % Math.max(3, state.settings.branching + state.settings.ttl)) + 1}`

  return {
    latency: formatLatency(metrics.latencyMs),
    coverage: formatPercent(metrics.coveragePct),
    hop: String(currentHop),
    redundancy: state.graph.redundantCount
      ? `${state.graph.activeRedundantCount} / ${state.graph.redundantCount}`
      : '0 / 0',
    slot: slotLabel,
    statusText: buildStatusText(state, metrics),
    metrics
  }
}

const drawGraphBackground = (ctx, width, height) => {
  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, '#0f131a')
  gradient.addColorStop(1, '#0b0d12')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)

  ctx.save()
  ctx.strokeStyle = 'rgba(255,255,255,0.03)'
  ctx.lineWidth = 1
  for (let x = 42; x < width; x += 64) {
    ctx.beginPath()
    ctx.moveTo(x, 18)
    ctx.lineTo(x, height - 18)
    ctx.stroke()
  }
  for (let y = 22; y < height; y += 56) {
    ctx.beginPath()
    ctx.moveTo(18, y)
    ctx.lineTo(width - 18, y)
    ctx.stroke()
  }
  ctx.restore()
}

const drawEdges = (ctx, state, metrics) => {
  state.graph.edges.forEach((edge) => {
    const nodeA = state.graph.nodes[edge.a]
    const nodeB = state.graph.nodes[edge.b]
    const hopA = state.graph.hops[edge.a]
    const hopB = state.graph.hops[edge.b]
    const aReachable = edge.a === 0 || (Number.isFinite(hopA) && hopA <= state.settings.ttl)
    const bReachable = edge.b === 0 || (Number.isFinite(hopB) && hopB <= state.settings.ttl)
    const reachable = aReachable && bReachable

    ctx.save()
    ctx.lineCap = 'round'
    ctx.lineWidth = edge.tree ? 2.2 : 1.5
    if (!edge.tree) {
      ctx.setLineDash([7, 6])
    }
    ctx.strokeStyle = edge.tree
      ? reachable
        ? `rgba(255,255,255,${0.24 + edge.activity * 0.28})`
        : 'rgba(255,255,255,0.09)'
      : reachable
        ? `rgba(126,168,255,${0.22 + edge.activity * 0.18})`
        : 'rgba(126,168,255,0.16)'
    ctx.beginPath()
    ctx.moveTo(nodeA.x, nodeA.y)
    ctx.lineTo(nodeB.x, nodeB.y)
    ctx.stroke()

    if (edge.activity > 0.04) {
      ctx.setLineDash([])
      ctx.strokeStyle = edge.tree
        ? metrics.saturationPct < 30
          ? `rgba(168,239,143,${0.24 + edge.activity * 0.32})`
          : metrics.saturationPct < 60
            ? `rgba(255,209,102,${0.26 + edge.activity * 0.32})`
            : `rgba(255,100,123,${0.28 + edge.activity * 0.34})`
        : `rgba(154,183,255,${0.28 + edge.activity * 0.34})`
      ctx.lineWidth = edge.tree ? 3.4 : 2.7
      ctx.beginPath()
      ctx.moveTo(nodeA.x, nodeA.y)
      ctx.lineTo(nodeB.x, nodeB.y)
      ctx.stroke()
    }

    if (edge.collisionPulse > 0.02) {
      const midX = (nodeA.x + nodeB.x) / 2
      const midY = (nodeA.y + nodeB.y) / 2
      ctx.fillStyle = `rgba(255,100,123,${edge.collisionPulse * 0.25})`
      ctx.beginPath()
      ctx.arc(midX, midY, 16 + edge.collisionPulse * 12, 0, Math.PI * 2)
      ctx.fill()
    }

    if (edge.reconfigurePulse > 0.02) {
      ctx.setLineDash([])
      ctx.strokeStyle = `rgba(126,168,255,${0.16 + edge.reconfigurePulse * 0.34})`
      ctx.lineWidth = 5 + edge.reconfigurePulse * 3
      ctx.beginPath()
      ctx.moveTo(nodeA.x, nodeA.y)
      ctx.lineTo(nodeB.x, nodeB.y)
      ctx.stroke()
    }

    ctx.restore()
  })
}

const drawGateway = (ctx, state) => {
  const gateway = state.graph.nodes[0]

  ctx.save()
  ctx.shadowColor = 'rgba(126,168,255,0.34)'
  ctx.shadowBlur = 20 + state.deliveredPulse * 22
  ctx.fillStyle = '#0c1019'
  ctx.beginPath()
  ctx.arc(gateway.x, gateway.y + 20, 17, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = 'rgba(126,168,255,0.18)'
  ctx.beginPath()
  ctx.arc(gateway.x, gateway.y + 20, 22 + state.deliveredPulse * 14, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()

  const labelWidth = 128
  const labelHeight = 38
  const labelX = gateway.x - labelWidth / 2
  const labelY = gateway.y - 34

  ctx.fillStyle = 'rgba(17,20,27,0.94)'
  ctx.strokeStyle = 'rgba(126,168,255,0.4)'
  ctx.lineWidth = 2
  roundRect(ctx, labelX, labelY, labelWidth, labelHeight, 18)
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = '#f2f3f7'
  ctx.font = '700 16px "IBM Plex Sans", "Avenir Next", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('GATEWAY', gateway.x, labelY + labelHeight / 2)

  ctx.fillStyle = '#9fb7ff'
  ctx.font = '700 18px "JetBrains Mono", "IBM Plex Mono", monospace'
  ctx.fillText('*', gateway.x, gateway.y + 21)
}

const drawNodes = (ctx, state) => {
  for (let index = 1; index < state.graph.nodes.length; index += 1) {
    const node = state.graph.nodes[index]
    const reachable = node.active && node.hop <= state.settings.ttl
    const fill = reachable ? '#a8ef8f' : '#2b3343'
    const icon = reachable ? '#183324' : '#263147'

    ctx.save()
    ctx.shadowColor = reachable ? 'rgba(168,239,143,0.34)' : 'rgba(0,0,0,0)'
    ctx.shadowBlur = reachable ? 14 + node.pulse * 10 : 0
    ctx.fillStyle = fill
    ctx.beginPath()
    ctx.arc(node.x, node.y, 10.6 + (reachable ? node.pulse * 2 : 0), 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = icon
    ctx.beginPath()
    ctx.moveTo(node.x, node.y - 4.8)
    ctx.lineTo(node.x - 3.9, node.y + 3.6)
    ctx.lineTo(node.x + 3.9, node.y + 3.6)
    ctx.closePath()
    ctx.fill()
    ctx.restore()
  }

  drawGateway(ctx, state)
}

const drawTransmissions = (ctx, state) => {
  state.transmissions.forEach((transmission) => {
    ctx.save()
    ctx.shadowColor = transmission.glow
    ctx.shadowBlur = 16
    ctx.fillStyle = transmission.color
    ctx.beginPath()
    ctx.arc(transmission.x, transmission.y, transmission.size, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  })
}

const drawFlashes = (ctx, state) => {
  state.flashes.forEach((flash) => {
    const alpha = flash.life / flash.maxLife
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.strokeStyle = flash.color
    ctx.lineWidth = 2.5
    ctx.beginPath()
    ctx.arc(flash.x, flash.y, flash.radius * (1.2 - alpha * 0.2), 0, Math.PI * 2)
    ctx.stroke()
    ctx.restore()
  })
}

const drawAdaptationOverlay = (ctx, state) => {
  if (!state.adaptation.active || !state.adaptation.removedNode) return

  const alpha = state.adaptation.duration
    ? state.adaptation.timeLeft / state.adaptation.duration
    : 0
  const loss = state.adaptation.removedNode

  ctx.save()
  ctx.globalAlpha = alpha
  ctx.strokeStyle = 'rgba(255,100,123,0.92)'
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.arc(loss.x, loss.y, 15 + (1 - alpha) * 12, 0, Math.PI * 2)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(loss.x - 9, loss.y - 9)
  ctx.lineTo(loss.x + 9, loss.y + 9)
  ctx.moveTo(loss.x + 9, loss.y - 9)
  ctx.lineTo(loss.x - 9, loss.y + 9)
  ctx.stroke()

  state.adaptation.affectedNodes.forEach((point) => {
    ctx.strokeStyle = `rgba(126,168,255,${0.22 + alpha * 0.34})`
    ctx.lineWidth = 2
    ctx.setLineDash([6, 6])
    ctx.beginPath()
    ctx.moveTo(loss.x, loss.y)
    ctx.lineTo(point.x, point.y)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = `rgba(126,168,255,${0.16 + alpha * 0.2})`
    ctx.beginPath()
    ctx.arc(point.x, point.y, 10 + alpha * 8, 0, Math.PI * 2)
    ctx.fill()
  })

  ctx.fillStyle = 'rgba(255,100,123,0.92)'
  ctx.font = '700 12px "JetBrains Mono", "IBM Plex Mono", monospace'
  ctx.textAlign = 'left'
  ctx.fillText('NODE LOSS / REROUTE', loss.x + 18, loss.y - 10)
  ctx.restore()
}

const drawGraphLabels = (ctx, state, metrics, width) => {
  ctx.fillStyle = 'rgba(255,255,255,0.72)'
  ctx.font = '600 12px "JetBrains Mono", "IBM Plex Mono", monospace'
  ctx.textAlign = 'left'
  ctx.fillText('PROPAGATION MESH', 18, 22)

  ctx.textAlign = 'right'
  ctx.fillStyle = 'rgba(255,255,255,0.46)'
  ctx.fillText(`SAT ${Math.round(metrics.saturationPct)}%`, width - 18, 22)
}

const drawHistory = (ctx, state, width, height) => {
  ctx.clearRect(0, 0, width, height)

  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, 'rgba(14,17,24,0.98)')
  gradient.addColorStop(1, 'rgba(10,13,18,0.98)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)

  ctx.save()
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'
  ctx.lineWidth = 1
  for (let y = 18; y < height; y += 24) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }
  ctx.restore()

  if (!state.history.length) {
    ctx.fillStyle = 'rgba(255,255,255,0.42)'
    ctx.font = '600 12px "IBM Plex Sans", "Avenir Next", sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Initiate dispersion to populate the saturation history.', width / 2, height / 2)
    return
  }

  const xStep = width / Math.max(1, HISTORY_POINTS - 1)

  ctx.beginPath()
  state.history.forEach((entry, index) => {
    const x = index * xStep
    const y = height - clamp(entry.activity, 0, 1.15) * (height - 16)
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.lineTo((state.history.length - 1) * xStep, height)
  ctx.lineTo(0, height)
  ctx.closePath()
  const activityFill = ctx.createLinearGradient(0, 0, 0, height)
  activityFill.addColorStop(0, 'rgba(126,168,255,0.34)')
  activityFill.addColorStop(1, 'rgba(126,168,255,0.02)')
  ctx.fillStyle = activityFill
  ctx.fill()

  ctx.beginPath()
  state.history.forEach((entry, index) => {
    const x = index * xStep
    const y = height - clamp(entry.saturation, 0, 1.25) * (height - 16)
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.strokeStyle = '#8bb0ff'
  ctx.lineWidth = 2.2
  ctx.stroke()

  ctx.beginPath()
  state.history.forEach((entry, index) => {
    const x = index * xStep
    const y = height - clamp(entry.collisions, 0, 1) * (height - 16)
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.strokeStyle = '#ff647b'
  ctx.lineWidth = 1.6
  ctx.stroke()
}

const Control = ({ label, value, min, max, step, onChange, suffix = '', disabled = false }) => (
  <div className="grid gap-2">
    <div className="flex items-center justify-between gap-3">
      <label className="text-sm font-medium text-slate-100">{label}</label>
      <div className="min-w-[72px] rounded-xl border border-white/15 bg-white/[0.04] px-3 py-2 text-center font-mono text-sm text-white">
        {value}{suffix}
      </div>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(Number(event.target.value))}
      style={disabled ? undefined : getRangeStyle(value, min, max)}
      className="h-[6px] w-full appearance-none rounded-full bg-white/20 accent-blue-300 disabled:cursor-not-allowed disabled:opacity-70"
    />
  </div>
)

const MetricCard = ({ label, value }) => (
  <article className="rounded-[18px] border border-white/5 bg-white/[0.03] p-3">
    <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{label}</div>
    <div className="mt-2 font-mono text-2xl font-bold tracking-tight text-white">{value}</div>
  </article>
)

export default function SwarmPropagationLabPage() {
  const graphShellRef = useRef(null)
  const graphCanvasRef = useRef(null)
  const historyCanvasRef = useRef(null)
  const simulationRef = useRef(null)
  const settingsRef = useRef(DEFAULT_SETTINGS)

  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [telemetry, setTelemetry] = useState(DEFAULT_TELEMETRY)

  useEffect(() => {
    settingsRef.current = settings
    simulationRef.current?.applySettings(settings)
  }, [settings])

  useEffect(() => {
    const graphShell = graphShellRef.current
    const graphCanvas = graphCanvasRef.current
    const historyCanvas = historyCanvasRef.current
    const historyShell = historyCanvas?.parentElement

    if (!graphShell || !graphCanvas || !historyCanvas || !historyShell) {
      return undefined
    }

    const graphCtx = graphCanvas.getContext('2d')
    const historyCtx = historyCanvas.getContext('2d')

    if (!graphCtx || !historyCtx) {
      return undefined
    }

    const state = {
      settings: { ...settingsRef.current },
      anchors: buildAnchorLayout(settingsRef.current.drones),
      graph: {
        nodes: [],
        edges: [],
        adjacency: [],
        parents: [],
        hops: [],
        coveredCount: 0,
        averageHop: 0,
        maxCoveredHop: 0,
        redundantCount: 0,
        activeRedundantCount: 0,
        backupNodeCount: 0
      },
      graphWidth: 0,
      graphHeight: 0,
      historyWidth: 0,
      historyHeight: 0,
      time: 0,
      lastTimestamp: 0,
      transmissions: [],
      flashes: [],
      history: [],
      historyAccumulator: 0,
      recentCollisions: 0,
      deliveredPulse: 0,
      phase: 'idle',
      propagation: {
        startedAt: 0,
        complete: false,
        schedule: []
      },
      adaptation: {
        active: false,
        duration: 0,
        timeLeft: 0,
        removedNode: null,
        affectedNodes: []
      },
      spawnCarry: 0,
      rafId: 0,
      telemetryAccumulator: 0
    }

    const measureCanvases = () => {
      const graphRect = graphShell.getBoundingClientRect()
      const historyRect = historyShell.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)

      state.graphWidth = Math.max(420, Math.floor(graphRect.width || 1280))
      state.graphHeight = Math.max(360, Math.floor(graphRect.height || 620))
      state.historyWidth = Math.max(420, Math.floor(historyRect.width || 1248))
      state.historyHeight = Math.max(100, Math.floor(historyRect.height || 120))

      graphCanvas.width = Math.floor(state.graphWidth * dpr)
      graphCanvas.height = Math.floor(state.graphHeight * dpr)
      historyCanvas.width = Math.floor(state.historyWidth * dpr)
      historyCanvas.height = Math.floor(state.historyHeight * dpr)

      graphCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
      historyCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const updateTelemetryState = () => {
      const nextTelemetry = getTelemetry(state)
      setTelemetry({
        latency: nextTelemetry.latency,
        coverage: nextTelemetry.coverage,
        hop: nextTelemetry.hop,
        redundancy: nextTelemetry.redundancy,
        slot: nextTelemetry.slot,
        statusText: nextTelemetry.statusText
      })
      return nextTelemetry
    }

    const rebuildGraph = ({ keepHistory = false } = {}) => {
      measureCanvases()
      state.graph = buildGraph(state.graphWidth, state.graphHeight, state.anchors, state.settings)
      state.transmissions = []
      state.flashes = []
      state.recentCollisions = 0
      state.deliveredPulse = 0
      state.spawnCarry = 0
      state.propagation.complete = false
      state.propagation.schedule = []
      state.phase = 'idle'
      if (!keepHistory) {
        state.history = []
      }
      state.graph.edges.forEach((edge) => {
        edge.activity = 0
        edge.collisionPulse = 0
        edge.reconfigurePulse = 0
      })
      state.graph.nodes.forEach((node) => {
        node.active = node.isGateway
        node.pulse = node.isGateway ? 1 : 0
      })
      updateTelemetryState()
      drawHistory(historyCtx, state, state.historyWidth, state.historyHeight)
    }

    const startDispersion = () => {
      state.transmissions = []
      state.flashes = []
      state.history = []
      state.historyAccumulator = 0
      state.recentCollisions = 0
      state.deliveredPulse = 0
      state.spawnCarry = 0
      state.phase = 'propagating'
      state.propagation.complete = false
      state.propagation.startedAt = state.time
      state.propagation.schedule = []

      state.graph.nodes.forEach((node) => {
        node.active = node.isGateway
        node.pulse = node.isGateway ? 1 : 0
      })

      for (let nodeId = 1; nodeId < state.graph.nodes.length; nodeId += 1) {
        const hop = state.graph.hops[nodeId]
        const parentId = state.graph.parents[nodeId]
        if (!Number.isFinite(hop) || hop > state.settings.ttl || parentId === null) continue
        state.propagation.schedule.push({
          launchAt: hop * PROPAGATION_WAVE_DELAY + randomBetween(0.02, 0.09),
          parentId,
          nodeId
        })
      }

      state.propagation.schedule.sort((left, right) => left.launchAt - right.launchAt)
      updateTelemetryState()
    }

    const spawnFlash = (x, y, color, radius, life) => {
      if (state.flashes.length >= MAX_FLASHES) {
        state.flashes.shift()
      }
      state.flashes.push({
        x,
        y,
        color,
        radius,
        life,
        maxLife: life
      })
    }

    const makeTransmission = ({ path, kind, sourceNodeId, usesRedundant = false }) => {
      if (!path || path.length < 2 || state.transmissions.length >= MAX_TRANSMISSIONS) {
        return
      }

      const metrics = computeMetrics(state)
      const collisionChance = clamp(metrics.lossPct / 100, 0, 0.92)
      const collisionPlanned = kind === 'uplink' && Math.random() < collisionChance

      state.transmissions.push({
        path,
        kind,
        sourceNodeId,
        usesRedundant,
        segmentIndex: 0,
        distanceOnSegment: 0,
        speed: kind === 'c2'
          ? randomBetween(118, 170)
          : randomBetween(74, 122),
        size: kind === 'c2'
          ? 3.4
          : clamp(2.2 + state.settings.payload / 1800, 2.2, 4.8),
        color: kind === 'c2'
          ? '#8ea8ff'
          : usesRedundant
            ? '#9ab7ff'
            : metrics.saturationPct < 30
              ? '#a8ef8f'
              : metrics.saturationPct < 60
                ? '#ffd166'
                : '#ff647b',
        glow: kind === 'c2'
          ? 'rgba(142,168,255,0.42)'
          : usesRedundant
            ? 'rgba(154,183,255,0.34)'
            : metrics.saturationPct < 30
              ? 'rgba(168,239,143,0.34)'
              : metrics.saturationPct < 60
                ? 'rgba(255,209,102,0.32)'
                : 'rgba(255,100,123,0.34)',
        collisionPlanned,
        collisionSegment: collisionPlanned ? Math.floor(randomBetween(0, path.length - 1)) : -1,
        collisionProgress: randomBetween(0.38, 0.72),
        x: state.graph.nodes[path[0]].x,
        y: state.graph.nodes[path[0]].y
      })
    }

    const removeRandomNode = () => {
      if (state.anchors.length <= 3) return

      const removeIndex = Math.floor(Math.random() * state.anchors.length)
      const removedAnchor = state.anchors[removeIndex]
      const removedPoint = {
        x: removedAnchor.xNorm * state.graphWidth,
        y: removedAnchor.yNorm * state.graphHeight,
        label: removedAnchor.label
      }

      state.anchors = state.anchors.filter((_, index) => index !== removeIndex)
      state.adaptation = {
        active: true,
        duration: 4.6,
        timeLeft: 4.6,
        removedNode: removedPoint,
        affectedNodes: state.anchors
          .map((anchor) => ({
            x: anchor.xNorm * state.graphWidth,
            y: anchor.yNorm * state.graphHeight,
            d: Math.hypot(anchor.xNorm * state.graphWidth - removedPoint.x, anchor.yNorm * state.graphHeight - removedPoint.y)
          }))
          .sort((left, right) => left.d - right.d)
          .slice(0, 5)
          .map((item) => ({ x: item.x, y: item.y }))
      }

      rebuildGraph({ keepHistory: false })
      state.graph.edges.forEach((edge) => {
        const nodeA = state.graph.nodes[edge.a]
        const nodeB = state.graph.nodes[edge.b]
        const midX = (nodeA.x + nodeB.x) / 2
        const midY = (nodeA.y + nodeB.y) / 2
        const distToLoss = Math.hypot(midX - removedPoint.x, midY - removedPoint.y)
        if (distToLoss < state.graphWidth * 0.22 || !edge.tree) {
          edge.reconfigurePulse = distToLoss < state.graphWidth * 0.16 ? 1 : 0.54
        }
      })
      startDispersion()
    }

    const applySettings = (nextSettings) => {
      state.settings = { ...nextSettings }
      state.anchors = buildAnchorLayout(nextSettings.drones)
      state.adaptation = {
        active: false,
        duration: 0,
        timeLeft: 0,
        removedNode: null,
        affectedNodes: []
      }
      rebuildGraph({ keepHistory: false })
    }

    const tick = (timestamp) => {
      if (!state.lastTimestamp) {
        state.lastTimestamp = timestamp
      }

      const dt = Math.min(0.05, (timestamp - state.lastTimestamp) / 1000)
      state.lastTimestamp = timestamp
      state.time += dt

      state.graph.nodes.forEach((node) => {
        node.pulse = Math.max(0, node.pulse - dt * 0.7)
      })

      if (state.phase === 'propagating') {
        const elapsed = state.time - state.propagation.startedAt
        while (state.propagation.schedule.length && elapsed >= state.propagation.schedule[0].launchAt) {
          const nextLaunch = state.propagation.schedule.shift()
          makeTransmission({
            path: [nextLaunch.parentId, nextLaunch.nodeId],
            kind: 'c2',
            sourceNodeId: nextLaunch.nodeId
          })
        }

        if (!state.propagation.schedule.length && !state.transmissions.some((item) => item.kind === 'c2')) {
          state.phase = 'complete'
          state.propagation.complete = true
        }
      }

      if (state.phase !== 'idle') {
        const metrics = computeMetrics(state)
        let remaining = metrics.visualRate * dt + state.spawnCarry
        while (remaining >= 1) {
          const reachableNodes = []
          for (let nodeId = 1; nodeId < state.graph.nodes.length; nodeId += 1) {
            const node = state.graph.nodes[nodeId]
            if (node.active && node.hop <= state.settings.ttl) {
              reachableNodes.push(nodeId)
            }
          }

          if (reachableNodes.length) {
            const sourceNodeId = reachableNodes[Math.floor(Math.random() * reachableNodes.length)]
            const hasBackup = getBackupNeighbor(state.graph, sourceNodeId, state.settings.ttl) !== null
            const useBackup = hasBackup && Math.random() < Math.min(0.46, 0.14 + (state.graph.backupNodeCount / Math.max(1, state.graph.coveredCount)) * 0.4)
            makeTransmission({
              path: pathToGateway(state.graph, sourceNodeId, state.settings.ttl, useBackup),
              kind: 'uplink',
              sourceNodeId,
              usesRedundant: useBackup
            })
          }
          remaining -= 1
        }
        state.spawnCarry = remaining
      }

      state.graph.edges.forEach((edge) => {
        edge.activity *= 0.92
        edge.collisionPulse = Math.max(0, edge.collisionPulse - dt * 2.2)
        edge.reconfigurePulse = Math.max(0, edge.reconfigurePulse - dt * 0.55)
      })

      for (let index = state.transmissions.length - 1; index >= 0; index -= 1) {
        const transmission = state.transmissions[index]
        const fromId = transmission.path[transmission.segmentIndex]
        const toId = transmission.path[transmission.segmentIndex + 1]
        const fromNode = state.graph.nodes[fromId]
        const toNode = state.graph.nodes[toId]

        if (!fromNode || !toNode) {
          state.transmissions.splice(index, 1)
          continue
        }

        const edge = state.graph.edges.find((candidate) => (
          candidate.key === `${Math.min(fromId, toId)}:${Math.max(fromId, toId)}`
        ))

        const segmentLength = distance(fromNode, toNode) || 1
        transmission.distanceOnSegment += transmission.speed * dt
        const progress = clamp(transmission.distanceOnSegment / segmentLength, 0, 1)
        transmission.x = lerp(fromNode.x, toNode.x, progress)
        transmission.y = lerp(fromNode.y, toNode.y, progress)

        if (edge) {
          edge.activity = Math.min(1, edge.activity + 0.16)
        }

        if (
          transmission.collisionPlanned &&
          transmission.segmentIndex === transmission.collisionSegment &&
          progress >= transmission.collisionProgress
        ) {
          spawnFlash(transmission.x, transmission.y, '#ff647b', 18, 0.28)
          if (edge) {
            edge.collisionPulse = 1
          }
          state.recentCollisions = Math.min(1, state.recentCollisions + 0.32)
          state.transmissions.splice(index, 1)
          continue
        }

        if (progress >= 1) {
          transmission.segmentIndex += 1
          transmission.distanceOnSegment = 0

          if (transmission.segmentIndex >= transmission.path.length - 1) {
            if (transmission.kind === 'c2') {
              const node = state.graph.nodes[transmission.sourceNodeId]
              if (node) {
                node.active = true
                node.pulse = 1
                spawnFlash(node.x, node.y, '#8ea8ff', 14, 0.24)
              }
            } else {
              state.deliveredPulse = Math.min(1, state.deliveredPulse + 0.24)
            }
            state.transmissions.splice(index, 1)
          }
        }
      }

      state.deliveredPulse = Math.max(0, state.deliveredPulse - dt * 0.82)
      state.recentCollisions = Math.max(0, state.recentCollisions - dt * 0.42)

      if (state.adaptation.active) {
        state.adaptation.timeLeft = Math.max(0, state.adaptation.timeLeft - dt)
        if (state.adaptation.timeLeft <= 0) {
          state.adaptation.active = false
        }
      }

      for (let index = state.flashes.length - 1; index >= 0; index -= 1) {
        state.flashes[index].life -= dt
        if (state.flashes[index].life <= 0) {
          state.flashes.splice(index, 1)
        }
      }

      state.historyAccumulator += dt
      if (state.historyAccumulator >= 0.12) {
        state.historyAccumulator = 0
        const metrics = computeMetrics(state)
        const baselineCapacity = Math.max(12, state.graph.coveredCount * 0.42)
        const normalizedActivity = clamp(
          (state.transmissions.length + state.recentCollisions * 8) / baselineCapacity,
          0,
          1.15
        )
        state.history.push({
          activity: normalizedActivity,
          collisions: state.recentCollisions,
          saturation: clamp(metrics.saturationPct / 100, 0, 1.25)
        })
        if (state.history.length > HISTORY_POINTS) {
          state.history.shift()
        }
      }

      const telemetrySnapshot = getTelemetry(state)

      drawGraphBackground(graphCtx, state.graphWidth, state.graphHeight)
      drawEdges(graphCtx, state, telemetrySnapshot.metrics)
      drawNodes(graphCtx, state)
      drawTransmissions(graphCtx, state)
      drawFlashes(graphCtx, state)
      drawAdaptationOverlay(graphCtx, state)
      drawGraphLabels(graphCtx, state, telemetrySnapshot.metrics, state.graphWidth)
      drawHistory(historyCtx, state, state.historyWidth, state.historyHeight)

      state.telemetryAccumulator += dt
      if (state.telemetryAccumulator >= 0.14) {
        state.telemetryAccumulator = 0
        setTelemetry({
          latency: telemetrySnapshot.latency,
          coverage: telemetrySnapshot.coverage,
          hop: telemetrySnapshot.hop,
          redundancy: telemetrySnapshot.redundancy,
          slot: telemetrySnapshot.slot,
          statusText: telemetrySnapshot.statusText
        })
      }

      state.rafId = window.requestAnimationFrame(tick)
    }

    simulationRef.current = {
      applySettings,
      reset: () => {
        state.anchors = buildAnchorLayout(state.settings.drones)
        state.adaptation.active = false
        rebuildGraph({ keepHistory: false })
      },
      startDispersion,
      removeRandomNode
    }

    rebuildGraph({ keepHistory: false })

    const resizeHandler = () => {
      rebuildGraph({ keepHistory: true })
    }

    let resizeObserver = null
    if (typeof window.ResizeObserver === 'function') {
      resizeObserver = new window.ResizeObserver(() => {
        resizeHandler()
      })
      resizeObserver.observe(graphShell)
      resizeObserver.observe(historyShell)
    } else {
      window.addEventListener('resize', resizeHandler)
    }

    state.rafId = window.requestAnimationFrame(tick)

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect()
      } else {
        window.removeEventListener('resize', resizeHandler)
      }
      window.cancelAnimationFrame(state.rafId)
      simulationRef.current = null
    }
  }, [])

  const updateSetting = (key, value) => {
    setSettings((current) => ({
      ...current,
      [key]: value
    }))
  }

  return (
    <main className="space-y-5 p-4 md:p-5">
      <section className="overflow-hidden rounded-[30px] border border-slate-700/70 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.12),transparent_28%),linear-gradient(180deg,rgba(23,25,31,0.98),rgba(17,19,25,0.98))] shadow-[0_28px_90px_rgba(0,0,0,0.42)]">
        <div className="grid gap-5 px-5 py-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
          <div className="space-y-4">
            <span className="inline-flex rounded-full border border-blue-300/25 bg-blue-400/10 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.22em] text-blue-100">
              Propagation Stress Lab
            </span>
            <div className="space-y-3">
              <h2 className="max-w-4xl text-3xl font-semibold tracking-tight text-white md:text-[2.35rem]">
                Model how hop limits, payload size, and backup links change mesh behavior before it touches the live relay demo.
              </h2>
              <p className="max-w-4xl text-sm leading-7 text-slate-300">
                This page is a planning and stress tool rather than a live feed. It visualizes a gateway-centered mesh under configurable C2 load so you can see TTL coverage, redundant links, saturation, and reroute pressure after node loss without claiming those exact counts are the deployed hardware topology.
              </p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Why This Page Exists</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                The page makes propagation assumptions visible. If TTL is too short or payload pressure is too high, you see the coverage and contention cost directly.
              </p>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">What It Emphasizes</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Gateway pressure, backup-link usage, and the difference between nominal command dispersion and a reroute event after node loss.
              </p>
            </div>
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">What It Is Not</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                It is not claiming the live JARVIS demo currently runs dozens of nodes. It is a stress-modeling lens for mesh behavior and relay design choices.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(36,39,44,0.98),rgba(24,27,33,0.98))] shadow-[0_28px_80px_rgba(0,0,0,0.45)]">
        <div className="grid gap-4 border-b border-white/5 px-5 py-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,2fr)]">
          <div>
            <h3 className="text-[1.9rem] font-bold tracking-tight text-white">Swarm Propagation Stress Lab</h3>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">{telemetry.statusText}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Total Latency" value={telemetry.latency} />
            <MetricCard label="Coverage" value={telemetry.coverage} />
            <MetricCard label="Current Hop" value={telemetry.hop} />
            <MetricCard label="Backup Links" value={telemetry.redundancy} />
            <MetricCard label="Active Slot" value={telemetry.slot} />
          </div>
        </div>

        <div className="border-b border-white/5 bg-[radial-gradient(circle_at_center,rgba(96,117,180,0.08),transparent_45%),rgba(10,13,19,0.9)]">
          <div ref={graphShellRef} className="relative h-[33rem] min-h-[420px] w-full">
            <canvas ref={graphCanvasRef} className="block h-full w-full" />
          </div>
        </div>

        <div className="border-b border-white/5 bg-[linear-gradient(180deg,rgba(13,16,22,0.98),rgba(12,15,21,0.98))] px-4 py-4">
          <div>
            <h4 className="text-lg font-semibold text-white">Network Saturation History</h4>
            <p className="mt-1 text-sm text-slate-400">
              Blue traces overall saturation pressure, the filled area shows activity level, and the red line marks collision pressure as redundancy and load rise together.
            </p>
          </div>
          <div className="mt-3 h-32 overflow-hidden rounded-[18px] border border-white/5 bg-black/10">
            <canvas ref={historyCanvasRef} className="block h-full w-full" />
          </div>
        </div>

        <div className="grid gap-5 px-5 py-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Control
              label="Number of Drones"
              value={settings.drones}
              min={8}
              max={100}
              step={1}
              onChange={(value) => updateSetting('drones', value)}
            />
            <Control
              label="Branching Factor"
              value={settings.branching}
              min={1}
              max={6}
              step={1}
              onChange={(value) => updateSetting('branching', value)}
            />
            <Control
              label="Hop Limit (TTL)"
              value={settings.ttl}
              min={1}
              max={8}
              step={1}
              onChange={(value) => updateSetting('ttl', value)}
            />
            <Control
              label="Payload Size"
              value={settings.payload}
              min={50}
              max={5000}
              step={10}
              onChange={(value) => updateSetting('payload', value)}
            />
            <Control
              label="Broadcast Rate"
              value={settings.rate}
              min={1}
              max={20}
              step={1}
              onChange={(value) => updateSetting('rate', value)}
            />
            <Control
              label="Channel Model"
              value={2}
              min={0}
              max={1}
              step={1}
              suffix=" Mbps"
              disabled
              onChange={() => {}}
            />
          </div>

          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <button
                type="button"
                onClick={() => simulationRef.current?.reset()}
                className="rounded-[18px] bg-gradient-to-b from-slate-600 to-slate-700 px-4 py-4 text-sm font-semibold text-white transition hover:-translate-y-0.5"
              >
                Reset Mesh
              </button>
              <button
                type="button"
                onClick={() => simulationRef.current?.removeRandomNode()}
                className="rounded-[18px] bg-gradient-to-b from-rose-700 to-rose-800 px-4 py-4 text-sm font-semibold text-white transition hover:-translate-y-0.5"
              >
                Remove Random Node
              </button>
              <button
                type="button"
                onClick={() => simulationRef.current?.startDispersion()}
                className="rounded-[18px] bg-gradient-to-b from-indigo-500 to-blue-700 px-4 py-4 text-sm font-semibold text-white transition hover:-translate-y-0.5"
              >
                Initiate Dispersion
              </button>
            </div>

            <div className="rounded-[22px] border border-white/10 bg-black/15 p-4">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Reading Guide</div>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Solid links are primary routes, dashed blue links are redundant backups, the center badge is the gateway, and removing a node forces the mesh to expose reroute pressure around the loss point.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
