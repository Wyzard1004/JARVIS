/*
JARVIS React App - Main Entry Point
Component Hub for the Command Center UI
*/

import React, { useEffect, useRef, useState } from 'react'
import SwarmCanvas from './components/SwarmCanvas'
import EventConsole from './components/EventConsole'
import GridLegend from './components/GridLegend'
import DroneStatusCard from './components/DroneStatusCard'
import PushToTalkButton from './components/PushToTalkButton'
import StatusPanel from './components/StatusPanel'
import SoldierSelector from './components/SoldierSelector'

const MAP_MODE_OPTIONS = [
  {
    id: 'nato',
    label: 'NATO',
    description: 'Full map symbols'
  },
  {
    id: 'atak',
    label: 'ATAK-Inspired',
    description: 'Badge circles'
  }
]

const DEFAULT_MAP_OVERLAY = {
  asset_url: null,
  asset_path: null,
  opacity: 0.72,
  visible: false
}

const EDITOR_TOOL_OPTIONS = [
  { id: 'select', label: 'Select', description: 'Select and move placed objects' },
  { id: 'building', label: 'Building', description: 'Drag rectangle footprints' },
  { id: 'enemy-infantry', label: 'Infantry', description: 'Place hostile infantry' },
  { id: 'enemy-tank', label: 'Tank', description: 'Place hostile armor' },
  { id: 'enemy-vehicle', label: 'Vehicle', description: 'Place hostile vehicle' },
  { id: 'poi-downed_aircraft', label: 'Downed Aircraft', description: 'Place POI' },
  { id: 'poi-cache', label: 'Supply Cache', description: 'Place POI' },
  { id: 'poi-checkpoint', label: 'Checkpoint', description: 'Place POI' }
]

const POINT_TOOL_CONFIG = {
  'enemy-infantry': {
    collection: 'enemies',
    subtype: 'infantry',
    labelPrefix: 'Enemy Infantry',
    defaultStatus: 'active',
    revealed: false
  },
  'enemy-tank': {
    collection: 'enemies',
    subtype: 'tank',
    labelPrefix: 'Enemy Tank',
    defaultStatus: 'active',
    revealed: false
  },
  'enemy-vehicle': {
    collection: 'enemies',
    subtype: 'vehicle',
    labelPrefix: 'Enemy Vehicle',
    defaultStatus: 'active',
    revealed: false
  },
  'poi-downed_aircraft': {
    collection: 'special_entities',
    subtype: 'downed_aircraft',
    labelPrefix: 'Downed Aircraft',
    defaultStatus: 'undiscovered',
    revealed: false
  },
  'poi-cache': {
    collection: 'special_entities',
    subtype: 'cache',
    labelPrefix: 'Supply Cache',
    defaultStatus: 'undiscovered',
    revealed: false
  },
  'poi-checkpoint': {
    collection: 'special_entities',
    subtype: 'checkpoint',
    labelPrefix: 'Checkpoint',
    defaultStatus: 'active',
    revealed: false
  }
}

const normalizeSwarmState = (state) => {
  if (!state || typeof state !== 'object') return null

  return {
    ...state,
    map_overlay: {
      ...DEFAULT_MAP_OVERLAY,
      ...(state.map_overlay || {})
    },
    enemies: Array.isArray(state.enemies) ? state.enemies : [],
    structures: Array.isArray(state.structures) ? state.structures : [],
    special_entities: Array.isArray(state.special_entities) ? state.special_entities : [],
    nodes: Array.isArray(state.nodes) ? state.nodes : [],
    edges: Array.isArray(state.edges) ? state.edges : [],
    events: Array.isArray(state.events) ? state.events : []
  }
}

const cloneEditorPayload = (state) => {
  const normalized = normalizeSwarmState(state) || normalizeSwarmState({})
  return JSON.parse(JSON.stringify({
    drones: normalized?.nodes || [],
    map_overlay: normalized?.map_overlay || DEFAULT_MAP_OVERLAY,
    structures: normalized?.structures || [],
    enemies: normalized?.enemies || [],
    special_entities: normalized?.special_entities || []
  }))
}

const getSelectedMapEntityRecord = (state, selection) => {
  if (!selection || !state) return null
  const collection = Array.isArray(state[selection.kind]) ? state[selection.kind] : []
  return collection.find((item) => item.id === selection.id) || null
}

const getSelectedDroneRecord = (state, droneId) => {
  if (!state || !droneId) return null
  return (state.nodes || []).find((node) => node.id === droneId) || null
}

function App() {
  const [swarmState, setSwarmState] = useState(null)
  const [scenarioCatalog, setScenarioCatalog] = useState([])
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('')
  const [scenarioName, setScenarioName] = useState('Blank Workspace')
  const [scenarioNameDirty, setScenarioNameDirty] = useState(false)
  const [events, setEvents] = useState([])
  const [currentCommand, setCurrentCommand] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [commandHistory, setCommandHistory] = useState([])
  const [activeSoldier, setActiveSoldier] = useState('soldier-1')
  const [soldierStatus, setSoldierStatus] = useState(null)
  const [selectedDrone, setSelectedDrone] = useState(null)
  const [selectedMapEntity, setSelectedMapEntity] = useState(null)
  const [mapMode, setMapMode] = useState('nato')
  const [showEntityLabels, setShowEntityLabels] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [editorTool, setEditorTool] = useState('select')
  const [editorStatus, setEditorStatus] = useState('Map editor ready')
  const [editorBusy, setEditorBusy] = useState(false)
  const [scenarioBusy, setScenarioBusy] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const isCleaningUpRef = useRef(false)
  const overlayInputRef = useRef(null)
  const entityIdSequenceRef = useRef(1)
  const activeScenarioKeyRef = useRef('')
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 2000

  const syncScenarioNameDraft = (scenarioInfo, options = {}) => {
    const nextScenarioKey = scenarioInfo?.relative_path || ''
    const nextScenarioName = scenarioInfo?.name || 'Blank Workspace'
    const scenarioChanged = activeScenarioKeyRef.current !== nextScenarioKey

    activeScenarioKeyRef.current = nextScenarioKey

    if (options.force || scenarioChanged || !scenarioNameDirty) {
      setScenarioName(nextScenarioName)
      setScenarioNameDirty(false)
    }
  }

  const applyIncomingState = (payload, options = {}) => {
    const normalized = normalizeSwarmState(payload)
    if (!normalized) return null
    setSwarmState(normalized)
    setEvents(normalized.events || [])
    setSelectedScenarioKey(normalized.scenario_info?.relative_path || '')
    syncScenarioNameDraft(normalized.scenario_info, options)
    return normalized
  }

  const nextEntityId = (prefix) => `${prefix}-${Date.now()}-${entityIdSequenceRef.current++}`

  const refreshScenarioCatalog = async () => {
    try {
      const response = await fetch('/api/scenarios')
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Scenario list request failed')
      }
      setScenarioCatalog(Array.isArray(result.scenarios) ? result.scenarios : [])
      setSelectedScenarioKey(result.active_scenario?.relative_path || '')
      syncScenarioNameDraft(result.active_scenario)
    } catch (error) {
      console.error('[App] Failed to fetch scenario catalog:', error)
    }
  }

  const pushEditorPayload = async (payload, successMessage) => {
    setEditorBusy(true)
    try {
      const response = await fetch('/api/map-editor/state', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Map editor update failed')
      }
      applyIncomingState(result)
      if (successMessage) {
        setEditorStatus(successMessage)
      }
      return result
    } catch (error) {
      console.error('[App] Map editor update failed:', error)
      setEditorStatus(error.message)
      throw error
    } finally {
      setEditorBusy(false)
    }
  }

  const applyOverlayMutation = async (updates) => {
    if (!swarmState) return
    const payload = cloneEditorPayload(swarmState)
    payload.map_overlay = {
      ...DEFAULT_MAP_OVERLAY,
      ...payload.map_overlay,
      ...updates
    }
    await pushEditorPayload(payload, 'Overlay updated')
  }

  useEffect(() => {
    isCleaningUpRef.current = false

    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return () => {}
    }

    const connectWebSocket = () => {
      if (isCleaningUpRef.current) return

      let wsUrl = import.meta.env.VITE_WEBSOCKET_URL
      if (!wsUrl) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        wsUrl = `${protocol}//${window.location.hostname}:8000/ws/swarm`
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

          if (data.event === 'state_update' || data.event === 'initial_state') {
            if (data.event === 'state_update') {
              console.log('[App] State update: drones=' + (data.nodes?.length || 0) +
                ', edges=' + (data.edges?.length || 0))
            } else {
              console.log('[App] Initial state received')
            }
            applyIncomingState(data)
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
            applyIncomingState(data)
            setCurrentCommand({
              timestamp: new Date().toLocaleTimeString(),
              target: data.target_location || 'Unknown',
              status: data.status || 'processing',
              nodes: data.active_nodes?.length || data.nodes?.length || 0,
              totalTime: `${(data.total_propagation_ms || 0).toFixed(0)}ms`,
              message: data.confirmation_text || data.message || '',
              pendingExecute: Boolean(data.pending_execute?.present),
              callsign: data.parsed_command?.callsign || 'JARVIS'
            })
            return
          }

          if (data.event === 'command_response') {
            console.log('[App] Command response:', data.command_type)
            return
          }

          if (data.event === 'connected') {
            console.log('[App] ' + data.message)
            return
          }

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

        if (isCleaningUpRef.current) return

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current)
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connectWebSocket()
          }, delay)
        } else {
          console.error('[App] Max reconnection attempts reached')
        }
      }

      ws.onerror = (error) => {
        if (isCleaningUpRef.current) return
        console.error('[App] WebSocket error:', error)
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

  useEffect(() => {
    void refreshScenarioCatalog()
  }, [])

  useEffect(() => {
    if (!swarmState) return

    const activeNodeIds = new Set((swarmState.nodes || []).map((node) => node.id))
    if (selectedDrone && !activeNodeIds.has(selectedDrone)) {
      setSelectedDrone(null)
    }

    if (selectedMapEntity && !getSelectedMapEntityRecord(swarmState, selectedMapEntity)) {
      setSelectedMapEntity(null)
    }
  }, [swarmState])

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

      setCommandHistory((previous) => [...previous, {
        timestamp: new Date().toISOString(),
        command: transcriptText,
        status: result.status,
        goal: result.parsed_command?.goal || 'UNKNOWN',
        executionState: result.parsed_command?.execution_state || 'NONE'
      }])

      if (result.nodes?.length) {
        applyIncomingState(result)
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

  const handleMapEntityCreate = async (descriptor) => {
    if (!swarmState || !descriptor) return

    const payload = cloneEditorPayload(swarmState)

    if (descriptor.kind === 'structures') {
      const footprint = descriptor.footprint
      const position = descriptor.position || [
        footprint.x + footprint.width / 2,
        footprint.y + footprint.height / 2
      ]
      const structureRecord = {
        id: nextEntityId('structure-building'),
        label: `Building ${payload.structures.length + 1}`,
        subtype: 'building',
        status: 'intact',
        blocking_size: Number((Math.max(0.65, Math.min(4, Math.max(footprint.width, footprint.height) / 100))).toFixed(2)),
        position,
        footprint,
        render: {
          shape: 'rectangle',
          size: Math.max(18, Math.round(Math.max(footprint.width, footprint.height) / 4)),
          color: '#8B7355',
          opacity: 0.48
        }
      }
      payload.structures.push(structureRecord)
      setSelectedMapEntity({ kind: 'structures', id: structureRecord.id })
      setSelectedDrone(null)
      await pushEditorPayload(payload, 'Building added')
      return
    }

    const pointTool = POINT_TOOL_CONFIG[descriptor.tool]
    if (!pointTool) return

    const collection = payload[pointTool.collection]
    const entityRecord = {
      id: nextEntityId(`${pointTool.collection === 'enemies' ? 'enemy' : 'special'}-${pointTool.subtype.replace(/_/g, '-')}`),
      label: `${pointTool.labelPrefix} ${collection.length + 1}`,
      subtype: pointTool.subtype,
      status: pointTool.defaultStatus,
      position: descriptor.position,
      revealed: pointTool.revealed
    }

    collection.push(entityRecord)
    setSelectedMapEntity({ kind: pointTool.collection, id: entityRecord.id })
    setSelectedDrone(null)
    await pushEditorPayload(payload, `${pointTool.labelPrefix} placed`)
  }

  const handleMapEntityMove = async (descriptor) => {
    if (!swarmState || !descriptor?.kind || !descriptor?.id) return

    const payload = cloneEditorPayload(swarmState)
    const collection = payload[descriptor.kind]
    const targetIndex = collection.findIndex((item) => item.id === descriptor.id)
    if (targetIndex < 0) return

    const nextRecord = {
      ...collection[targetIndex],
      ...(descriptor.position ? { position: descriptor.position } : {}),
      ...(descriptor.footprint ? { footprint: descriptor.footprint } : {})
    }

    collection[targetIndex] = nextRecord
    await pushEditorPayload(payload, 'Map object moved')
  }

  const handleDroneMove = async (descriptor) => {
    if (!swarmState || !descriptor?.id || !descriptor?.position) return

    const payload = cloneEditorPayload(swarmState)
    payload.drones = payload.drones.map((node) => (
      node.id === descriptor.id
        ? { ...node, position: descriptor.position }
        : node
    ))
    await pushEditorPayload(payload, 'Drone moved')
  }

  const handleDeleteSelectedEntity = async () => {
    if (!swarmState) return
    const payload = cloneEditorPayload(swarmState)

    if (selectedMapEntity) {
      payload[selectedMapEntity.kind] = payload[selectedMapEntity.kind].filter((entity) => entity.id !== selectedMapEntity.id)
      setSelectedMapEntity(null)
      await pushEditorPayload(payload, 'Map object deleted')
      return
    }

    if (selectedDrone) {
      payload.drones = payload.drones.filter((node) => node.id !== selectedDrone)
      setSelectedDrone(null)
      await pushEditorPayload(payload, 'Drone deleted')
    }
  }

  const handleOverlayUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setEditorBusy(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch('/api/map-editor/overlay', {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Overlay upload failed')
      }
      applyIncomingState(result)
      setEditorStatus('Overlay uploaded')
    } catch (error) {
      console.error('[App] Overlay upload failed:', error)
      setEditorStatus(error.message)
    } finally {
      setEditorBusy(false)
      event.target.value = ''
    }
  }

  const handleSaveScenario = async () => {
    setEditorBusy(true)
    try {
      const response = await fetch('/api/map-editor/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_name: scenarioName.trim() })
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Scenario save failed')
      }
      applyIncomingState(result, { force: true })
      setEditorStatus(result.message || 'Scenario saved')
      await refreshScenarioCatalog()
    } catch (error) {
      console.error('[App] Scenario save failed:', error)
      setEditorStatus(error.message)
    } finally {
      setEditorBusy(false)
    }
  }

  const handleScenarioLoad = async () => {
    if (!selectedScenarioKey) return
    setScenarioBusy(true)
    try {
      const response = await fetch('/api/scenarios/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_key: selectedScenarioKey })
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Scenario load failed')
      }
      applyIncomingState(result, { force: true })
      setCurrentCommand(null)
      setSelectedDrone(null)
      setSelectedMapEntity(null)
      setEditMode(false)
      setEditorTool('select')
      setEditorStatus(result.message || 'Scenario loaded')
      await refreshScenarioCatalog()
    } catch (error) {
      console.error('[App] Scenario load failed:', error)
      setEditorStatus(error.message)
    } finally {
      setScenarioBusy(false)
    }
  }

  const selectedMapRecord = getSelectedMapEntityRecord(swarmState, selectedMapEntity)
  const selectedDroneRecord = getSelectedDroneRecord(swarmState, selectedDrone)
  const overlayState = swarmState?.map_overlay || DEFAULT_MAP_OVERLAY
  const activeScenarioInfo = swarmState?.scenario_info || null
  const saveButtonLabel = activeScenarioInfo?.relative_path === 'swarm_initial_state.json'
    ? 'Save New Scenario'
    : 'Save Scenario'

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
              <div className="grid gap-4 md:grid-cols-3 md:gap-8">
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

      <main className="grid gap-4 p-4 auto-rows-max xl:grid-cols-[minmax(0,1.7fr)_minmax(20rem,1fr)]">
        <div className="min-w-0 space-y-4">
          <div className="w-full">
            <div className="w-full bg-gray-800 rounded border border-gray-700 p-4">
              <div className="mb-4 grid gap-3 2xl:grid-cols-[minmax(0,1fr)_minmax(17rem,22rem)]">
                <div className="rounded border border-gray-700 bg-gray-900/60 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-bold">📡 Swarm Grid Visualization</h2>
                      <p className="text-xs text-gray-400">
                        {mapMode === 'atak'
                          ? 'ATAK-inspired circular badges with embedded unit marks'
                          : 'Full NATO map symbols with translucent unit labels'}
                      </p>
                    </div>
                    <div className="min-w-[230px] rounded border border-gray-600 bg-gray-950/70 p-2">
                      <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-400">Map Mode</div>
                      <div className="mt-2 flex gap-2">
                        {MAP_MODE_OPTIONS.map((option) => {
                          const isActive = option.id === mapMode
                          return (
                            <button
                              key={option.id}
                              type="button"
                              onClick={() => setMapMode(option.id)}
                              className={`flex-1 rounded border px-3 py-2 text-left text-xs transition ${
                                isActive
                                  ? 'border-sky-400 bg-sky-500/15 text-sky-100'
                                  : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500 hover:bg-gray-700'
                              }`}
                            >
                              <div className="font-bold uppercase tracking-wide">{option.label}</div>
                              <div className="mt-0.5 text-[10px] text-gray-400">{option.description}</div>
                            </button>
                          )
                        })}
                      </div>
                      <div className="mt-3 flex items-center justify-between gap-3 rounded border border-gray-700 bg-gray-900/60 px-3 py-2">
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-gray-300">Labels</div>
                          <div className="text-[10px] text-gray-500">Smaller translucent callsign chips</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setShowEntityLabels((current) => !current)}
                          className={`rounded border px-3 py-1.5 text-[11px] font-bold transition ${
                            showEntityLabels
                              ? 'border-sky-400 bg-sky-500/15 text-sky-100'
                              : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500 hover:bg-gray-700'
                          }`}
                        >
                          {showEntityLabels ? 'Shown' : 'Hidden'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="rounded border border-gray-600 bg-gray-900/70 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-400">Scenario Loader</p>
                        <p className="text-xs text-gray-400">
                          {activeScenarioInfo
                            ? `Active: ${activeScenarioInfo.name}`
                            : 'Select a blank or saved scenario to load.'}
                        </p>
                      </div>
                      {activeScenarioInfo && (
                        <div className="rounded border border-gray-700 bg-gray-950/50 px-2 py-1 text-[10px] uppercase tracking-wide text-gray-400">
                          {activeScenarioInfo.node_count} nodes / {activeScenarioInfo.structure_count} structures
                        </div>
                      )}
                    </div>

                    <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                      <select
                        value={selectedScenarioKey}
                        onChange={(event) => setSelectedScenarioKey(event.target.value)}
                        disabled={scenarioBusy}
                        className="min-w-0 flex-1 rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100"
                      >
                        {scenarioCatalog.length > 0 ? (
                          scenarioCatalog.map((scenario) => (
                            <option key={scenario.key} value={scenario.key}>
                              {scenario.name}{scenario.is_blank ? ' (Blank)' : ''}
                            </option>
                          ))
                        ) : (
                          <option value="">No scenarios found</option>
                        )}
                      </select>
                      <button
                        type="button"
                        onClick={handleScenarioLoad}
                        disabled={scenarioBusy || !selectedScenarioKey}
                        className="rounded border border-cyan-500/60 bg-cyan-500/10 px-3 py-2 text-xs font-bold text-cyan-100 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {scenarioBusy ? 'Loading...' : 'Load Scenario'}
                      </button>
                    </div>

                    <label className="mt-3 block text-xs text-gray-300">
                      <span className="mb-1 block">Scenario Name</span>
                      <input
                        type="text"
                        value={scenarioName}
                        onChange={(event) => {
                          setScenarioName(event.target.value)
                          setScenarioNameDirty(true)
                        }}
                        className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100"
                        placeholder="Scenario name"
                      />
                    </label>

                    <div className="mt-2 text-[11px] text-gray-500">
                      Saving from the blank workspace creates a new scenario file in the library.
                    </div>
                  </div>

                  <div className="rounded border border-gray-600 bg-gray-900/70 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-400">Map Editor</p>
                        <p className="text-xs text-gray-400">Live scenario editing and save-to-config controls.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setEditMode((current) => !current)
                          setEditorTool('select')
                        }}
                        className={`rounded border px-3 py-2 text-xs font-bold transition ${
                          editMode
                            ? 'border-emerald-400 bg-emerald-500/15 text-emerald-100'
                            : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500 hover:bg-gray-700'
                        }`}
                      >
                        {editMode ? 'Editor On' : 'Editor Off'}
                      </button>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2">
                      {EDITOR_TOOL_OPTIONS.map((tool) => {
                        const isActive = tool.id === editorTool
                        return (
                          <button
                            key={tool.id}
                            type="button"
                            onClick={() => {
                              setEditorTool(tool.id)
                              setEditMode(true)
                            }}
                            className={`rounded border px-2 py-2 text-left text-[11px] transition ${
                              isActive
                                ? 'border-amber-400 bg-amber-500/15 text-amber-100'
                                : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500 hover:bg-gray-700'
                            }`}
                          >
                            <div className="font-bold uppercase tracking-wide">{tool.label}</div>
                            <div className="mt-1 text-[10px] text-gray-400">{tool.description}</div>
                          </button>
                        )
                      })}
                    </div>

                    <div className="mt-3 space-y-3 rounded border border-gray-700 bg-gray-950/40 p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          onClick={() => overlayInputRef.current?.click()}
                          disabled={editorBusy}
                          className="rounded border border-blue-500/60 bg-blue-500/10 px-3 py-2 text-xs font-bold text-blue-100 transition hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Upload Overlay
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveScenario}
                          disabled={editorBusy}
                          className="rounded border border-emerald-500/60 bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {saveButtonLabel}
                        </button>
                        <button
                          type="button"
                          onClick={handleDeleteSelectedEntity}
                          disabled={editorBusy || (!selectedMapEntity && !selectedDrone)}
                          className="rounded border border-rose-500/60 bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Delete Selected
                        </button>
                        <input
                          ref={overlayInputRef}
                          type="file"
                          accept="image/*"
                          onChange={handleOverlayUpload}
                          className="hidden"
                        />
                      </div>

                      <label className="flex items-center justify-between gap-3 text-xs text-gray-300">
                        <span>Overlay Visible</span>
                        <input
                          type="checkbox"
                          checked={Boolean(overlayState.visible && overlayState.asset_url)}
                          disabled={!overlayState.asset_url || editorBusy}
                          onChange={(event) => {
                            void applyOverlayMutation({ visible: event.target.checked })
                          }}
                        />
                      </label>

                      <label className="block text-xs text-gray-300">
                        <span className="mb-1 block">Overlay Opacity: {Math.round((overlayState.opacity || 0) * 100)}%</span>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={Math.round((overlayState.opacity || 0) * 100)}
                          disabled={!overlayState.asset_url || editorBusy}
                          onChange={(event) => {
                            const nextOpacity = Number(event.target.value) / 100
                            void applyOverlayMutation({ opacity: nextOpacity })
                          }}
                          className="w-full"
                        />
                      </label>

                      <div className="text-[11px] text-gray-400">
                        {editorStatus}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {swarmState ? (
                <SwarmCanvas
                  state={swarmState}
                  selectedDrone={selectedDrone}
                  selectedMapEntity={selectedMapEntity}
                  mapMode={mapMode}
                  showEntityLabels={showEntityLabels}
                  editMode={editMode}
                  editorTool={editorTool}
                  onDroneClick={(droneId) => {
                    setSelectedDrone(droneId)
                    if (droneId) {
                      setSelectedMapEntity(null)
                    }
                  }}
                  onMapEntitySelect={(selection) => {
                    setSelectedMapEntity(selection)
                    if (selection) {
                      setSelectedDrone(null)
                    }
                  }}
                  onMapEntityCreate={handleMapEntityCreate}
                  onMapEntityMove={handleMapEntityMove}
                  onDroneMove={handleDroneMove}
                />
              ) : (
                <div className="w-full min-h-[24rem] flex items-center justify-center bg-gray-900 rounded">
                  <p className="text-gray-500">Awaiting swarm state...</p>
                </div>
              )}
            </div>
          </div>

          <div className="w-full">
            <EventConsole events={events} maxVisible={20} />
          </div>
        </div>

        <div className="min-w-0 space-y-4">
          <SoldierSelector
            activeSoldier={activeSoldier}
            onSoldierChange={handleSoldierChange}
            soldierStatus={soldierStatus}
          />

          <StatusPanel connectionStatus={connectionStatus} swarmState={swarmState} />

          {selectedDroneRecord && (
            <DroneStatusCard
              drone={selectedDroneRecord}
              commsStatus="online"
            />
          )}

          {selectedMapRecord && (
            <div className="bg-gray-800 rounded border border-gray-700 p-4 space-y-2">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Selected Map Object</div>
              <div className="text-lg font-bold text-gray-100">{selectedMapRecord.label || selectedMapRecord.id}</div>
              <div className="text-sm text-gray-300 capitalize">
                {(selectedMapEntity?.kind || '').replace(/_/g, ' ')} / {(selectedMapRecord.subtype || selectedMapRecord.type || 'unknown').replace(/_/g, ' ')}
              </div>
              {Array.isArray(selectedMapRecord.position) && (
                <div className="font-mono text-xs text-gray-400">
                  Position: {Math.round(selectedMapRecord.position[0])}, {Math.round(selectedMapRecord.position[1])}
                </div>
              )}
            </div>
          )}

          <GridLegend activeDrones={swarmState?.nodes || []} mapMode={mapMode} />

          <div className="bg-gray-800 rounded border border-gray-700 p-4">
            <h3 className="text-lg font-bold mb-4">🎤 Voice Command</h3>
            <PushToTalkButton onCommand={handleVoiceCommand} />
          </div>

          <div className="bg-gray-800 rounded border border-gray-700 p-4 min-h-[12rem] max-h-[20rem] overflow-y-auto">
            <h3 className="text-lg font-bold mb-2">📜 Recent Commands</h3>
            {commandHistory.length === 0 ? (
              <p className="text-gray-500 text-sm">No commands yet</p>
            ) : (
              <div className="space-y-2">
                {commandHistory.slice(-5).map((cmd, index) => (
                  <div key={`${cmd.timestamp}-${index}`} className="bg-gray-900 p-2 rounded text-xs border-l-2 border-yellow-500">
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
