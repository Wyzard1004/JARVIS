import React, { useState } from 'react'

const SOLDIER_ACCENTS = [
  'bg-orange-500',
  'bg-blue-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-rose-500'
]

/**
 * Soldier Selector Component
 * 
 * Provides UI for selecting which soldier operator to control.
 * Shows current soldier status and available commands.
 */
function SoldierSelector({ activeSoldier, availableSoldiers = [], onSoldierChange, soldierStatus }) {
  const [showStatus, setShowStatus] = useState(false)

  const soldiers = (availableSoldiers.length > 0 ? availableSoldiers : [
    { id: 'soldier-1', label: 'Soldier 1' },
    { id: 'soldier-2', label: 'Soldier 2' }
  ]).map((soldier, index) => ({
    ...soldier,
    color: SOLDIER_ACCENTS[index % SOLDIER_ACCENTS.length]
  }))
  
  const getStatusColor = (status) => {
    if (!status) return "text-gray-500"
    if (status.status === "online") return "text-green-500"
    if (status.status === "busy") return "text-yellow-500"
    return "text-red-500"
  }
  
  const getStatusIcon = (status) => {
    if (!status) return "○"
    if (status.status === "online") return "●"
    if (status.status === "busy") return "◐"
    return "✕"
  }

  const activeSoldierLabel = soldiers.find((soldier) => soldier.id === activeSoldier)?.label || 'Unknown Soldier'

  return (
    <div className="soldier-selector w-full bg-gray-900 border border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Soldier Control</h3>
        <button
          onClick={() => setShowStatus(!showStatus)}
          className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
        >
          {showStatus ? "Hide Status" : "Show Status"}
        </button>
      </div>

      {/* Soldier Selection Buttons */}
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between gap-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
          <span>Operators</span>
          <span>{soldiers.length} Available</span>
        </div>
        <div className="max-w-full overflow-x-auto rounded-lg border border-gray-700 bg-gray-950/60 p-2">
          <div className="flex w-max min-w-full gap-2">
            {soldiers.map((soldier) => (
              <button
                key={soldier.id}
                onClick={() => onSoldierChange(soldier.id)}
                className={`
                  w-40 shrink-0 rounded-lg border px-3 py-2 text-left font-semibold transition-all
                  ${activeSoldier === soldier.id
                    ? `${soldier.color} border-transparent text-white shadow-lg`
                    : "border-gray-700 bg-gray-700 text-gray-300 hover:bg-gray-600"
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${
                    activeSoldier === soldier.id ? "bg-white" : "bg-gray-500"
                  }`}></span>
                  <span className="truncate">{soldier.label}</span>
                </div>
                <div className={`mt-1 text-[10px] uppercase tracking-[0.16em] ${
                  activeSoldier === soldier.id ? "text-white/80" : "text-gray-400"
                }`}>
                  {soldier.id}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Status Display */}
      {showStatus && soldierStatus && (
        <div className="bg-gray-800 border border-gray-600 rounded p-3 text-sm text-gray-300">
          <div className="mb-2 grid gap-2 sm:grid-cols-2">
            <div>
              <span className="text-gray-400">Status:</span>
              <span className={`ml-2 font-semibold ${getStatusColor(soldierStatus)}`}>
                {getStatusIcon(soldierStatus)} {soldierStatus.status || "unknown"}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Selected Soldier:</span>
              <span className="ml-2 text-cyan-400">{activeSoldierLabel}</span>
            </div>
          </div>
          
          {soldierStatus.pending_commands && (
            <div>
              <span className="text-gray-400">Pending Commands:</span>
              <span className="ml-2 font-semibold">{soldierStatus.pending_commands}</span>
            </div>
          )}
          
          {soldierStatus.last_mission && (
            <div className="mt-2 border-t border-gray-600 pt-2">
              <span className="text-gray-400">Last Mission:</span>
              <div className="text-cyan-300 font-mono text-xs mt-1">
                {soldierStatus.last_mission}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Command Hints */}
      <div className="mt-4 bg-gray-800 border border-gray-600 rounded p-3 text-xs text-gray-400">
        <div className="font-semibold text-gray-300 mb-2">Voice Commands:</div>
        <div className="space-y-1">
          <div>→ <span className="text-cyan-400">"Scan Grid Echo 5"</span> - Send recon drones to scan an area</div>
          <div>→ <span className="text-red-400">"Attack Grid Echo 5"</span> - Stage a strike on a confirmed target</div>
          <div>→ <span className="text-yellow-400">"Execute"</span> - Approve a pending attack command</div>
          <div>→ <span className="text-emerald-400">"Review reports"</span> - Summarize current reports without retasking the swarm</div>
          <div>→ <span className="text-orange-400">"End attack mission"</span> - Abort an active attack mission and clear the mission banner</div>
        </div>
        <div className="mt-3 border-t border-gray-700 pt-2 text-[11px] text-gray-500">
          Detailed outcomes remain visible in <span className="text-gray-300">Mission Events</span> and <span className="text-gray-300">Recent Commands</span>.
        </div>
      </div>
    </div>
  )
}

export default SoldierSelector
