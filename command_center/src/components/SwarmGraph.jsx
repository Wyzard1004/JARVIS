import React, { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

/**
 * SwarmGraph Component (4.2.2 & 4.3.1)
 * 
 * Visualizes the swarm topology using D3 force simulation.
 * Maps WebSocket updates to node/link positions.
 * Animates when nodes move toward target coordinates.
 * Pulses nodes when they receive gossip commands.
 */

function SwarmGraph({ state }) {
  const svgRef = useRef()
  const simulationRef = useRef()
  const [propagationTimings, setPropagationTimings] = useState({})
  const [currentTime, setCurrentTime] = useState(0)

  useEffect(() => {
    if (!svgRef.current) return

    // Build propagation timing map for pulse animation
    if (state?.data?.propagation_order) {
      const timings = {}
      state.data.propagation_order.forEach(event => {
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
  }, [state?.data?.propagation_order])

  useEffect(() => {
    if (!svgRef.current) return

    const nodes = (state?.nodes || []).map(node => ({
      id: node.id,
      status: node.status,
      x: node.x,
      y: node.y
    }))

    const links = (state?.edges || []).map(edge => ({
      source: edge.source,
      target: edge.target
    }))

    const width = 800
    const height = 384

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove()

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))

    simulationRef.current = simulation

    // Draw links
    const link = svg.selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', '#4B5563')
      .attr('stroke-width', 2)

    // Draw nodes
    const node = svg.selectAll('circle')
      .data(nodes, d => d.id)
      .enter()
      .append('circle')
      .attr('r', 8)
      .attr('fill', d => {
        // Pulse effect: nodes pulse red during propagation window
        if (propagationTimings[d.id] !== undefined) {
          const nodeTime = propagationTimings[d.id]
          const timeSinceEvent = currentTime - nodeTime
          
          // Pulse for 200ms after event
          if (timeSinceEvent >= 0 && timeSinceEvent < 200) {
            const pulseFraction = (timeSinceEvent % 100) / 100
            const isInPulse = (timeSinceEvent % 100) < 50
            return isInPulse ? '#FCA5A5' : '#EF4444'
          }
        }
        
        return d.status === 'active' ? '#EF4444' : '#6B7280'
      })
      .call(drag(simulation))

    // Draw pulse circles for animation
    const pulseCircles = svg.selectAll('.pulse')
      .data(nodes.filter(d => propagationTimings[d.id] !== undefined))
      .enter()
      .append('circle')
      .attr('class', 'pulse')
      .attr('r', 8)
      .attr('fill', 'none')
      .attr('stroke', '#EF4444')
      .attr('stroke-width', 2)
      .attr('opacity', d => {
        const nodeTime = propagationTimings[d.id]
        const timeSinceEvent = currentTime - nodeTime
        
        if (timeSinceEvent >= 0 && timeSinceEvent < 400) {
          // Fade out after 400ms
          return 1 - (timeSinceEvent / 400)
        }
        return 0
      })

    // Draw labels
    const labels = svg.selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .attr('x', 0)
      .attr('y', 0)
      .attr('font-size', '12px')
      .attr('fill', '#D1D5DB')
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .text(d => d.id)

    // Update positions on each simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      node
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)

      pulseCircles
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)

      labels
        .attr('x', d => d.x)
        .attr('y', d => d.y)
    })

    return () => simulation.stop()
  }, [state, currentTime, propagationTimings])

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
    <div className="w-full h-96 bg-gray-900 rounded flex items-center justify-center overflow-hidden">
      <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}

export default SwarmGraph
