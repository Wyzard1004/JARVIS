import React, { useState, useEffect } from 'react'

/**
 * Soldier Selector Component
 * 
 * Provides UI for selecting which soldier operator to control.
 * Shows current soldier status and available commands.
 */
function SoldierSelector({ activeSoldier, onSoldierChange, soldierStatus }) {
  const [showStatus, setShowStatus] = useState(false)
  
  const soldiers = [
    { id: "soldier-1", label: "Soldier 1", color: "bg-orange-500" },
    { id: "soldier-2", label: "Soldier 2", color: "bg-blue-500" }
  ]
  
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

  const activeSoldierLabel = soldiers.find((soldier) => soldier.id === activeSoldier)?.label || "Unknown Soldier"

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
      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        {soldiers.map(soldier => (
          <button
            key={soldier.id}
            onClick={() => onSoldierChange(soldier.id)}
            className={`
              flex-1 py-2 px-3 rounded-lg font-semibold transition-all
              ${activeSoldier === soldier.id
                ? `${soldier.color} text-white shadow-lg scale-105`
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }
            `}
          >
            <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
              activeSoldier === soldier.id ? "bg-white" : "bg-gray-500"
            }`}></span>
            {soldier.label}
          </button>
        ))}
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
        <div className="font-semibold text-gray-300 mb-2">Available Commands:</div>
        <div className="space-y-1">
          <div>→ <span className="text-cyan-400">Request Recon</span> - Send recon drones to scan area</div>
          <div>→ <span className="text-red-400">Request Attack</span> - Authorize strike on confirmed target</div>
          <div>→ <span className="text-yellow-400">Approve Command</span> - Authorize pending operations</div>
          <div>→ <span className="text-green-400">Process Reports</span> - Review mission outcomes</div>
        </div>
      </div>
    </div>
  )
}

export default SoldierSelector
