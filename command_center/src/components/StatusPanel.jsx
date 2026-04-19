import React from 'react'

/**
 * StatusPanel Component
 * 
 * Displays connection status, swarm health, and system diagnostics.
 */

function StatusPanel({ connectionStatus, swarmState, embedded = false }) {
  const statusColor = {
    connected: 'text-green-400',
    disconnected: 'text-red-400',
    error: 'text-yellow-400'
  }
  const totalNodes = swarmState?.nodes?.length || swarmState?.data?.nodes?.length || 0
  const activeScenario = swarmState?.scenario_info?.name
  const networkProfile = swarmState?.network_profile || {}
  const pendingExecute = swarmState?.pending_execute
  const missionStatus = swarmState?.search_state?.mission_status
  const missionObjective = swarmState?.search_state?.objective

  return (
    <div className={embedded ? '' : 'bg-gray-800 rounded border border-gray-700 p-4'}>
      {!embedded && <h3 className="text-lg font-bold mb-4">System Status</h3>}

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

        {missionStatus && missionStatus !== 'idle' && (
          <div>
            <p className="text-gray-400 text-sm">Mission</p>
            <p className="font-mono text-amber-300">{missionStatus}</p>
            {missionObjective && (
              <p className="mt-1 text-xs text-gray-400">{missionObjective}</p>
            )}
          </div>
        )}

        {activeScenario && (
          <div>
            <p className="text-gray-400 text-sm">Scenario</p>
            <p className="font-mono text-cyan-400">{activeScenario}</p>
          </div>
        )}

        {pendingExecute?.present && (
          <div>
            <p className="text-gray-400 text-sm">Pending Execute</p>
            <p className="font-mono text-yellow-300">AWAITING CONFIRMATION</p>
          </div>
        )}

        {networkProfile?.gossip_fanout && (
          <div>
            <p className="text-gray-400 text-sm">Network Profile</p>
            <p className="font-mono text-cyan-400">
              {networkProfile.profile || 'baseline'} / fanout {networkProfile.gossip_fanout} / hops {networkProfile.max_hops}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusPanel
