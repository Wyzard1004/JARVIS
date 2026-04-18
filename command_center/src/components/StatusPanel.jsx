import React from 'react'

/**
 * StatusPanel Component
 * 
 * Displays connection status, swarm health, and system diagnostics.
 */

function StatusPanel({ connectionStatus, swarmState }) {
  const statusColor = {
    connected: 'text-green-400',
    disconnected: 'text-red-400',
    error: 'text-yellow-400'
  }
  const totalNodes = swarmState?.nodes?.length || swarmState?.data?.nodes?.length || 0

  return (
    <div className="bg-gray-800 rounded border border-gray-700 p-4">
      <h3 className="text-lg font-bold mb-4">System Status</h3>
      
      <div className="space-y-3">
        {/* Connection Status */}
        <div>
          <p className="text-gray-400 text-sm">Base Station</p>
          <p className={`font-mono ${statusColor[connectionStatus] || 'text-gray-500'}`}>
            {connectionStatus.toUpperCase()}
          </p>
        </div>

        {/* Active Nodes */}
        {swarmState?.active_nodes && (
          <div>
            <p className="text-gray-400 text-sm">Active Nodes</p>
            <p className="font-mono text-blue-400">{swarmState.active_nodes.length} / {totalNodes || '?'}</p>
          </div>
        )}

        {/* Swarm Status */}
        {swarmState?.status && (
          <div>
            <p className="text-gray-400 text-sm">Status</p>
            <p className="font-mono text-purple-400">{swarmState.status}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusPanel
