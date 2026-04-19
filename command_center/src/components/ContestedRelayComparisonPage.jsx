import React, { useEffect, useRef, useState } from 'react'

const EVENT_LIFETIME_MS = 9000
const EVENT_POSITIONS = [
  { x: 0.2, y: 0.26 },
  { x: 0.7, y: 0.3 },
  { x: 0.42, y: 0.48 },
  { x: 0.58, y: 0.62 },
  { x: 0.3, y: 0.68 }
]

const SUMMARY_CARDS = [
  {
    label: 'Tier 1',
    value: '8 Pathfinders',
    detail: 'Forward sensors that discover hazards first and should only emit small local bursts.'
  },
  {
    label: 'Tier 2',
    value: '21 Scouts',
    detail: 'Local maneuver and auction layer that should absorb most traffic without waking the whole network.'
  },
  {
    label: 'Tier 3',
    value: 'Overwatch + Operator',
    detail: 'High-value verification and release authority, not the default router for every frontline update.'
  }
]

const NOTE_CARDS = [
  {
    title: 'Hazard Event',
    detail: 'A frontline contact should cause a local reroute, not a full climb into a centralized approval loop.'
  },
  {
    title: 'Target Event',
    detail: 'A target discovery should narrow traffic to the relevant scout cluster before escalating to the operator gate.'
  },
  {
    title: 'Why It Matters',
    detail: 'The point of the page is to make communication doctrine visible: long global relay chains create congestion that local autonomy avoids.'
  }
]

const ROLE_COLORS = {
  pathfinder: '#66dfff',
  scout: '#8ef5af',
  overwatch: '#ffc96b',
  human: '#f4f7ff'
}

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)

const getIdSeed = (id) => {
  return String(id || '')
    .split('')
    .reduce((total, char, index) => total + char.charCodeAt(0) * (index + 1), 0)
}

const withAlpha = (hexColor, alpha) => {
  const value = String(hexColor || '').replace('#', '')
  if (value.length !== 6) return hexColor
  const red = Number.parseInt(value.slice(0, 2), 16)
  const green = Number.parseInt(value.slice(2, 4), 16)
  const blue = Number.parseInt(value.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}

const drawTriangle = (ctx, x, y, size) => {
  ctx.beginPath()
  ctx.moveTo(x, y - size)
  ctx.lineTo(x + size * 0.88, y + size * 0.76)
  ctx.lineTo(x - size * 0.88, y + size * 0.76)
  ctx.closePath()
}

const drawHexagon = (ctx, x, y, size) => {
  ctx.beginPath()
  for (let index = 0; index < 6; index += 1) {
    const angle = (Math.PI / 3) * index - Math.PI / 6
    const pointX = x + Math.cos(angle) * size
    const pointY = y + Math.sin(angle) * size
    if (index === 0) {
      ctx.moveTo(pointX, pointY)
    } else {
      ctx.lineTo(pointX, pointY)
    }
  }
  ctx.closePath()
}

const buildFormation = (width, height) => {
  const nodes = []
  const pushNode = (id, role, x, y) => {
    const seed = getIdSeed(id)
    nodes.push({
      id,
      role,
      baseX: x * width,
      baseY: y * height,
      x: x * width,
      y: y * height,
      size: role === 'overwatch' ? 11 : role === 'human' ? 9 : role === 'pathfinder' ? 7.5 : 6.8,
      phase: seed * 0.11,
      driftX: role === 'human' ? 1.2 : role === 'overwatch' ? 2.2 : role === 'pathfinder' ? 3.8 : 3,
      driftY: role === 'human' ? 0.8 : role === 'overwatch' ? 1.6 : role === 'pathfinder' ? 2.8 : 2.3
    })
  }

  const pathfinderRows = [
    { y: 0.18, count: 4, start: 0.18, span: 0.58 },
    { y: 0.27, count: 4, start: 0.14, span: 0.66 }
  ]

  let pathfinderIndex = 0
  pathfinderRows.forEach((row) => {
    for (let index = 0; index < row.count; index += 1) {
      const x = row.start + (row.span / Math.max(1, row.count - 1)) * index
      pathfinderIndex += 1
      pushNode(`P${pathfinderIndex}`, 'pathfinder', x, row.y)
    }
  })

  const scoutRows = [
    { y: 0.42, count: 5, start: 0.12, span: 0.72 },
    { y: 0.53, count: 5, start: 0.11, span: 0.74 },
    { y: 0.64, count: 6, start: 0.08, span: 0.8 },
    { y: 0.75, count: 5, start: 0.15, span: 0.68 }
  ]

  let scoutIndex = 0
  scoutRows.forEach((row) => {
    for (let index = 0; index < row.count; index += 1) {
      const x = row.start + (row.span / Math.max(1, row.count - 1)) * index
      scoutIndex += 1
      pushNode(`S${scoutIndex}`, 'scout', x, row.y)
    }
  })

  pushNode('O1', 'overwatch', 0.52, 0.87)
  pushNode('H1', 'human', 0.14, 0.93)
  return nodes
}

const animateNodes = (nodes, nowMs, noise, activeEvents) => {
  const hazardEvents = activeEvents.filter((event) => event.type === 'hazard')
  const targetEvents = activeEvents.filter((event) => event.type === 'target')

  return nodes.map((node) => {
    const driftTime = nowMs / 1000
    let x = node.baseX + Math.sin(driftTime * 0.72 + node.phase) * node.driftX
    let y = node.baseY + Math.cos(driftTime * 0.56 + node.phase * 0.85) * node.driftY

    const noiseBias = (noise / 100) * 1.2
    x += Math.cos(driftTime * 1.1 + node.phase * 0.5) * noiseBias
    y += Math.sin(driftTime * 0.94 + node.phase * 0.4) * noiseBias

    hazardEvents.forEach((event) => {
      const eventX = event.x * 1
      const eventY = event.y * 1
      const dx = x - eventX
      const dy = y - eventY
      const eventDistance = Math.hypot(dx, dy) || 1
      if (eventDistance < 130 && node.role !== 'human' && node.role !== 'overwatch') {
        const repelStrength = (1 - eventDistance / 130) * (node.role === 'pathfinder' ? 8 : 5)
        x += (dx / eventDistance) * repelStrength
        y += (dy / eventDistance) * repelStrength
      }
    })

    targetEvents.forEach((event) => {
      const eventX = event.x * 1
      const eventY = event.y * 1
      const dx = eventX - x
      const dy = eventY - y
      const eventDistance = Math.hypot(dx, dy) || 1
      if (eventDistance < 150 && node.role === 'scout') {
        const attractStrength = (1 - eventDistance / 150) * 2.2
        x += (dx / eventDistance) * attractStrength
        y += (dy / eventDistance) * attractStrength
      }
    })

    return {
      ...node,
      x,
      y
    }
  })
}

const drawSignalPulse = (ctx, from, to, color, nowMs, phaseOffset = 0, alpha = 0.95) => {
  const progress = ((nowMs / 900) + phaseOffset) % 1
  const pulseX = from.x + (to.x - from.x) * progress
  const pulseY = from.y + (to.y - from.y) * progress

  ctx.save()
  ctx.fillStyle = withAlpha(color, alpha)
  ctx.shadowColor = withAlpha(color, 0.55)
  ctx.shadowBlur = 14
  ctx.beginPath()
  ctx.arc(pulseX, pulseY, 3.2, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
}

const buildBaseEdges = (nodes, mode) => {
  const byId = Object.fromEntries(nodes.map((node) => [node.id, node]))
  const pathfinders = nodes.filter((node) => node.role === 'pathfinder')
  const scouts = nodes.filter((node) => node.role === 'scout')
  const overwatch = byId.O1
  const human = byId.H1

  if (mode === 'centralized') {
    return [
      ...pathfinders.map((node) => [node, overwatch]),
      ...scouts.map((node) => [node, overwatch]),
      [overwatch, human]
    ]
  }

  const localEdges = []
  pathfinders.forEach((node) => {
    const nearestScout = scouts
      .map((candidate) => ({ candidate, d: distance(node, candidate) }))
      .sort((left, right) => left.d - right.d)[0]?.candidate
    if (nearestScout) {
      localEdges.push([node, nearestScout])
    }
  })

  scouts.forEach((node) => {
    const peers = scouts
      .filter((candidate) => candidate.id !== node.id)
      .map((candidate) => ({ candidate, d: distance(node, candidate) }))
      .sort((left, right) => left.d - right.d)
      .slice(0, 2)
      .map((item) => item.candidate)
    peers.forEach((peer) => {
      if (!localEdges.some(([from, to]) => (
        (from.id === node.id && to.id === peer.id) ||
        (from.id === peer.id && to.id === node.id)
      ))) {
        localEdges.push([node, peer])
      }
    })
  })

  const clusterLeads = scouts
    .filter((_, index) => index % 5 === 0)
    .slice(0, 3)

  return [
    ...localEdges,
    ...clusterLeads.map((node) => [node, overwatch]),
    [overwatch, human]
  ]
}

const buildMetrics = (mode, noise, events, nowMs) => {
  let saturation = mode === 'centralized' ? 12 + noise * 0.58 : 8 + noise * 0.26
  let latency = mode === 'centralized' ? 88 + noise * 3.7 : 46 + noise * 1.8
  let loss = mode === 'centralized' ? noise * 0.18 : noise * 0.07
  let pressure = mode === 'centralized' ? 14 + noise * 0.65 : 78 - noise * 0.18

  const activeEvents = events.filter((event) => nowMs - event.createdAt < EVENT_LIFETIME_MS)
  const latestEvent = activeEvents.at(-1) || null

  activeEvents.forEach((event) => {
    const intensity = 1 - ((nowMs - event.createdAt) / EVENT_LIFETIME_MS)
    if (event.type === 'hazard') {
      if (mode === 'centralized') {
        saturation += 26 * intensity
        latency += 185 * intensity
        loss += 13 * intensity
        pressure += 31 * intensity
      } else {
        saturation += 8 * intensity
        latency += 58 * intensity
        loss += 4 * intensity
        pressure -= 8 * intensity
      }
    } else {
      if (mode === 'centralized') {
        saturation += 22 * intensity
        latency += 152 * intensity
        loss += 11 * intensity
        pressure += 26 * intensity
      } else {
        saturation += 10 * intensity
        latency += 74 * intensity
        loss += 5 * intensity
        pressure -= 6 * intensity
      }
    }
  })

  saturation = clamp(Math.round(saturation), 0, 99)
  latency = Math.round(latency)
  loss = clamp(Math.round(loss), 0, 99)
  pressure = clamp(Math.round(pressure), 0, 99)

  if (!latestEvent) {
    return {
      saturation,
      latency,
      loss,
      pressure,
      pillTone: mode === 'centralized' ? 'neutral' : 'positive',
      pillLabel: 'Idle',
      state: mode === 'centralized'
        ? 'Swarm advancing under centralized relay discipline.'
        : 'Swarm advancing with local autonomy intact.',
      detail: mode === 'centralized'
        ? 'No contact yet. Long relay paths stay quiet until the front line discovers something and everything converges near Overwatch.'
        : 'No contact yet. The local mesh stays short-hop and quiet, ready to absorb contact without waking the whole network.'
    }
  }

  if (latestEvent.type === 'hazard') {
    if (mode === 'centralized') {
      return {
        saturation,
        latency,
        loss,
        pressure,
        pillTone: loss > 35 ? 'danger' : 'warning',
        pillLabel: 'Hazard Escalated',
        state: 'Hazard routed to Overwatch and operator gate.',
        detail: 'A frontline contact is climbing a long relay chain. The architecture turns a local survivability update into network-wide contention.'
      }
    }
    return {
      saturation,
      latency,
      loss,
      pressure,
      pillTone: 'positive',
      pillLabel: 'Local Reroute',
      state: 'Pathfinder burst triggered a local detour.',
      detail: 'Only the nearby scout cluster reacts, so the mesh bends around the hazard without global relay pressure.'
    }
  }

  if (mode === 'centralized') {
    return {
      saturation,
      latency,
      loss,
      pressure,
      pillTone: loss > 32 ? 'danger' : 'warning',
      pillLabel: 'Awaiting Release',
      state: 'Target report is moving through the full approval chain.',
      detail: 'The network is paying for scout-to-overwatch, overwatch-to-operator, and return release traffic before the strike role can act.'
    }
  }

  return {
    saturation,
    latency,
    loss,
    pressure,
    pillTone: 'warning',
    pillLabel: 'Cluster Auction',
    state: 'Scout cluster resolving target ownership locally.',
    detail: 'The target stays local until the final verification burst, which keeps the rest of the network quieter and faster.'
  }
}

const drawScene = (ctx, width, height, mode, noise, events, nowMs) => {
  const baseNodes = buildFormation(width, height)
  const activeEvents = events.filter((event) => nowMs - event.createdAt < EVENT_LIFETIME_MS)
  const eventPoints = activeEvents.map((event) => ({
    ...event,
    x: event.x * width,
    y: event.y * height
  }))
  const nodes = animateNodes(baseNodes, nowMs, noise, eventPoints)
  const edges = buildBaseEdges(nodes, mode)
  const metrics = buildMetrics(mode, noise, events, nowMs)
  const byId = Object.fromEntries(nodes.map((node) => [node.id, node]))
  const pathfinders = nodes.filter((node) => node.role === 'pathfinder')
  const scouts = nodes.filter((node) => node.role === 'scout')
  const overwatch = byId.O1
  const human = byId.H1

  ctx.clearRect(0, 0, width, height)

  const background = ctx.createLinearGradient(0, 0, 0, height)
  background.addColorStop(0, mode === 'centralized' ? '#071019' : '#06111b')
  background.addColorStop(1, '#040811')
  ctx.fillStyle = background
  ctx.fillRect(0, 0, width, height)

  const topGlow = ctx.createRadialGradient(width * 0.2, height * 0.16, 10, width * 0.2, height * 0.16, width * 0.55)
  topGlow.addColorStop(0, mode === 'centralized' ? 'rgba(255, 120, 120, 0.08)' : 'rgba(102, 223, 255, 0.08)')
  topGlow.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = topGlow
  ctx.fillRect(0, 0, width, height)

  ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)'
  ctx.lineWidth = 1
  for (let index = 1; index < 10; index += 1) {
    const x = (width / 10) * index
    const y = (height / 10) * index
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  edges.forEach(([from, to]) => {
    ctx.strokeStyle = mode === 'centralized'
      ? 'rgba(255,255,255,0.08)'
      : 'rgba(102,223,255,0.08)'
    ctx.lineWidth = mode === 'centralized' ? 1.15 : 1
    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
    ctx.stroke()
  })

  eventPoints.forEach((event) => {
    const age = nowMs - event.createdAt
    const progress = clamp(age / EVENT_LIFETIME_MS, 0, 1)
    const alpha = 1 - progress
    const eventX = event.x
    const eventY = event.y
    const baseColor = event.type === 'hazard' ? '#ff627d' : '#ffc96b'

    for (let ring = 0; ring < 2; ring += 1) {
      ctx.strokeStyle = withAlpha(baseColor, 0.22 * alpha)
      ctx.lineWidth = ring === 0 ? 2 : 1.2
      ctx.beginPath()
      ctx.arc(eventX, eventY, 20 + (progress * 110) + ring * 18, 0, Math.PI * 2)
      ctx.stroke()
    }

    ctx.fillStyle = withAlpha(baseColor, 0.16 * alpha)
    ctx.beginPath()
    ctx.arc(eventX, eventY, event.type === 'hazard' ? 26 : 18, 0, Math.PI * 2)
    ctx.fill()

    if (event.type === 'hazard') {
      ctx.strokeStyle = withAlpha(baseColor, 0.9 * alpha)
      ctx.lineWidth = 2.2
      ctx.beginPath()
      ctx.arc(eventX, eventY, 12, 0, Math.PI * 2)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(eventX - 10, eventY)
      ctx.lineTo(eventX + 10, eventY)
      ctx.moveTo(eventX, eventY - 10)
      ctx.lineTo(eventX, eventY + 10)
      ctx.stroke()
    } else {
      ctx.strokeStyle = withAlpha(baseColor, 0.92 * alpha)
      ctx.lineWidth = 2.2
      ctx.beginPath()
      ctx.moveTo(eventX - 12, eventY)
      ctx.lineTo(eventX + 12, eventY)
      ctx.moveTo(eventX, eventY - 12)
      ctx.lineTo(eventX, eventY + 12)
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(eventX, eventY, 10, 0, Math.PI * 2)
      ctx.stroke()
    }

    const discoveryNode = event.type === 'hazard'
      ? pathfinders
        .map((node) => ({ node, d: distance(node, { x: eventX, y: eventY }) }))
        .sort((left, right) => left.d - right.d)[0]?.node
      : scouts
        .map((node) => ({ node, d: distance(node, { x: eventX, y: eventY }) }))
        .sort((left, right) => left.d - right.d)[0]?.node

    const highlightedSegments = []

    if (discoveryNode && mode === 'centralized') {
      highlightedSegments.push([discoveryNode, overwatch, '#8aa2ff', 2.2])
      highlightedSegments.push([overwatch, human, '#ffc96b', 2.4])

      if (event.type === 'hazard') {
        scouts
          .map((node) => ({ node, d: distance(node, { x: eventX, y: eventY }) }))
          .sort((left, right) => left.d - right.d)
          .slice(0, 5)
          .forEach(({ node }) => highlightedSegments.push([overwatch, node, '#ff9662', 2.1]))
      } else {
        const strikeNode = scouts
          .map((node) => ({ node, d: distance(node, { x: eventX, y: eventY }) }))
          .sort((left, right) => left.d - right.d)[0]?.node
        if (strikeNode) {
          highlightedSegments.push([human, overwatch, '#ff627d', 2.2])
          highlightedSegments.push([overwatch, strikeNode, '#ff9662', 2.2])
        }
      }
    }

    if (discoveryNode && mode === 'hierarchical') {
      const nearestScouts = scouts
        .map((node) => ({ node, d: distance(node, { x: eventX, y: eventY }) }))
        .sort((left, right) => left.d - right.d)
        .slice(0, event.type === 'hazard' ? 5 : 6)
        .map((item) => item.node)

      if (event.type === 'hazard') {
        nearestScouts.forEach((node) => highlightedSegments.push([discoveryNode, node, '#8ef5af', 1.8]))
      } else {
        const leader = nearestScouts[0]
        nearestScouts.slice(1).forEach((node) => highlightedSegments.push([node, leader, '#8ef5af', 1.8]))
        if (leader) {
          highlightedSegments.push([leader, overwatch, '#66dfff', 1.9])
          highlightedSegments.push([overwatch, human, '#ffc96b', 1.7])
        }
      }
    }

    highlightedSegments.forEach(([from, to, color, widthPx], index) => {
      ctx.strokeStyle = withAlpha(color, 0.88 * alpha)
      ctx.lineWidth = widthPx
      ctx.beginPath()
      ctx.moveTo(from.x, from.y)
      ctx.lineTo(to.x, to.y)
      ctx.stroke()
      drawSignalPulse(ctx, from, to, color, nowMs, index * 0.19, alpha)
    })
  })

  nodes.forEach((node, index) => {
    const glowAlpha = node.role === 'overwatch' ? 0.2 : 0.14
    ctx.fillStyle = withAlpha(ROLE_COLORS[node.role], glowAlpha)
    ctx.beginPath()
    ctx.arc(node.x, node.y, node.size * (2.45 + Math.sin(nowMs / 700 + index * 0.25) * 0.08), 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = ROLE_COLORS[node.role]
    ctx.strokeStyle = withAlpha(ROLE_COLORS[node.role], 0.7)
    ctx.lineWidth = 1.8

    if (node.role === 'pathfinder') {
      drawTriangle(ctx, node.x, node.y, node.size)
      ctx.fill()
      ctx.stroke()
    } else if (node.role === 'overwatch') {
      drawHexagon(ctx, node.x, node.y, node.size)
      ctx.fill()
      ctx.stroke()
    } else if (node.role === 'human') {
      ctx.beginPath()
      ctx.roundRect(node.x - node.size, node.y - node.size, node.size * 2, node.size * 2, 4)
      ctx.fill()
      ctx.stroke()
    } else {
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.size, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
    }
  })

  return metrics
}

function ComparisonCanvas({ mode, noise, events }) {
  const shellRef = useRef(null)
  const canvasRef = useRef(null)
  const frameRef = useRef(null)
  const [size, setSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const updateSize = (nextWidth, nextHeight) => {
      setSize({
        width: Math.max(320, Math.floor(nextWidth)),
        height: Math.max(420, Math.floor(nextHeight))
      })
    }

    const measure = () => {
      if (!shellRef.current) return
      updateSize(shellRef.current.clientWidth, shellRef.current.clientHeight)
    }

    measure()
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      updateSize(entry.contentRect.width, entry.contentRect.height)
    })
    if (shellRef.current) {
      observer.observe(shellRef.current)
    }
    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [])

  useEffect(() => {
    if (!canvasRef.current || size.width <= 0 || size.height <= 0) return undefined

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = Math.round(size.width * dpr)
    canvas.height = Math.round(size.height * dpr)
    canvas.style.width = `${size.width}px`
    canvas.style.height = `${size.height}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const render = () => {
      const nowMs = Date.now()
      drawScene(ctx, size.width, size.height, mode, noise, events, nowMs)
      frameRef.current = window.requestAnimationFrame(render)
    }

    render()
    return () => {
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current)
      }
    }
  }, [events, mode, noise, size.height, size.width])

  return (
    <div
      ref={shellRef}
      className="relative h-[420px] overflow-hidden rounded-[24px] border border-cyan-500/15 bg-slate-950/95 md:h-[460px] xl:h-[500px]"
    >
      <canvas ref={canvasRef} className="absolute inset-0 block h-full w-full" />
    </div>
  )
}

const getToneClasses = (tone) => {
  if (tone === 'danger') {
    return 'border-rose-400/35 bg-rose-500/10 text-rose-100'
  }
  if (tone === 'warning') {
    return 'border-amber-300/35 bg-amber-400/10 text-amber-100'
  }
  if (tone === 'positive') {
    return 'border-emerald-300/35 bg-emerald-400/10 text-emerald-100'
  }
  return 'border-white/10 bg-white/5 text-slate-100'
}

function TheaterPanel({ mode, title, description, metrics, noise, events }) {
  const pressureLabel = mode === 'centralized'
    ? `${metrics.pressure}%`
    : `${metrics.pressure}% locality`

  return (
    <article className="overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/90 shadow-[0_26px_90px_rgba(0,0,0,0.38)]">
      <div className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-4">
        <div className="space-y-2">
          <h3 className="text-xl font-semibold tracking-tight text-white">{title}</h3>
          <p className="max-w-[38rem] text-sm leading-6 text-slate-400">{description}</p>
        </div>
        <span className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${getToneClasses(metrics.pillTone)}`}>
          {metrics.pillLabel}
        </span>
      </div>

      <div className="space-y-4 p-4">
        <ComparisonCanvas mode={mode} noise={noise} events={events} />

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Network Saturation</div>
            <div className="mt-2 text-2xl font-semibold text-white">{metrics.saturation}%</div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-amber-300 to-rose-400" style={{ width: `${metrics.saturation}%` }} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Command Latency</div>
            <div className="mt-2 text-2xl font-semibold text-white">{metrics.latency} ms</div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-sky-300" style={{ width: `${clamp(Math.round((metrics.latency / 450) * 100), 0, 100)}%` }} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Packet Loss</div>
            <div className="mt-2 text-2xl font-semibold text-white">{metrics.loss}%</div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
              <div className="h-full rounded-full bg-gradient-to-r from-amber-300 to-rose-400" style={{ width: `${metrics.loss}%` }} />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">
              {mode === 'centralized' ? 'Gateway Pressure' : 'Locality Index'}
            </div>
            <div className="mt-2 text-2xl font-semibold text-white">{pressureLabel}</div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
              <div
                className={`h-full rounded-full ${mode === 'centralized' ? 'bg-gradient-to-r from-cyan-300 via-amber-300 to-rose-400' : 'bg-gradient-to-r from-emerald-300 via-cyan-300 to-sky-300'}`}
                style={{ width: `${metrics.pressure}%` }}
              />
            </div>
          </div>

          <div className="md:col-span-2 rounded-2xl border border-white/10 bg-slate-900/80 p-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Mission State</div>
            <div className="mt-2 text-lg font-semibold text-white">{metrics.state}</div>
            <p className="mt-2 text-sm leading-6 text-slate-400">{metrics.detail}</p>
          </div>
        </div>
      </div>
    </article>
  )
}

export default function ContestedRelayComparisonPage() {
  const [noise, setNoise] = useState(35)
  const [events, setEvents] = useState([])
  const [nowMs, setNowMs] = useState(() => Date.now())
  const eventIndexRef = useRef(0)

  const spawnEvent = (type) => {
    const point = EVENT_POSITIONS[eventIndexRef.current % EVENT_POSITIONS.length]
    eventIndexRef.current += 1
    setEvents((current) => [
      ...current.slice(-5),
      {
        id: `${type}-${Date.now()}-${eventIndexRef.current}`,
        type,
        x: point.x,
        y: point.y,
        createdAt: Date.now()
      }
    ])
  }

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNowMs(Date.now())
      setEvents((current) => current.filter((event) => Date.now() - event.createdAt < EVENT_LIFETIME_MS))
    }, 500)
    return () => window.clearInterval(interval)
  }, [])

  const centralizedMetrics = buildMetrics('centralized', noise, events, nowMs)
  const hierarchicalMetrics = buildMetrics('hierarchical', noise, events, nowMs)

  const latestEvent = events.at(-1) || null
  const noiseNarrative = noise < 25
    ? 'Low background noise. Both topologies are stable, so the difference mostly shows up in how much traffic each doctrine generates.'
    : noise < 55
      ? 'Moderate RF clutter. Centralized relay starts to tax the gateway while local clusters still stay manageable.'
      : 'Heavy RF pressure. The centralized side is now paying a serious penalty for every extra climb into Overwatch and operator release.'

  return (
    <main className="space-y-5 p-4 md:p-5">
      <section className="overflow-hidden rounded-[30px] border border-cyan-400/15 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.12),transparent_28%),radial-gradient(circle_at_top_right,rgba(244,114,182,0.08),transparent_24%),linear-gradient(160deg,rgba(2,6,23,0.98),rgba(8,15,27,0.96)_48%,rgba(11,20,34,0.98))] shadow-[0_30px_90px_rgba(0,0,0,0.42)]">
        <div className="grid gap-5 px-5 py-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
          <div className="space-y-4">
            <span className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.22em] text-cyan-100">
              Relay Comparison Lab
            </span>
            <div className="space-y-3">
              <h2 className="max-w-4xl text-3xl font-semibold tracking-tight text-white md:text-[2.35rem]">
                Compare centralized relay doctrine against local autonomous coordination under contested conditions.
              </h2>
              <p className="max-w-4xl text-sm leading-7 text-slate-300">
                This page is about communication doctrine, not just aesthetics. The left panel forces hazard and target events up through Overwatch and the operator gate, while the right panel keeps most routing and auction behavior inside the local scout cluster. It makes the congestion cost of centralized relay loops visible.
              </p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            {SUMMARY_CARDS.map((card) => (
              <div key={card.label} className="rounded-[22px] border border-white/10 bg-slate-950/70 p-4">
                <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">{card.label}</div>
                <div className="mt-2 text-lg font-semibold text-white">{card.value}</div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{card.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/90 shadow-[0_26px_90px_rgba(0,0,0,0.38)]">
        <div className="grid gap-5 p-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-100">Scenario Controls</div>
              <p className="max-w-4xl text-sm leading-7 text-slate-400">
                Mirror the same event into both topologies and watch how much communication work each doctrine creates. The centralized model spends radio budget on long climbs and return approvals. The tiered model contains most behavior locally, then escalates only the final high-value burst.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => spawnEvent('hazard')}
                className="rounded-2xl bg-gradient-to-b from-sky-500 to-cyan-700 px-4 py-3 text-sm font-semibold text-white shadow-[0_14px_40px_rgba(14,165,233,0.24)] transition hover:-translate-y-0.5"
              >
                Spawn Hazard
              </button>
              <button
                type="button"
                onClick={() => spawnEvent('target')}
                className="rounded-2xl bg-gradient-to-b from-violet-500 to-indigo-700 px-4 py-3 text-sm font-semibold text-white shadow-[0_14px_40px_rgba(99,102,241,0.24)] transition hover:-translate-y-0.5"
              >
                Spawn Target
              </button>
              <button
                type="button"
                onClick={() => setEvents([])}
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-slate-100 transition hover:-translate-y-0.5 hover:bg-white/10"
              >
                Reset Theater
              </button>
            </div>

            <div className="rounded-[24px] border border-cyan-400/15 bg-slate-900/70 p-4">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Background RF Noise</div>
                  <div className="text-2xl font-semibold text-white">{noise}%</div>
                  <p className="max-w-3xl text-sm leading-6 text-slate-400">{noiseNarrative}</p>
                </div>
                {latestEvent && (
                  <div className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${latestEvent.type === 'hazard' ? getToneClasses('danger') : getToneClasses('warning')}`}>
                    Last Event: {latestEvent.type}
                  </div>
                )}
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={noise}
                onChange={(event) => setNoise(Number(event.target.value))}
                className="mt-4 w-full accent-cyan-300"
              />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            {NOTE_CARDS.map((note) => (
              <div key={note.title} className="rounded-[22px] border border-white/10 bg-slate-950/70 p-4">
                <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-100">{note.title}</div>
                <p className="mt-2 text-sm leading-6 text-slate-400">{note.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <TheaterPanel
          mode="centralized"
          title="Centralized Relay Chain"
          description="Every hazard report and target decision climbs into Overwatch and the operator release loop. The doctrine creates long global relay paths and heats up the gateway."
          metrics={centralizedMetrics}
          noise={noise}
          events={events}
        />

        <TheaterPanel
          mode="hierarchical"
          title="Tiered Local Autonomy"
          description="Pathfinders warn locally, scouts coordinate locally, and Overwatch only joins when the final authorization burst is actually necessary."
          metrics={hierarchicalMetrics}
          noise={noise}
          events={events}
        />
      </section>

      <p className="px-1 text-sm leading-6 text-slate-400">
        Visual language: cyan triangles are pathfinders, green circles are scouts, amber hex is Overwatch, and the white square is the operator tablet. Red hazard rings and amber target markers are mirrored into both panels so the comparison stays focused on communication doctrine rather than scenario differences.
      </p>
    </main>
  )
}
