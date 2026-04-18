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
  const wsRef = React.useRef(null)
  const reconnectTimeoutRef = React.useRef(null)
  const reconnectAttemptsRef = React.useRef(0)
  const isCleaningUpRef = React.useRef(false)
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 2000 // 2 seconds

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
          console.log('[App] Received:', data)
          
          // Handle both gossip updates and initial swarm state
          if (data.event === 'gossip_update' || data.event === 'swarm_state') {
            console.log('[App] Updating swarm state')
            setSwarmState(data)
          }
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
        goal: result.parsed_command?.goal || 'UNKNOWN'
      }])

      if (result.nodes?.length) {
        setSwarmState(result)
      }
      
      console.log('[App] Command sent:', result)
      return result
    } catch (error) {
      console.error('[App] Error sending command:', error)
      return { error: error.message }
    }
  }

  return (
    <div className="app min-h-screen bg-gray-900 text-white">
      <header className="bg-black border-b border-red-500 p-4">
        <h1 className="text-3xl font-bold">⚡ JARVIS Command Center</h1>
        <p className="text-gray-400">Consensus-Driven Swarm Coordination</p>
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

          {/* Optional voice input */}
          <div className="bg-gray-800 rounded border border-gray-700 p-4 mt-4">
            <h3 className="text-lg font-bold mb-4">Optional Voice Input</h3>
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
                    <p className="text-xs text-blue-400">{cmd.goal}</p>
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
