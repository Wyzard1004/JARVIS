import React, { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

/**
 * SwarmGraph Component (4.4.0 - Grid & Spanning Tree)
 * 
 * Visualizes the swarm topology using D3 force simulation with:
 * - Full Grid Display: Nodes anchored to their grid positions, not centered
 * - Spanning Tree Visualization: Only shows edges used in gossip propagation
 * - 3D Topological Layers: Visual hierarchy by altitude (data-ready for 3D):
 *   * Sky Layer: Compute drones fly high (z=100)
 *   * Mid Layers: Gateway & Soldiers at z=20-80
 *   * Ground Layer: Recon & Attack drones close to ground (z<10)
 * - Color-Coded Drones: Each type has distinct color for fast identification
 * - Smooth Animation: Nodes move naturally without jumping or flickering
 */

function SwarmGraph({ state }) {
  const svgRef = useRef()
  const simulationRef = useRef()
  const svgElementsRef = useRef(null)  // Store SVG selections for reuse
  const [propagationTimings, setPropagationTimings] = useState({})
  const [currentTime, setCurrentTime] = useState(0)
  const propagationOrder = state?.data?.propagation_order || state?.propagation_order || []
  const targetX = state?.target_x ?? state?.data?.target_x ?? 0
  const targetY = state?.target_y ?? state?.data?.target_y ?? 0
  const activeNodes = new Set(state?.active_nodes || state?.data?.active_nodes || [])
  const enemies = state?.enemies || state?.data?.enemies || []
  const signalAnimations = state?.signal_animations || state?.data?.signal_animations || []

  // Handle propagation animation timing separately
  useEffect(() => {
    // Build propagation timing map for pulse animation
    if (propagationOrder.length > 0) {
      const timings = {}
      propagationOrder.forEach(event => {
        timings[event.node] = event.timestamp_ms
      })
      setPropagationTimings(timings)
      
      // Start animation timer
      const startTime = Date.now()
      const interval = setInterval(() => {
        const elapsed = Date.now() - startTime
        setCurrentTime(elapsed)
      }, 50)
      
      return () => clearInterval(interval)
    }
    setPropagationTimings({})
    setCurrentTime(0)
  }, [propagationOrder])

  // Initialize and update the D3 visualization (preserving elements, not clearing)
  useEffect(() => {
    if (!svgRef.current) return

    const nodes = (state?.nodes || []).map(node => ({
      id: node.id,
      status: node.status,
      drone_type: node.drone_type || 'unknown',
      role: node.role,
      x: node.x,
      y: node.y,
      homeX: node.x,
      homeY: node.y
    }))

    const links = (state?.edges || []).map(edge => ({
      source: edge.source,
      target: edge.target
    }))

    const width = 1000
    const height = 600
    const missionX = (width / 2) + targetX
    const missionY = (height / 2) + targetY

    const svg = d3.select(svgRef.current)

    // FIRST TIME SETUP: Only initialize SVG structure once
    if (svgElementsRef.current === null) {
      svgRef.current.setAttribute('width', width)
      svgRef.current.setAttribute('height', height)
      svgRef.current.setAttribute('viewBox', [0, 0, width, height])

      // Create force simulation once
      const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(60))
        .force('charge', d3.forceManyBody().strength(-100))  // Reduced to let anchor forces dominate
        // Remove center force completely - let nodes stay at grid positions
        .force(
          'grid-x',
          d3.forceX(d => d.homeX).strength(0.8)  // Strong anchor to home X position
        )
        .force(
          'grid-y',
          d3.forceY(d => d.homeY).strength(0.8)  // Strong anchor to home Y position
        )
        .force(
          'mission-x',
          d3.forceX(d => {
            if (d.role === 'gateway' || d.drone_type === 'compute') return d.homeX
            return activeNodes.has(d.id) ? missionX : d.homeX
          }).strength(d => {
            if (d.role === 'gateway' || d.drone_type === 'compute') return 0.2
            return activeNodes.has(d.id) ? 0.3 : 0.05
          })
        )
        .force(
          'mission-y',
          d3.forceY(d => {
            if (d.role === 'gateway' || d.drone_type === 'compute') return d.homeY
            return activeNodes.has(d.id) ? missionY : d.homeY
          }).strength(d => {
            if (d.role === 'gateway' || d.drone_type === 'compute') return 0.2
            return activeNodes.has(d.id) ? 0.3 : 0.05
          })
        )

      simulationRef.current = simulation

      // SPANNING TREE FILTERING: Build set of edges used in first-time propagation
      // Only show edges that were part of the gossip spanning tree (not all 104 edges)
      const spanningTreeEdges = new Set()
      const visitedInPropagation = new Set()
      
      if (propagationOrder && propagationOrder.length > 0) {
        propagationOrder.forEach((event, idx) => {
          const currentNode = event.node
          // Find which node sent to this one (previous in order, if in active_nodes)
          if (idx > 0) {
            // Look back for the first node that sent to current
            for (let i = idx - 1; i >= 0; i--) {
              const prevNode = propagationOrder[i].node
              // Create edge identifier (symmetric for undirected graph)
              const edgeKey = [currentNode, prevNode].sort().join('|')
              spanningTreeEdges.add(edgeKey)
              break  // Only connect to direct predecessor (spanning tree property)
            }
          }
          visitedInPropagation.add(currentNode)
        })
      }
      
      // Filter links to only show spanning tree edges
      const spanningTreeLinks = links.filter(link => {
        const edgeKey = [link.source, link.target].sort().join('|')
        return spanningTreeEdges.has(edgeKey)
      })

      // Add 3D layer information (z-coordinate) for topological visualization
      // This prepares for future 3D visualization
      nodes.forEach(node => {
        if (node.drone_type === 'compute') {
          node.z = 100  // High in sky
        } else if (node.drone_type === 'gateway') {
          node.z = 80   // Mid-high (base station)
        } else if (node.drone_type === 'soldier') {
          node.z = 20   // Slightly elevated (operator position)
        } else if (node.drone_type === 'recon') {
          node.z = 10   // Close to ground
        } else if (node.drone_type === 'attack') {
          node.z = 5    // Very close to ground (tactical position)
        } else {
          node.z = 0
        }
      })

      // Create links with enter/update/exit pattern (spanning tree only)
      const linkGroup = svg.selectAll('.link-group')
        .data(spanningTreeLinks, (d, i) => i)
        .join(
          enter => enter.append('g')
            .attr('class', 'link-group')
            .append('line')
            .attr('class', 'link-line')
            .attr('stroke', '#4B5563')
            .attr('stroke-width', 2)
            .attr('opacity', 0.3)  // Visible for spanning tree edges
        )

      // Create nodes with enter/update/exit pattern (with 3D layer information)
      const nodeGroup = svg.selectAll('.node-group')
        .data(nodes, d => d.id)
        .join(
          enter => enter.append('g')
            .attr('class', 'node-group')
            .call(drag(simulation))
            .append('circle')
            .attr('r', d => {
              // Larger nodes for drones higher in the sky (visual hierarchy)
              if (d.drone_type === 'compute') return 12
              if (d.drone_type === 'gateway') return 11
              if (d.drone_type === 'soldier') return 10
              return 8
            })
            .attr('fill', d => {
              if (d.drone_type === 'compute') return '#06B6D4'  // Cyan - high altitude
              if (d.drone_type === 'gateway') return '#A855F7'  // Purple - base station
              if (d.drone_type === 'soldier') return '#FB923C'  // Orange - operators
              if (d.drone_type === 'attack') return '#EF4444'   // Red - tactical
              if (d.drone_type === 'recon') return '#22C55E'    // Green - scout
              return '#6B7280'  // Gray - unknown
            })
            .attr('opacity', d => {
              // Higher altitude = more opaque, lower altitude = slightly transparent (depth cue)
              return 0.7 + (d.z / 100) * 0.3
            })
        )

      // Create pulse circles
      const pulseGroup = svg.selectAll('.pulse')
        .data(nodes.filter(d => propagationTimings[d.id] !== undefined), d => d.id)
        .join(
          enter => enter.append('circle')
            .attr('class', 'pulse')
            .attr('r', 8)
            .attr('fill', 'none')
            .attr('stroke', '#EF4444')
            .attr('stroke-width', 2)
        )

      // Create labels
      const labelGroup = svg.selectAll('text')
        .data(nodes, d => d.id)
        .join(
          enter => enter.append('text')
            .attr('font-size', '12px')
            .attr('fill', '#D1D5DB')
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .text(d => d.id)
        )

      // Store selections for updates
      svgElementsRef.current = {
        simulation,
        linkGroup,
        nodeGroup,
        pulseGroup,
        labelGroup,
        nodes,
        links
      }

      // Set up tick handler
      simulation.on('tick', () => updatePositions())
    } else {
      // UPDATE EXISTING VISUALIZATION
      const { simulation, linkGroup, nodeGroup, pulseGroup, labelGroup } = svgElementsRef.current
      
      // Update node colors based on propagation timing and drone type
      nodeGroup.select('circle')
        .attr('fill', d => {
          // Pulse effect during propagation
          if (propagationTimings[d.id] !== undefined) {
            const nodeTime = propagationTimings[d.id]
            const timeSinceEvent = currentTime - nodeTime
            if (timeSinceEvent >= 0 && timeSinceEvent < 200) {
              const isInPulse = (timeSinceEvent % 100) < 50
              return isInPulse ? '#FCA5A5' : '#FFFFFF'
            }
          }
          
          // Offline nodes stay gray
          if (d.status === 'offline') return '#374151'
          
          // Use drone-type colors
          if (d.drone_type === 'compute') return '#06B6D4'  // Cyan
          if (d.drone_type === 'gateway') return '#A855F7'  // Purple
          if (d.drone_type === 'soldier') return '#FB923C'  // Orange
          if (d.drone_type === 'attack') return '#EF4444'   // Red
          if (d.drone_type === 'recon') return '#22C55E'    // Green
          return '#6B7280'  // Gray - unknown
        })

      // Update pulse opacity
      pulseGroup
        .attr('opacity', d => {
          const nodeTime = propagationTimings[d.id]
          const timeSinceEvent = currentTime - nodeTime
          if (timeSinceEvent >= 0 && timeSinceEvent < 400) {
            return 1 - (timeSinceEvent / 400)
          }
          return 0
        })

      // Update link opacity based on active signals
      const activeSignalEdges = new Set()
      signalAnimations.forEach(sig => {
        const edgeIndex = links.findIndex(l =>
          (l.source === sig.from_node && l.target === sig.to_node) ||
          (l.source === sig.to_node && l.target === sig.from_node)
        )
        if (edgeIndex >= 0) activeSignalEdges.add(edgeIndex)
      })

      linkGroup.select('.link-line')
        .attr('opacity', (d, i) => activeSignalEdges.has(i) ? 0.6 : 0)
    }

    function updatePositions() {
      if (!svgElementsRef.current) return
      const { linkGroup, nodeGroup, pulseGroup, labelGroup } = svgElementsRef.current
      const { links } = svgElementsRef.current

      linkGroup.select('.link-line')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      nodeGroup
        .attr('transform', d => `translate(${d.x},${d.y})`)

      pulseGroup
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)

      labelGroup
        .attr('x', d => d.x)
        .attr('y', d => d.y)
    }

    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop()
      }
    }
  }, [state, propagationTimings, currentTime])  // Update when state, timings, or time changes

  function drag(simulation) {
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    }

    function dragged(event, d) {
      d.fx = event.x
      d.fy = event.y
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    }

    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
  }

  return (
    <div className="w-full bg-gray-900 rounded overflow-hidden">
      <div style={{ width: '100%', height: '600px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
      </div>
      
      {/* Layer and Drone Type Legend */}
      <div className="bg-gray-800 border-t border-gray-700 p-3 text-xs text-gray-300">
        <div className="grid grid-cols-3 gap-4">
          {/* Drone Types Column */}
          <div>
            <p className="font-bold mb-2 text-blue-400">🚁 Drone Types</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-cyan-400"></div>
                <span>Compute (Processors)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-purple-500"></div>
                <span>Gateway (Base)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-orange-400"></div>
                <span>Soldiers (Ops)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-green-500"></div>
                <span>Recon (Scouts)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-red-500"></div>
                <span>Attack (Tactical)</span>
              </div>
            </div>
          </div>

          {/* Layer Heights Column */}
          <div>
            <p className="font-bold mb-2 text-purple-400">📊 Topological Layers</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-cyan-400">●●●</span>
                <span>Sky Layer (z=100)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-purple-400">●●</span>
                <span>Mid Layer (z=20-80)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-red-400">●</span>
                <span>Ground Layer (z≤10)</span>
              </div>
              <p className="text-gray-500 mt-2 text-xs">Larger nodes = higher altitude</p>
            </div>
          </div>

          {/* Spanning Tree Column */}
          <div>
            <p className="font-bold mb-2 text-green-400">🌳 Network Status</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-4 bg-gray-500"></div>
                <span>Spanning Tree Edge</span>
              </div>
              <p className="text-gray-500 mt-2">Only edges from gossip propagation are shown</p>
              <p className="text-gray-500 text-xs">Duplicate messages ignored (spanning tree property)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SwarmGraph
