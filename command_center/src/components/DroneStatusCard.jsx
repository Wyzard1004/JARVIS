/**
 * DroneStatusCard Component
 * 
 * Displays detailed status for a selected drone:
 * - Current position and 8x8 display sector
 * - Behavior (Lurk/Patrol/Transit)
 * - Health, fuel, and transmission status
 * - Next waypoint (if patrolling)
 */

import React from 'react'

const NATO_PHONETIC = [
  'Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel'
]

const BEHAVIOR_ICONS = {
  lurk: '🛡️',
  patrol: '🔄',
  transit: '➡️',
  swarm: '🐝'
}

const BEHAVIOR_LABELS = {
  lurk: 'Lurking',
  patrol: 'Patrolling',
  transit: 'Transiting',
  swarm: 'Swarming'
}

function DroneStatusCard({ drone, commsStatus = 'online', batteryLevels = {} }) {
  if (!drone) {
    return (
      <div className="w-full p-4 bg-gray-700 border border-gray-600 rounded text-center text-gray-400">
        Select a drone to view details
      </div>
    )
  }

  // Get persistent battery level for this drone
  const battery = batteryLevels[drone.id] || 75

  const position = Array.isArray(drone.position) ? drone.position : null
  const formatSector = (point) => {
    if (!Array.isArray(point) || point.length !== 2) return 'Unknown'
    const col = Math.max(0, Math.min(7, Math.floor(point[0] / 125)))
    const row = Math.max(0, Math.min(7, Math.floor(point[1] / 125)))
    return `${NATO_PHONETIC[row]}-${col + 1}`
  }
  const sectorString = formatSector(position)
  const coordinateString = position
    ? `${Math.round(position[0])}, ${Math.round(position[1])}`
    : 'Unknown'

  // Comms status indicator
  const getCommsColor = () => {
    return commsStatus === 'online' ? 'text-green-400' : 'text-red-400'
  }

  const getTransmissionRange = () => {
    if (typeof drone.transmission_range !== 'number') return 'Unknown'
    return `${drone.transmission_range.toFixed(0)}u`
  }

  return (
    <div className="w-full p-4 bg-gray-700 border border-gray-600 rounded space-y-3">
      {/* Header with drone ID and type */}
      <div className="border-b border-gray-600 pb-3">
        <h3 className="font-bold text-lg text-gray-100">{drone.id}</h3>
        <p className="text-xs text-gray-400 capitalize">{drone.type} Drone</p>
      </div>

      {/* Position */}
      <div>
        <div className="text-xs text-gray-400 font-bold">POSITION</div>
        <div className="font-mono text-sm text-gray-200 mt-1">{sectorString}</div>
        <div className="text-xs text-gray-400 mt-1">World: {coordinateString}</div>
      </div>

      {/* Behavior */}
      <div>
        <div className="text-xs text-gray-400 font-bold">BEHAVIOR</div>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-lg">{BEHAVIOR_ICONS[drone.behavior] || '❓'}</span>
          <span className="font-mono text-sm text-gray-200 capitalize">
            {BEHAVIOR_LABELS[drone.behavior] || drone.behavior}
          </span>
        </div>
      </div>

      {/* Battery Level */}
      <div>
        <div className="flex justify-between items-center text-xs text-gray-400 font-bold mb-1">
          <span>BATTERY</span>
          <span className="text-sm font-mono text-gray-200">{battery}%</span>
        </div>
        <div className="w-full bg-gray-600 rounded-full h-2 overflow-hidden">
          <div
            className="bg-green-500 h-full transition-all"
            style={{ width: `${battery}%` }}
          />
        </div>
      </div>

      {/* Communications Status */}
      <div>
        <div className="text-xs text-gray-400 font-bold">COMMS</div>
        <div className={`mt-1 font-mono text-sm font-bold ${getCommsColor()}`}>
          ● {commsStatus.toUpperCase()}
        </div>
        <div className="text-xs text-gray-400 mt-1">
          Range: {getTransmissionRange()} ({typeof drone.transmission_range === 'number' ? `${(drone.transmission_range / 125).toFixed(1)} sectors` : 'n/a'})
        </div>
      </div>

      {/* Next Waypoint (if patrolling) */}
      {drone.behavior === 'patrol' && drone.next_waypoint && (
        <div className="bg-gray-600 p-2 rounded border border-gray-500">
          <div className="text-xs text-gray-300 font-bold mb-1">NEXT WAYPOINT</div>
          <div className="font-mono text-sm text-gray-200">
            {formatSector(drone.next_waypoint)}
          </div>
        </div>
      )}

      {/* Actions Bar */}
      <div className="pt-2 border-t border-gray-600 flex gap-2">
        <button className="flex-1 px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded transition">
          Details
        </button>
        <button className="flex-1 px-2 py-1.5 bg-gray-600 hover:bg-gray-500 text-gray-100 text-xs font-bold rounded transition">
          Command
        </button>
      </div>
    </div>
  )
}

export default DroneStatusCard
