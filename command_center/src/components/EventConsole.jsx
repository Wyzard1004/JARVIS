/**
 * EventConsole Component
 * 
 * Scrollable, time-stamped mission event feed.
 * Auto-scrolls to newest events but does not auto-clear.
 * Color-coded by event severity.
 */

import React, { useEffect, useRef } from 'react'

const SEVERITY_COLORS = {
  info: 'bg-blue-900 text-blue-200 border-blue-700',
  warning: 'bg-yellow-900 text-yellow-200 border-yellow-700',
  critical: 'bg-red-900 text-red-200 border-red-700',
  alert: 'bg-red-800 text-red-100 border-red-600'
}

const SEVERITY_BADGE = {
  info: 'bg-blue-700 text-blue-200',
  warning: 'bg-yellow-700 text-yellow-200',
  critical: 'bg-red-700 text-red-200',
  alert: 'bg-red-600 text-red-100'
}

function EventConsole({ events = [], maxVisible = 20 }) {
  const consoleEndRef = useRef(null)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  // Format timestamp to HH:MM:SS.mmm
  const formatTime = (timestamp_ms) => {
    const totalSecs = Math.floor(timestamp_ms / 1000)
    const mins = Math.floor(totalSecs / 60)
    const secs = totalSecs % 60
    const ms = timestamp_ms % 1000

    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
  }

  // Get display color for severity
  const getSeverityColor = (severity) => {
    return SEVERITY_COLORS[severity] || SEVERITY_COLORS.info
  }

  const getSeverityBadge = (severity) => {
    return SEVERITY_BADGE[severity] || SEVERITY_BADGE.info
  }

  // Show only most recent events
  const visibleEvents = events.slice(-maxVisible)

  return (
    <div className="w-full h-full border border-gray-600 bg-gray-700 rounded">
      {/* Header */}
      <div className="bg-gray-800 text-white px-4 py-2 font-bold text-sm border-b border-gray-600">
        Mission Events ({events.length} total)
      </div>

      {/* Event List */}
      <div className="overflow-y-auto h-80 font-mono text-xs">
        {visibleEvents.length === 0 ? (
          <div className="p-4 text-gray-400 text-center">
            No events yet...
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {visibleEvents.map((event, idx) => (
              <div
                key={idx}
                className={`p-2 border-l-4 rounded ${getSeverityColor(event.severity)}`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1">
                    <div className="flex gap-2 items-center">
                      <span className="font-bold">[{formatTime(event.timestamp_ms)}]</span>
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${getSeverityBadge(event.severity)}`}>
                        {event.severity.toUpperCase().substring(0, 3)}
                      </span>
                    </div>
                    <div className="mt-1 break-words">
                      {event.message}
                    </div>
                    {event.entity_id && (
                      <div className="text-xs opacity-75 mt-1">
                        Entity: {event.entity_id} ({event.entity_type})
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="bg-gray-100 border-t border-gray-400 px-4 py-2 text-xs text-gray-600">
        <div className="flex justify-between">
          <span>Showing {visibleEvents.length} of {events.length} events</span>
          <span>
            Critical: {events.filter(e => e.severity === 'critical').length} |
            Warning: {events.filter(e => e.severity === 'warning').length}
          </span>
        </div>
      </div>
    </div>
  )
}

export default EventConsole
