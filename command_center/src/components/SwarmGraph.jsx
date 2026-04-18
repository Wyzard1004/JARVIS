import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'

/**
 * SwarmGraph Component (4.2.2)
 * 
 * Visualizes the swarm topology using D3 force simulation.
 * Maps WebSocket updates to node/link positions.
 * Animates when nodes move toward target coordinates.
 */

function SwarmGraph({ state }) {
  const svgRef = useRef()
  const simulationRef = useRef()

  useEffect(() => {
    if (!svgRef.current) return

    const nodes = (state?.nodes || []).map(node => ({
      id: node.id,
      status: node.status
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
      .data(nodes)
      .enter()
      .append('circle')
      .attr('r', 8)
      .attr('fill', d => d.status === 'active' ? '#EF4444' : '#6B7280')
      .call(drag(simulation))

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
        .attr('fill', d => d.status === 'active' ? '#EF4444' : '#6B7280')

      labels
        .attr('x', d => d.x)
        .attr('y', d => d.y)
    })

    return () => simulation.stop()
  }, [state])

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
