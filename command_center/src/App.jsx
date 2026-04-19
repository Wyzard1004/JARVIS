/*
JARVIS React App - Main Entry Point
Component Hub for the Command Center UI
*/

import React, { useEffect, useState } from 'react'
import SwarmCanvas from './components/SwarmCanvas'
import EventConsole from './components/EventConsole'
import GridLegend from './components/GridLegend'
import DroneStatusCard from './components/DroneStatusCard'
import PushToTalkButton from './components/PushToTalkButton'
import StatusPanel from './components/StatusPanel'
import SoldierSelector from './components/SoldierSelector'

function App() {
  const [swarmState, setSwarmState] = useState(null)
  const [events, setEvents] = useState([])
  const [currentCommand, setCurrentCommand] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [commandHistory, setCommandHistory] = useState([])
  const [activeSoldier, setActiveSoldier] = useState('soldier-1')
  const [soldierStatus, setSoldierStatus] = useState(null)
  const [selectedDrone, setSelectedDrone] = useState(null)
  const [batteryLevels, setBatteryLevels] = useState({}) // Persistent battery levels across renders
  const wsRef = React.useRef(null)
  const reconnectTimeoutRef = React.useRef(null)
  const reconnectAttemptsRef = React.useRef(0)
  const isCleaningUpRef = React.useRef(false)
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 2000 // 2 seconds

  // Initialize random battery once per drone ID and keep it stable
  useEffect(() => {
    if (!swarmState) return

    const droneIds = [
      ...((swarmState.drones || []).map(d => d.id)),
      ...((swarmState.nodes || []).map(n => n.id))
    ]

    if (droneIds.length === 0) return

    setBatteryLevels(prev => {
      const next = { ...prev }
      for (const id of droneIds) {
        if (next[id] === undefined) {
          next[id] = Math.floor(Math.random() * 30) + 70
        }
      }
      return next
    })
  }, [swarmState])

  // Initialize WebSocket connection to FastAPI backend
  useEffect(() => {
    // Reset cleanup flag when effect runs
    isCleaningUpRef.current = false

    // Don't reconnect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return () => {}
    }

    const connectWebSocket = () => {
      // Don't attempt connection during cleanup
      if (isCleaningUpRef.current) {
        return
      }

      // Determine the WebSocket URL based on environment or current hostname
      let wsUrl = import.meta.env.VITE_WEBSOCKET_URL
      
      if (!wsUrl) {
        // For SSH port forwarding scenarios, use the same hostname as the frontend
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const hostname = window.location.hostname
        const port = 8000 // Backend runs on 8000
        wsUrl = `${protocol}//${hostname}:${port}/ws/swarm`
      }
      
      console.log(`[App] Connecting to WebSocket at ${wsUrl}`)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[App] Connected to JARVIS Base Station')
        setConnectionStatus('connected')
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('[App] Received event:', data.event)
          
          // Handle Phase 4 continuous state updates
          if (data.event === 'state_update') {
            // Real-time state sync from swarm coordinator
            console.log('[App] State update: drones=' + (data.nodes?.length || 0) + 
                         ', edges=' + (data.edges?.length || 0))
            setSwarmState(data)
            return
          }
          
          // Handle initial state on connection
          if (data.event === 'initial_state') {
            console.log('[App] Initial state received')
            setSwarmState(data)
            return
          }
          
          // Handle gossip updates from voice commands and staged command states
          if (
            data.event === 'gossip_update' ||
            data.event === 'swarm_state' ||
            data.event === 'command_pending' ||
            data.event === 'command_canceled'
          ) {
            console.log('[App] Updating swarm state from command response')
            setSwarmState(data)
            
            // Update events if included in payload
            if (data.events && Array.isArray(data.events)) {
              setEvents(data.events)
            }
            
            // Update current command display for command lifecycle events
            if (data.event === 'gossip_update' || data.event === 'command_pending' || data.event === 'command_canceled') {
              setCurrentCommand({
                timestamp: new Date().toLocaleTimeString(),
                target: data.target_location || 'Unknown',
                status: data.status || 'processing',
                nodes: data.active_nodes?.length || data.nodes?.length || 0,
                totalTime: `${(data.total_propagation_ms || 0).toFixed(0)}ms`,
                message: data.confirmation_text || '',
                pendingExecute: Boolean(data.pending_execute?.present),
                callsign: data.parsed_command?.callsign || 'JARVIS'
              })
            }
            return
          }
          
          // Handle command responses
          if (data.event === 'command_response') {
            console.log('[App] Command response:', data.command_type)
            if (data.response?.status === 'success') {
              console.log('[App] Command executed:', data.response.message)
            }
            return
          }
          
          // Handle connection confirmations
          if (data.event === 'connected') {
            console.log('[App] ' + data.message)
            return
          }
          
          // Handle errors
          if (data.event === 'error') {
            console.error('[App] Server error:', data.error)
            return
          }
          
          console.log('[App] Unknown event type:', data.event)
        } catch (error) {
          console.error('[App] Failed to parse WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        console.log('[App] Disconnected from Base Station')
        if (wsRef.current === ws) {
          wsRef.current = null
        }
        setConnectionStatus('disconnected')
        
        // Don't attempt reconnection during cleanup (React Strict Mode)
        if (isCleaningUpRef.current) {
          return
        }
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current)
          console.log(`[App] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connectWebSocket()
          }, delay)
        } else {
          console.error('[App] Max reconnection attempts reached')
        }
      }

      ws.onerror = (error) => {
        // Don't log errors during cleanup (React Strict Mode)
        if (isCleaningUpRef.current) {
          return
        }

        console.error('[App] WebSocket error:', {
          type: error.type,
          readyState: error.target?.readyState,
          url: error.target?.url,
          message: error.message || 'Unknown WebSocket error'
        })
        
        // Provide helpful debugging info
        if (error.target?.readyState === 3) {
          console.error('[App] WebSocket connection closed. Ensure:')
          console.error('[App]   1. Backend is running: cd base_station && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000')
          console.error('[App]   2. SSH port forwarding is active: ssh -L 5173:localhost:5173 -L 8000:localhost:8000 user@server')
          console.error('[App]   3. Check backend logs for errors')
        }
        
        setConnectionStatus('error')
      }
    }

    connectWebSocket()
    
    return () => {
      isCleaningUpRef.current = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleVoiceCommand = async (transcript) => {
    try {
      let response
      let historyCommand = typeof transcript === 'string' ? transcript : 'Processing audio...'

      if (typeof transcript === 'string') {
        response = await fetch('/api/voice-command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcribed_text: transcript })
        })
      } else {
        const formData = new FormData()
        const extension = transcript.mimeType?.includes('ogg')
          ? 'ogg'
          : transcript.mimeType?.includes('wav')
            ? 'wav'
            : 'webm'

        formData.append('audio', transcript.audioBlob, `recording.${extension}`)
        response = await fetch('/api/transcribe-command', {
          method: 'POST',
          body: formData
        })
      }
      
      const result = await response.json()
      const transcriptText = result.transcribed_text || historyCommand
      historyCommand = transcriptText

      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Voice command request failed')
      }

      setCommandHistory(prev => [...prev, {
        timestamp: new Date().toISOString(),
        command: transcriptText,
        status: result.status,
        goal: result.parsed_command?.goal || 'UNKNOWN',
        executionState: result.parsed_command?.execution_state || 'NONE'
      }])

      if (result.nodes?.length) {
        setSwarmState(result)
      }

      if (result.status) {
        setCurrentCommand({
          timestamp: new Date().toLocaleTimeString(),
          target: result.target_location || 'Unknown',
          status: result.status || 'processing',
          nodes: result.active_nodes?.length || result.nodes?.length || 0,
          totalTime: `${(result.total_propagation_ms || 0).toFixed(0)}ms`,
          message: result.confirmation_text || result.message || '',
          pendingExecute: Boolean(result.pending_execute?.present),
          callsign: result.parsed_command?.callsign || 'JARVIS'
        })
      }
      
      console.log('[App] Command sent:', result)
      return result
    } catch (error) {
      console.error('[App] Error sending command:', error)
      return { error: error.message }
    }
  }

  const handleSoldierChange = async (soldierId) => {
    setActiveSoldier(soldierId)
    try {
      const response = await fetch(`/api/soldier/${soldierId}/status`)
      if (response.ok) {
        const data = await response.json()
        setSoldierStatus({
          status: 'online',
          pending_commands: data.pending_commands || 0,
          last_mission: data.last_mission_id || null
        })
      }
    } catch (error) {
      console.error('[App] Failed to fetch soldier status:', error)
    }
  }

  return (
    <div className="app min-h-screen bg-gray-900 text-white">
      <header className="bg-black border-b border-red-500 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">⚡ JARVIS Command Center</h1>
            <p className="text-gray-400">Voice-Activated Swarm Coordinator</p>
          </div>
          <div className={`text-center px-4 py-2 rounded ${connectionStatus === 'connected' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'}`}>
            <p className="text-sm font-bold">
              {connectionStatus === 'connected' ? '🟢 CONNECTED' : '🔴 DISCONNECTED'}
            </p>
          </div>
        </div>
      </header>

      {/* Active Mission Status */}
      {currentCommand && (
        <div className={currentCommand.pendingExecute
          ? 'bg-gradient-to-r from-yellow-950 to-orange-900 border-b-4 border-yellow-500 p-6'
          : 'bg-gradient-to-r from-yellow-900 to-red-900 border-b-4 border-red-500 p-6'}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-gray-300 mb-2">📡 ACTIVE MISSION</p>
              <h2 className="text-4xl font-bold text-yellow-300 mb-4">
                {currentCommand.target || 'UNKNOWN'}
              </h2>
              {currentCommand.pendingExecute && (
                <p className="mb-4 inline-block rounded border border-yellow-400 px-3 py-1 text-sm font-semibold uppercase tracking-wide text-yellow-200">
                  Awaiting Execute
                </p>
              )}
              <div className="grid grid-cols-3 gap-8">
                <div>
                  <p className="text-xs text-gray-300 uppercase">Status</p>
                  <p className="text-xl font-bold text-white capitalize">
                    {currentCommand.status.replace(/_/g, ' ')}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-300 uppercase">Active Nodes</p>
                  <p className="text-3xl font-bold text-white">{currentCommand.nodes}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-300 uppercase">Propagation Time</p>
                  <p className="text-2xl font-bold text-white">{currentCommand.totalTime}</p>
                </div>
              </div>
            </div>
            <div className="text-right text-sm text-gray-300">
              <p>{currentCommand.timestamp}</p>
              {currentCommand.message && (
                <p className="text-xs italic text-gray-400 mt-2">"{currentCommand.message}"</p>
              )}
            </div>
          </div>
        </div>
      )}

      <main className="grid grid-cols-12 gap-4 p-4 auto-rows-max">
        {/* Left: Swarm Canvas Visualization (8 columns, square aspect) */}
        <div className="col-span-8 flex justify-center">
          <div className="bg-gray-800 rounded border border-gray-700 p-4" style={{ width: 'fit-content' }}>
            <h2 className="text-xl font-bold mb-2">📡 Swarm Grid Visualization</h2>
            {swarmState && (swarmState.drones || swarmState.nodes) ? (
              <SwarmCanvas 
                state={swarmState}
                selectedDrone={selectedDrone}
                onDroneClick={(droneId) => setSelectedDrone(droneId)}
              />
            ) : (
              <div className="w-full h-96 flex items-center justify-center bg-gray-900 rounded">
                <p className="text-gray-500">Awaiting swarm state...</p>
              </div>
            )}
          </div>

          {/* Event Console Below Grid */}
          <div className="mt-4">
            <EventConsole events={events} maxVisible={20} />
          </div>
        </div>

        {/* Right Panel (4 columns) */}
        <div className="col-span-4 space-y-4">
          {/* Soldier Selector */}
          <SoldierSelector 
            activeSoldier={activeSoldier}
            onSoldierChange={handleSoldierChange}
            soldierStatus={soldierStatus}
          />

          {/* Status Indicator */}
          <StatusPanel connectionStatus={connectionStatus} swarmState={swarmState} />

          {/* Selected Drone Status Card */}
          {selectedDrone && swarmState && (
            <DroneStatusCard 
              drone={(swarmState.drones || []).find(d => d.id === selectedDrone) ||
                     (swarmState.nodes?.find(n => n.id === selectedDrone))}
              commsStatus="online"
              batteryLevels={batteryLevels}
            />
          )}

          {/* Grid Legend */}
          <GridLegend 
            activeDrones={swarmState?.drones || swarmState?.nodes || []}
          />

          {/* Push-to-Talk Button */}
          <div className="bg-gray-800 rounded border border-gray-700 p-4">
            <h3 className="text-lg font-bold mb-4">🎤 Voice Command</h3>
            <PushToTalkButton onCommand={handleVoiceCommand} />
          </div>

          {/* Command History */}
          <div className="bg-gray-800 rounded border border-gray-700 p-4 h-48 overflow-y-auto">
            <h3 className="text-lg font-bold mb-2">📜 Recent Commands</h3>
            {commandHistory.length === 0 ? (
              <p className="text-gray-500 text-sm">No commands yet</p>
            ) : (
              <div className="space-y-2">
                {commandHistory.slice(-5).map((cmd, i) => (
                  <div key={i} className="bg-gray-900 p-2 rounded text-xs border-l-2 border-yellow-500">
                    <p className="font-mono text-gray-300">{cmd.command.substring(0, 40)}...</p>
                    <p className="text-xs text-blue-400">{cmd.goal}</p>
                    <p className="text-[10px] text-gray-500">{cmd.status} / {cmd.executionState}</p>
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
