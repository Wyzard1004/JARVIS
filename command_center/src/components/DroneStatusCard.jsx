/**
 * DroneStatusCard Component
 * 
 * Displays detailed status for a selected drone:
 * - Current position and grid cell
 * - Behavior (Lurk/Patrol/Transit)
 * - Health, fuel, and transmission status
 * - Next waypoint (if patrolling)
 */

import React from 'react'

const NATO_PHONETIC = [
  'Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot',
  'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima',
  'Mike', 'November', 'Oscar', 'Papa', 'Quebec', 'Romeo',
  'Sierra', 'Tango', 'Uniform', 'Victor', 'Whiskey', 'X-ray',
  'Yankee', 'Zulu'
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

function DroneStatusCard({ drone, commsStatus = 'online' }) {
  if (!drone) {
    return (
      <div className="w-full p-4 bg-gray-700 border border-gray-600 rounded text-center text-gray-400">
        Select a drone to view details
      </div>
    )
  }

  // Format grid position with exact coordinates
  const gridString = drone.grid_position
    ? `${NATO_PHONETIC[drone.grid_position[0]]}-${drone.grid_position[1] + 1}`
    : 'Unknown'
  
  // Battery level (random for aesthetic)
  const battery = Math.floor(Math.random() * 30) + 70

  // Comms status indicator
  const getCommsColor = () => {
    return commsStatus === 'online' ? 'text-green-400' : 'text-red-400'
  }

  // Get transmission range based on drone type
  const getTransmissionRange = () => {
    const rangeMap = {
      soldier: '5 cells',
      compute: '12 cells',
      recon: '3 cells',
      attack: '3 cells'
    }
    return rangeMap[drone.type] || 'Unknown'
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
        <div className="font-mono text-sm text-gray-200 mt-1">{gridString}</div>
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
          Range: {getTransmissionRange()}
        </div>
      </div>

      {/* Next Waypoint (if patrolling) */}
      {drone.behavior === 'patrol' && drone.next_waypoint && (
        <div className="bg-gray-600 p-2 rounded border border-gray-500">
          <div className="text-xs text-gray-300 font-bold mb-1">NEXT WAYPOINT</div>
          <div className="font-mono text-sm text-gray-200">
            {NATO_PHONETIC[drone.next_waypoint[0]]}-{drone.next_waypoint[1] + 1}
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
