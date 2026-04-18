/*
JARVIS React App - Main Entry Point
Component Hub for the Command Center UI
*/

import React, { useEffect, useState } from 'react'
import SwarmGraph from './components/SwarmGraph'
import PushToTalkButton from './components/PushToTalkButton'
import StatusPanel from './components/StatusPanel'

function App() {
  const [swarmState, setSwarmState] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [commandHistory, setCommandHistory] = useState([])

  // Initialize WebSocket connection to FastAPI backend
  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws/swarm'
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('[App] Connected to JARVIS Base Station')
      setConnectionStatus('connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('[App] Received:', data)
      
      if (data.event === 'gossip_update' || data.event === 'swarm_state') {
        setSwarmState(data)
      }
    }

    ws.onclose = () => {
      console.log('[App] Disconnected from Base Station')
      setConnectionStatus('disconnected')
    }

    ws.onerror = (error) => {
      console.error('[App] WebSocket error:', error)
      setConnectionStatus('error')
    }

    return () => ws.close()
  }, [])

  const handleVoiceCommand = async (transcript) => {
    try {
      const response = await fetch('http://localhost:8000/api/voice-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcribed_text: transcript })
      })
      
      const result = await response.json()
      setCommandHistory(prev => [...prev, {
        timestamp: new Date().toISOString(),
        command: transcript,
        status: result.status
      }])
      
      console.log('[App] Command sent:', result)
    } catch (error) {
      console.error('[App] Error sending command:', error)
    }
  }

  return (
    <div className="app min-h-screen bg-gray-900 text-white">
      <header className="bg-black border-b border-red-500 p-4">
        <h1 className="text-3xl font-bold">⚡ JARVIS Command Center</h1>
        <p className="text-gray-400">Voice-Activated Swarm Coordinator</p>
      </header>

      <main className="flex gap-4 p-4">
        {/* Left: Swarm Graph Visualization */}
        <div className="flex-1">
          <div className="bg-gray-800 rounded border border-gray-700 p-4">
            <h2 className="text-xl font-bold mb-2">Swarm Topology</h2>
            {swarmState ? (
              <SwarmGraph state={swarmState} />
            ) : (
              <div className="w-full h-96 flex items-center justify-center bg-gray-900">
                <p className="text-gray-500">Awaiting connection...</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Control Panel */}
        <div className="w-80">
          {/* Status Indicator */}
          <StatusPanel connectionStatus={connectionStatus} swarmState={swarmState} />

          {/* Push-to-Talk Button */}
          <div className="bg-gray-800 rounded border border-gray-700 p-4 mt-4">
            <h3 className="text-lg font-bold mb-4">Voice Command</h3>
            <PushToTalkButton onCommand={handleVoiceCommand} />
          </div>

          {/* Command History */}
          <div className="bg-gray-800 rounded border border-gray-700 p-4 mt-4 h-96 overflow-y-auto">
            <h3 className="text-lg font-bold mb-2">Recent Commands</h3>
            {commandHistory.length === 0 ? (
              <p className="text-gray-500">No commands yet</p>
            ) : (
              <div className="space-y-2">
                {commandHistory.map((cmd, i) => (
                  <div key={i} className="bg-gray-900 p-2 rounded text-sm border-l-2 border-yellow-500">
                    <p className="font-mono">{cmd.command}</p>
                    <p className="text-xs text-gray-400">{cmd.status}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
