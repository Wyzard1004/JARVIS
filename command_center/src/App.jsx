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
import CollapsiblePanel from './components/CollapsiblePanel'
import ContestedRelayComparisonPage from './components/ContestedRelayComparisonPage'
import SwarmPropagationLabPage from './components/SwarmPropagationLabPage'
import { getEntityDisplayLabel, sanitizeUnitIdentifiers } from './lib/displayNames'

const normalizeBaseUrl = (value) => String(value || '').trim().replace(/\/+$/, '')
const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)
const EXPLICIT_WEBSOCKET_URL = normalizeBaseUrl(import.meta.env.VITE_WEBSOCKET_URL)

const joinUrl = (baseUrl, path) => {
  if (!baseUrl) return path
  const sanitizedPath = String(path || '').replace(/^\/+/, '')
  return new URL(sanitizedPath, `${baseUrl}/`).toString()
}

const resolveApiUrl = (path) => joinUrl(API_BASE_URL, path)

const resolveWebSocketUrl = () => {
  if (EXPLICIT_WEBSOCKET_URL) {
    return EXPLICIT_WEBSOCKET_URL
  }

  if (API_BASE_URL) {
    const wsUrl = new URL(joinUrl(API_BASE_URL, 'ws/swarm'))
    wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    return wsUrl.toString()
  }

  const wsUrl = new URL('/ws/swarm', window.location.origin)
  wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  return wsUrl.toString()
}

const resolveScenarioAssetUrl = (assetUrl) => {
  if (!assetUrl) return assetUrl
  if (/^https?:\/\//i.test(assetUrl)) return assetUrl
  return joinUrl(API_BASE_URL, assetUrl)
}

const PAGE_COMMAND_CENTER = 'command-center'
const PAGE_RELAY_COMPARISON = 'relay-comparison'
const PAGE_PROPAGATION_LAB = 'propagation-lab'

const VIEW_OPTIONS = [
  {
    id: PAGE_COMMAND_CENTER,
    label: 'Command Center',
    subtitle: 'Live swarm control',
    description: 'Live swarm command, scenario, and relay control',
    documentTitle: 'JARVIS Command Center'
  },
  {
    id: PAGE_RELAY_COMPARISON,
    label: 'Comparison Lab',
    subtitle: 'Doctrine simulator',
    description: 'Contested relay doctrine and topology comparison',
    documentTitle: 'JARVIS Relay Comparison Lab'
  },
  {
    id: PAGE_PROPAGATION_LAB,
    label: 'Propagation Lab',
    subtitle: 'Mesh stress simulator',
    description: 'Hop limits, backup links, and reroute pressure in a gateway-centered mesh',
    documentTitle: 'JARVIS Propagation Stress Lab'
  }
]

const getViewOption = (pageId) => {
  return VIEW_OPTIONS.find((view) => view.id === pageId) || VIEW_OPTIONS[0]
}

const getPageFromHash = () => {
  if (typeof window === 'undefined') return PAGE_COMMAND_CENTER
  const normalized = String(window.location.hash || '').replace(/^#\/?/, '').trim().toLowerCase()
  return getViewOption(normalized).id
}

const getActiveFullscreenElement = () => {
  if (typeof document === 'undefined') return null
  return document.fullscreenElement || document.webkitFullscreenElement || null
}

const requestFullscreenForElement = async (element) => {
  if (!element) {
    throw new Error('Map container is unavailable')
  }

  if (typeof element.requestFullscreen === 'function') {
    await element.requestFullscreen()
    return
  }

  if (typeof element.webkitRequestFullscreen === 'function') {
    element.webkitRequestFullscreen()
    return
  }

  throw new Error('Fullscreen API is unavailable in this browser')
}

const exitActiveFullscreen = async () => {
  if (typeof document === 'undefined') return

  if (typeof document.exitFullscreen === 'function') {
    await document.exitFullscreen()
    return
  }

  if (typeof document.webkitExitFullscreen === 'function') {
    document.webkitExitFullscreen()
  }
}

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

const DEFAULT_OPERATOR_CONTEXT = {
  active_operator: 'soldier-1',
  available_operators: ['soldier-1', 'soldier-2'],
  updated_at: null
}

const DEFAULT_SEARCH_STATE = {
  control_node: null,
  mission_status: 'idle',
  objective: null,
  target_location: null,
  action_code: null,
  origin: null,
  target_tasks: [],
  engagements: []
}

const DEFAULT_SIMULATION_SETTINGS = {
  slowdown_factor: 1,
  speed_multiplier: 1
}

const DEFAULT_SUGGESTED_COMMANDS = [
  'JARVIS, recon Alpha 1',
  'JARVIS, recon Bravo 6',
  'JARVIS, attack Bravo 6',
  'JARVIS, recon patrol Alpha 1 to Alpha 8',
  'JARVIS, recon patrol Bravo 2 to Delta 5'
]

const DEFAULT_COLLAPSED_PANELS = {
  mapMode: false,
  scenarioLoader: false,
  mapEditor: false,
  systemStatus: false,
  suggestedCommands: false,
  selectedUnit: false,
  selectedMapObject: false,
  legend: false,
  recentCommands: false
}

const EDITOR_TOOL_OPTIONS = [
  { id: 'select', label: 'Select', description: 'Select and move placed objects' },
  { id: 'building', label: 'Building', description: 'Drag rectangle footprints' },
  { id: 'friendly-soldier', label: 'Friendly Soldier', description: 'Place allied operator / infantry' },
  { id: 'friendly-compute', label: 'Friendly Compute', description: 'Place allied compute drone' },
  { id: 'friendly-recon', label: 'Friendly Recon', description: 'Place allied recon drone' },
  { id: 'friendly-attack', label: 'Friendly Attack', description: 'Place allied attack drone' },
  { id: 'enemy-infantry', label: 'Infantry', description: 'Place hostile infantry' },
  { id: 'enemy-tank', label: 'Tank', description: 'Place hostile armor' },
  { id: 'enemy-vehicle', label: 'Vehicle', description: 'Place hostile vehicle' },
  { id: 'poi-downed_aircraft', label: 'Downed Aircraft', description: 'Place POI' },
  { id: 'poi-cache', label: 'Supply Cache', description: 'Place POI' },
  { id: 'poi-checkpoint', label: 'Checkpoint', description: 'Place POI' }
]

const FRIENDLY_FORCE_TOOL_CONFIG = {
  'friendly-soldier': {
    nodeType: 'soldier',
    idPrefix: 'soldier',
    role: 'operator-node',
    labelPrefix: 'Soldier Operator',
    defaultBehavior: 'lurk',
    transmissionRange: 400,
    render: {
      shape: 'square',
      color: '#8B5CF6',
      radius: 14
    }
  },
  'friendly-compute': {
    nodeType: 'compute',
    idPrefix: 'compute',
    role: 'compute-drone',
    labelPrefix: 'Compute Drone',
    defaultBehavior: 'lurk',
    transmissionRange: 420,
    render: {
      shape: 'diamond',
      color: '#1E3A8A',
      radius: 16
    }
  },
  'friendly-recon': {
    nodeType: 'recon',
    idPrefix: 'recon',
    role: 'recon-drone',
    labelPrefix: 'Recon Drone',
    defaultBehavior: 'lurk',
    transmissionRange: 170,
    detectionRadius: 220,
    speed: 95,
    render: {
      shape: 'triangle',
      color: '#7DD3FC',
      radius: 13
    }
  },
  'friendly-attack': {
    nodeType: 'attack',
    idPrefix: 'attack',
    role: 'attack-drone',
    labelPrefix: 'Attack Drone',
    defaultBehavior: 'lurk',
    transmissionRange: 160,
    speed: 120,
    render: {
      shape: 'star',
      color: '#7DD3FC',
      radius: 15
    }
  }
}

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

  const mapOverlay = {
    ...DEFAULT_MAP_OVERLAY,
    ...(state.map_overlay || {})
  }
  if (mapOverlay.asset_url) {
    mapOverlay.asset_url = resolveScenarioAssetUrl(mapOverlay.asset_url)
  }

  return {
    ...state,
    operator_context: {
      ...DEFAULT_OPERATOR_CONTEXT,
      ...(state.operator_context || {}),
      available_operators: Array.isArray(state.operator_context?.available_operators)
        ? state.operator_context.available_operators
        : DEFAULT_OPERATOR_CONTEXT.available_operators
    },
    search_state: {
      ...DEFAULT_SEARCH_STATE,
      ...(state.search_state || {}),
      target_tasks: Array.isArray(state.search_state?.target_tasks)
        ? state.search_state.target_tasks
        : DEFAULT_SEARCH_STATE.target_tasks,
      engagements: Array.isArray(state.search_state?.engagements)
        ? state.search_state.engagements
        : DEFAULT_SEARCH_STATE.engagements
    },
    map_overlay: mapOverlay,
    enemies: Array.isArray(state.enemies) ? state.enemies : [],
    structures: Array.isArray(state.structures) ? state.structures : [],
    special_entities: Array.isArray(state.special_entities) ? state.special_entities : [],
    nodes: Array.isArray(state.nodes) ? state.nodes : [],
    edges: Array.isArray(state.edges) ? state.edges : [],
    propagation_order: Array.isArray(state.propagation_order) ? state.propagation_order : [],
    total_propagation_ms: Number(state.total_propagation_ms) || 0,
    events: Array.isArray(state.events) ? state.events : [],
    object_reports: Array.isArray(state.object_reports) ? state.object_reports : [],
    simulation_settings: {
      ...DEFAULT_SIMULATION_SETTINGS,
      ...(state.simulation_settings || {})
    },
    command_id: state.command_id || null,
    pending_execute: typeof state.pending_execute === 'object' && state.pending_execute !== null
      ? state.pending_execute
      : { present: false }
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

const buildAvailableSoldiers = (state) => {
  const operatorIds = Array.isArray(state?.operator_context?.available_operators)
    ? state.operator_context.available_operators
    : []

  const fallbackIds = ['soldier-1', 'soldier-2']
  const soldierIds = operatorIds.length > 0 ? operatorIds : fallbackIds

  return soldierIds.map((soldierId, index) => {
    const nodeRecord = getSelectedDroneRecord(state, soldierId)
    return {
      id: soldierId,
      label: nodeRecord ? getEntityDisplayLabel(nodeRecord) : sanitizeUnitIdentifiers(soldierId),
      index
    }
  })
}

const buildCommandHistoryEntry = (payload, fallbackOrigin = 'unknown') => {
  if (!payload || typeof payload !== 'object') return null

  const commandText = String(payload.transcribed_text || payload.message || '').trim()
  if (!commandText) return null
  const status = ['report_review', 'command_pending', 'command_canceled', 'command_ignored'].includes(payload.event)
    ? (payload.status || 'unknown')
    : (payload.search_state?.mission_status || payload.status || 'unknown')

  return {
    commandId: payload.command_id || null,
    timestamp: payload.timestamp || new Date().toISOString(),
    origin: payload.origin || payload.operator_context?.active_operator || fallbackOrigin || 'unknown',
    command: commandText,
    status,
    goal: payload.parsed_command?.goal || payload.action_code || 'UNKNOWN',
    executionState: payload.parsed_command?.execution_state || 'NONE'
  }
}

const getCommandHistoryKey = (entry) => {
  if (!entry) return null
  if (entry.commandId) return entry.commandId
  return [
    entry.timestamp,
    entry.origin,
    entry.goal,
    entry.status,
    entry.executionState,
    entry.command
  ].join('|')
}

const COMMAND_INPUT_SOURCE_META = {
  'browser-text-command': {
    label: 'Command Center Input',
    summary: 'Command Center',
    detail: 'Direct browser-issued command',
    badgeClass: 'border-slate-300/40 bg-slate-500/10 text-slate-100'
  },
  'browser-push-to-talk': {
    label: 'Browser Mic Active',
    summary: 'Browser Mic',
    detail: 'Push-to-talk audio captured in the browser',
    badgeClass: 'border-emerald-300/40 bg-emerald-500/10 text-emerald-100'
  },
  'jetson-wakeword': {
    label: 'Jetson Mic Pipeline',
    summary: 'Jetson Mic',
    detail: 'Wake-word audio uplink received from Jetson',
    badgeClass: 'border-sky-300/50 bg-sky-500/10 text-sky-100'
  },
  'jetson-esp32-ptt': {
    label: 'ESP32 Signal Received',
    summary: 'ESP32 Signal',
    detail: 'ESP32 push-to-talk relayed through the Jetson pipeline',
    badgeClass: 'border-cyan-200/70 bg-cyan-500/15 text-cyan-50'
  }
}

const getCommandInputSourceMeta = (inputSource) => (
  COMMAND_INPUT_SOURCE_META[inputSource] || {
    label: 'Signal Path Unknown',
    summary: 'Unknown Path',
    detail: 'No command ingress metadata was reported',
    badgeClass: 'border-white/20 bg-white/10 text-white'
  }
)

const buildCurrentCommandState = (payload, fallbackOrigin = 'unknown') => {
  const inputSource = payload.input_source || 'unknown'
  const inputSourceMeta = getCommandInputSourceMeta(inputSource)

  return {
    commandId: payload.command_id || null,
    timestamp: new Date().toLocaleTimeString(),
    origin: payload.origin || payload.operator_context?.active_operator || fallbackOrigin,
    target: payload.target_location || 'Unknown',
    status: payload.search_state?.mission_status || payload.status || 'processing',
    nodes: payload.active_nodes?.length || payload.nodes?.length || 0,
    totalTime: `${(payload.total_propagation_ms || 0).toFixed(0)}ms`,
    message: payload.confirmation_text || payload.message || '',
    pendingExecute: Boolean(payload.pending_execute?.present),
    callsign: payload.parsed_command?.callsign || 'JARVIS',
    goal: payload.parsed_command?.goal || payload.action_code || 'UNKNOWN',
    executionState: payload.parsed_command?.execution_state || payload.execution_state || 'NONE',
    inputSource,
    inputSourceLabel: inputSourceMeta.label,
    inputSourceSummary: inputSourceMeta.summary,
    inputSourceDetail: inputSourceMeta.detail,
    inputSourceBadgeClass: inputSourceMeta.badgeClass
  }
}

const getCurrentCommandDirective = (payload) => {
  const eventName = payload?.event
  const goal = payload?.parsed_command?.goal || payload?.action_code || ''

  if (eventName === 'command_canceled') return 'clear'
  if (goal === 'ABORT' || goal === 'DISREGARD') return 'clear'
  if (eventName === 'report_review' || goal === 'REVIEW_REPORTS') return 'keep'
  if (eventName === 'command_ignored' || goal === 'NO_OP') return 'keep'
  if (!payload?.status && !eventName) return 'keep'
  return 'set'
}

const shouldApplyPayloadState = (payload) => payload?.event !== 'report_review'

const formatMissionStatus = (status) => String(status || 'processing').replace(/_/g, ' ')

const RECON_GOALS = new Set(['SCAN_AREA', 'REVIEW_REPORTS', 'MARK'])
const MOVEMENT_GOALS = new Set(['MOVE_TO', 'LOITER', 'HOLD_POSITION', 'STANDBY', 'AVOID_AREA'])
const STRIKE_GOALS = new Set(['ATTACK_AREA', 'EXECUTE', 'ABORT', 'DISREGARD'])

const getCurrentCommandTone = (command) => {
  const goal = String(command?.goal || 'UNKNOWN').toUpperCase()
  const executionState = String(command?.executionState || 'NONE').toUpperCase()

  if (command?.pendingExecute || executionState === 'PENDING_EXECUTE') {
    return {
      missionLabel: 'Execute Confirmation Required',
      missionSummary: 'Operator approval is still required before this task can be actioned.',
      bannerClass: 'border-amber-400 bg-gradient-to-r from-amber-950/95 via-orange-950/95 to-stone-950/95',
      titleClass: 'text-amber-100',
      missionBadgeClass: 'border-amber-300/60 bg-amber-400/15 text-amber-100',
      statusBadgeClass: 'border-amber-200/60 bg-amber-300/15 text-amber-50',
      statCardClass: 'border-amber-100/10 bg-black/25',
      messageClass: 'border-amber-300/20 bg-amber-300/10 text-amber-50/90',
      detailClass: 'text-amber-50/75'
    }
  }

  if (RECON_GOALS.has(goal)) {
    return {
      missionLabel: 'Recon Task',
      missionSummary: 'Immediate reconnaissance or marking task with no execute gate required.',
      bannerClass: 'border-cyan-400 bg-gradient-to-r from-slate-950/95 via-cyan-950/95 to-teal-950/95',
      titleClass: 'text-cyan-50',
      missionBadgeClass: 'border-cyan-300/60 bg-cyan-400/15 text-cyan-50',
      statusBadgeClass: 'border-teal-200/50 bg-teal-300/15 text-teal-50',
      statCardClass: 'border-cyan-100/10 bg-black/25',
      messageClass: 'border-cyan-300/20 bg-cyan-300/10 text-cyan-50/90',
      detailClass: 'text-cyan-50/75'
    }
  }

  if (MOVEMENT_GOALS.has(goal)) {
    return {
      missionLabel: 'Mobility Task',
      missionSummary: 'Immediate positioning or hold instruction for the active network.',
      bannerClass: 'border-sky-400 bg-gradient-to-r from-slate-950/95 via-sky-950/95 to-indigo-950/95',
      titleClass: 'text-sky-50',
      missionBadgeClass: 'border-sky-300/60 bg-sky-400/15 text-sky-50',
      statusBadgeClass: 'border-indigo-200/50 bg-indigo-300/15 text-indigo-50',
      statCardClass: 'border-sky-100/10 bg-black/25',
      messageClass: 'border-sky-300/20 bg-sky-300/10 text-sky-50/90',
      detailClass: 'text-sky-50/75'
    }
  }

  if (STRIKE_GOALS.has(goal)) {
    return {
      missionLabel: 'Strike Task',
      missionSummary: 'Mission payload is destructive or conflict-critical and should remain highly visible.',
      bannerClass: 'border-rose-500 bg-gradient-to-r from-rose-950/95 via-red-950/95 to-slate-950/95',
      titleClass: 'text-rose-50',
      missionBadgeClass: 'border-rose-300/60 bg-rose-400/15 text-rose-50',
      statusBadgeClass: 'border-red-200/50 bg-red-300/15 text-red-50',
      statCardClass: 'border-rose-100/10 bg-black/25',
      messageClass: 'border-rose-300/20 bg-rose-300/10 text-rose-50/90',
      detailClass: 'text-rose-50/75'
    }
  }

  return {
    missionLabel: 'Mission Update',
    missionSummary: 'Latest command received from the operator pipeline.',
    bannerClass: 'border-slate-500 bg-gradient-to-r from-slate-950/95 via-gray-950/95 to-slate-900/95',
    titleClass: 'text-white',
    missionBadgeClass: 'border-slate-300/40 bg-slate-400/10 text-slate-100',
    statusBadgeClass: 'border-slate-200/40 bg-slate-300/10 text-slate-50',
    statCardClass: 'border-white/10 bg-black/25',
    messageClass: 'border-white/10 bg-white/5 text-gray-100',
    detailClass: 'text-gray-200/75'
  }
}

const normalizeSuggestedCommands = (commands) => {
  const values = typeof commands === 'string'
    ? commands.split(/\r?\n/)
    : Array.isArray(commands)
      ? commands
      : []

  const normalized = []
  values.forEach((value) => {
    const command = String(value || '').trim()
    if (command && !normalized.includes(command)) {
      normalized.push(command)
    }
  })
  return normalized
}

const serializeSuggestedCommands = (commands) => normalizeSuggestedCommands(commands).join('\n')
const DEFAULT_SUGGESTED_COMMANDS_TEXT = DEFAULT_SUGGESTED_COMMANDS.join('\n')

const getNextNodeId = (nodes, prefix) => {
  const pattern = new RegExp(`^${prefix}-(\\d+)$`)
  const nextIndex = (nodes || []).reduce((highest, node) => {
    const match = pattern.exec(String(node?.id || ''))
    if (!match) return highest
    return Math.max(highest, Number(match[1]) || 0)
  }, 0) + 1
  return `${prefix}-${nextIndex}`
}

function App() {
  const [activePage, setActivePage] = useState(getPageFromHash)
  const [swarmState, setSwarmState] = useState(null)
  const [scenarioCatalog, setScenarioCatalog] = useState([])
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('')
  const [scenarioName, setScenarioName] = useState('Blank Workspace')
  const [scenarioNameDirty, setScenarioNameDirty] = useState(false)
  const [suggestedCommandsText, setSuggestedCommandsText] = useState('')
  const [events, setEvents] = useState([])
  const [currentCommand, setCurrentCommand] = useState(null)
  const [missionBannerCollapsed, setMissionBannerCollapsed] = useState(false)
  const [communicationPlayback, setCommunicationPlayback] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [commandHistory, setCommandHistory] = useState([])
  const [activeSoldier, setActiveSoldier] = useState('soldier-1')
  const [soldierStatus, setSoldierStatus] = useState(null)
  const [selectedDrone, setSelectedDrone] = useState(null)
  const [selectedMapEntity, setSelectedMapEntity] = useState(null)
  const [mapMode, setMapMode] = useState('nato')
  const [showEntityLabels, setShowEntityLabels] = useState(true)
  const [mapFullscreenActive, setMapFullscreenActive] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editorTool, setEditorTool] = useState('select')
  const [editorStatus, setEditorStatus] = useState('Map editor ready')
  const [editorBusy, setEditorBusy] = useState(false)
  const [scenarioBusy, setScenarioBusy] = useState(false)
  const [collapsedPanels, setCollapsedPanels] = useState(DEFAULT_COLLAPSED_PANELS)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const isCleaningUpRef = useRef(false)
  const seenCommandHistoryKeysRef = useRef(new Set())
  const overlayInputRef = useRef(null)
  const mapShellRef = useRef(null)
  const entityIdSequenceRef = useRef(1)
  const activeScenarioKeyRef = useRef('')
  const scenarioNameDirtyRef = useRef(false)
  const suggestedCommandsDirtyRef = useRef(false)
  const scenarioSelectionDirtyRef = useRef(false)
  const lastPlaybackKeyRef = useRef(null)
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 2000
  const activeView = getViewOption(activePage)

  useEffect(() => {
    const syncPageFromHash = () => {
      setActivePage(getPageFromHash())
    }

    window.addEventListener('hashchange', syncPageFromHash)
    return () => {
      window.removeEventListener('hashchange', syncPageFromHash)
    }
  }, [])

  useEffect(() => {
    document.title = activeView.documentTitle
  }, [activeView])

  const syncScenarioDrafts = (scenarioInfo, options = {}) => {
    const nextScenarioKey = scenarioInfo?.relative_path || ''
    const nextScenarioName = scenarioInfo?.name || 'Blank Workspace'
    const nextSuggestedCommands = serializeSuggestedCommands(scenarioInfo?.suggested_commands)
    const scenarioChanged = activeScenarioKeyRef.current !== nextScenarioKey

    activeScenarioKeyRef.current = nextScenarioKey

    if (options.force || scenarioChanged || !scenarioSelectionDirtyRef.current) {
      setSelectedScenarioKey(nextScenarioKey)
      scenarioSelectionDirtyRef.current = false
    }

    if (options.force || scenarioChanged || !scenarioNameDirtyRef.current) {
      setScenarioName(nextScenarioName)
      scenarioNameDirtyRef.current = false
      setScenarioNameDirty(false)
    }

    if (options.force || scenarioChanged || !suggestedCommandsDirtyRef.current) {
      setSuggestedCommandsText(nextSuggestedCommands)
      suggestedCommandsDirtyRef.current = false
    }
  }

  const togglePanel = (panelId) => {
    setCollapsedPanels((previous) => ({
      ...previous,
      [panelId]: !previous[panelId]
    }))
  }

  const handlePageChange = (pageId) => {
    const nextHash = pageId === PAGE_COMMAND_CENTER ? '' : `#${pageId}`
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash
      return
    }
    setActivePage(pageId)
  }

  const applyIncomingState = (payload, options = {}) => {
    const normalized = normalizeSwarmState(payload)
    if (!normalized) return null
    setSwarmState(normalized)
    setEvents(normalized.events || [])
    if (normalized.operator_context?.active_operator) {
      setActiveSoldier(normalized.operator_context.active_operator)
    }
    syncScenarioDrafts(normalized.scenario_info, options)
    return normalized
  }

  const queueCommunicationPlayback = (payload) => {
    const propagationOrder = Array.isArray(payload?.propagation_order) ? payload.propagation_order : []
    const playbackSteps = propagationOrder
      .map((step) => ({
        node: step?.node,
        via: step?.via || step?.from || null,
        hop: Number(step?.hop) || 0,
        timestamp_ms: Number(step?.timestamp_ms) || 0
      }))
      .filter((step) => step.node && step.via && step.node !== step.via)

    if (playbackSteps.length === 0) return

    const playbackKey = payload?.command_id || [
      payload?.timestamp || '',
      payload?.origin || '',
      payload?.target_location || '',
      playbackSteps.map((step) => `${step.via}>${step.node}@${step.timestamp_ms}`).join('|')
    ].join('::')

    if (!playbackKey || lastPlaybackKeyRef.current === playbackKey) {
      return
    }

    lastPlaybackKeyRef.current = playbackKey
    setCommunicationPlayback({
      key: playbackKey,
      startedAtMs: Date.now(),
      slowdownFactor: Math.max(1, Number(payload?.simulation_settings?.slowdown_factor) || 1),
      steps: playbackSteps
    })
  }

  const pushCommandHistoryEntry = (payload, fallbackOrigin = activeSoldier) => {
    const entry = buildCommandHistoryEntry(payload, fallbackOrigin)
    if (!entry) return

    const historyKey = getCommandHistoryKey(entry)
    if (!historyKey || seenCommandHistoryKeysRef.current.has(historyKey)) {
      return
    }

    seenCommandHistoryKeysRef.current.add(historyKey)
    setCommandHistory((previous) => {
      const next = [...previous, entry]
      return next.length > 100 ? next.slice(-100) : next
    })
  }

  const nextEntityId = (prefix) => `${prefix}-${Date.now()}-${entityIdSequenceRef.current++}`

  const refreshScenarioCatalog = async () => {
    try {
      const response = await fetch(resolveApiUrl('/api/scenarios'))
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Scenario list request failed')
      }
      setScenarioCatalog(Array.isArray(result.scenarios) ? result.scenarios : [])
      syncScenarioDrafts(result.active_scenario)
    } catch (error) {
      console.error('[App] Failed to fetch scenario catalog:', error)
    }
  }

  const pushEditorPayload = async (payload, successMessage) => {
    setEditorBusy(true)
    try {
      const response = await fetch(resolveApiUrl('/api/map-editor/state'), {
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

  const applySimulationSettingsMutation = async (updates) => {
    try {
      const response = await fetch(resolveApiUrl('/api/simulation-settings'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || result.message || 'Simulation settings update failed')
      }
      applyIncomingState(result)
      return result
    } catch (error) {
      console.error('[App] Simulation settings update failed:', error)
      return null
    }
  }

  const fetchSoldierStatus = async (soldierId) => {
    if (!soldierId) {
      setSoldierStatus(null)
      return
    }

    try {
      const response = await fetch(resolveApiUrl(`/api/soldier/${soldierId}/status`))
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Soldier status request failed')
      }

      setSoldierStatus({
        status: 'online',
        pending_commands: data.pending_commands || 0,
        last_mission: data.last_mission_id || null
      })
    } catch (error) {
      console.error('[App] Failed to fetch soldier status:', error)
      setSoldierStatus({
        status: 'offline',
        pending_commands: 0,
        last_mission: null
      })
    }
  }

  useEffect(() => {
    if (typeof document === 'undefined') return undefined

    const syncMapFullscreenState = () => {
      const fullscreenElement = getActiveFullscreenElement()
      const mapShell = mapShellRef.current
      setMapFullscreenActive(Boolean(fullscreenElement && mapShell && fullscreenElement === mapShell))
    }

    syncMapFullscreenState()
    document.addEventListener('fullscreenchange', syncMapFullscreenState)
    document.addEventListener('webkitfullscreenchange', syncMapFullscreenState)

    return () => {
      document.removeEventListener('fullscreenchange', syncMapFullscreenState)
      document.removeEventListener('webkitfullscreenchange', syncMapFullscreenState)
    }
  }, [])

  useEffect(() => {
    isCleaningUpRef.current = false

    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return () => {}
    }

    const connectWebSocket = () => {
      if (isCleaningUpRef.current) return

      const wsUrl = resolveWebSocketUrl()

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
            data.event === 'report_review' ||
            data.event === 'command_pending' ||
            data.event === 'command_canceled' ||
            data.event === 'command_ignored'
          ) {
            console.log('[App] Updating swarm state from command response')
            if (shouldApplyPayloadState(data)) {
              applyIncomingState(data)
            }
            queueCommunicationPlayback(data)
            pushCommandHistoryEntry(data, data.origin || data.operator_context?.active_operator || activeSoldier)
            if (data.origin) {
              setSelectedDrone(data.origin)
              setSelectedMapEntity(null)
            }
            const currentCommandDirective = getCurrentCommandDirective(data)
            if (currentCommandDirective === 'clear') {
              setCurrentCommand(null)
            } else if (currentCommandDirective === 'set') {
              setCurrentCommand(buildCurrentCommandState(data, activeSoldier))
            }
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

  useEffect(() => {
    if (!currentCommand) {
      return
    }
    setMissionBannerCollapsed(false)
  }, [currentCommand?.commandId, currentCommand?.timestamp])

  useEffect(() => {
    void fetchSoldierStatus(activeSoldier)
  }, [activeSoldier])

  const handleVoiceCommand = async (transcript) => {
    try {
      let response
      let historyCommand = typeof transcript === 'string' ? transcript : 'Processing audio...'
      const originPayload = {
        origin: activeSoldier,
        operator_node: activeSoldier,
        input_source: 'browser-text-command'
      }

      if (typeof transcript === 'string') {
        response = await fetch(resolveApiUrl('/api/voice-command'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcribed_text: transcript,
            ...originPayload
          })
        })
      } else {
        const formData = new FormData()
        const extension = transcript.mimeType?.includes('ogg')
          ? 'ogg'
          : transcript.mimeType?.includes('wav')
            ? 'wav'
            : 'webm'

        formData.append('audio', transcript.audioBlob, `recording.${extension}`)
        formData.append('origin', activeSoldier)
        formData.append('operator_node', activeSoldier)
        formData.append('input_source', 'browser-push-to-talk')
        response = await fetch(resolveApiUrl('/api/transcribe-command'), {
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

      pushCommandHistoryEntry(
        {
          ...result,
          transcribed_text: transcriptText
        },
        activeSoldier
      )

      if (result.nodes?.length && shouldApplyPayloadState(result)) {
        applyIncomingState(result)
      }
      queueCommunicationPlayback(result)

      if (result.origin) {
        setSelectedDrone(result.origin)
        setSelectedMapEntity(null)
      }

      if (result.status) {
        const currentCommandDirective = getCurrentCommandDirective(result)
        if (currentCommandDirective === 'clear') {
          setCurrentCommand(null)
        } else if (currentCommandDirective === 'set') {
          setCurrentCommand(buildCurrentCommandState(result, activeSoldier))
        }
      }

      console.log('[App] Command sent:', result)
      return result
    } catch (error) {
      console.error('[App] Error sending command:', error)
      return { error: error.message }
    }
  }

  const handleSoldierChange = async (soldierId) => {
    const previousSoldier = activeSoldier
    setActiveSoldier(soldierId)
    try {
      const response = await fetch(resolveApiUrl('/api/operator-context'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_operator: soldierId })
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Operator context update failed')
      }
      applyIncomingState(data)
    } catch (error) {
      console.error('[App] Failed to update operator context:', error)
      setActiveSoldier(previousSoldier)
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

    const friendlyForce = FRIENDLY_FORCE_TOOL_CONFIG[descriptor.tool]
    if (friendlyForce) {
      const typedNodes = payload.drones.filter((node) => node.type === friendlyForce.nodeType)
      const nodeRecord = {
        id: getNextNodeId(payload.drones, friendlyForce.idPrefix),
        label: `${friendlyForce.labelPrefix} ${typedNodes.length + 1}`,
        type: friendlyForce.nodeType,
        role: friendlyForce.role,
        behavior: friendlyForce.defaultBehavior,
        position: descriptor.position,
        transmission_range: friendlyForce.transmissionRange,
        render: friendlyForce.render
      }

      if (typeof friendlyForce.detectionRadius === 'number') {
        nodeRecord.detection_radius = friendlyForce.detectionRadius
      }
      if (typeof friendlyForce.speed === 'number') {
        nodeRecord.speed = friendlyForce.speed
      }

      payload.drones.push(nodeRecord)
      setSelectedDrone(nodeRecord.id)
      setSelectedMapEntity(null)
      await pushEditorPayload(payload, `${friendlyForce.labelPrefix} placed`)
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

  const handleMapFullscreenToggle = async () => {
    const mapShell = mapShellRef.current
    if (!mapShell) return

    try {
      if (getActiveFullscreenElement() === mapShell) {
        await exitActiveFullscreen()
        return
      }

      await requestFullscreenForElement(mapShell)
    } catch (error) {
      console.error('[App] Unable to toggle map fullscreen:', error)
    }
  }

  const handleOverlayUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setEditorBusy(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(resolveApiUrl('/api/map-editor/overlay'), {
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
      const response = await fetch(resolveApiUrl('/api/map-editor/save'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_name: scenarioName.trim(),
          suggested_commands: normalizeSuggestedCommands(suggestedCommandsText)
        })
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
      const response = await fetch(resolveApiUrl('/api/scenarios/load'), {
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
  const availableSoldiers = buildAvailableSoldiers(swarmState)
  const activeSoldierRecord = getSelectedDroneRecord(swarmState, activeSoldier)
  const activeSoldierLabel = activeSoldierRecord
    ? getEntityDisplayLabel(activeSoldierRecord)
    : sanitizeUnitIdentifiers(activeSoldier)
  const overlayState = swarmState?.map_overlay || DEFAULT_MAP_OVERLAY
  const simulationSettings = swarmState?.simulation_settings || DEFAULT_SIMULATION_SETTINGS
  const simulationSlowdownFactor = Math.max(1, Number(simulationSettings.slowdown_factor) || 1)
  const simulationSlowdownLabel = simulationSlowdownFactor === 1
    ? 'Real-time'
    : `${simulationSlowdownFactor}x slower`
  const activeScenarioInfo = swarmState?.scenario_info || null
  const currentSuggestedCommands = normalizeSuggestedCommands(suggestedCommandsText)
  const displayedSuggestedCommands = currentSuggestedCommands.length > 0
    ? currentSuggestedCommands
    : DEFAULT_SUGGESTED_COMMANDS
  const currentCommandTone = currentCommand ? getCurrentCommandTone(currentCommand) : null
  const currentCommandStatusLabel = currentCommand ? formatMissionStatus(currentCommand.status) : ''
  const currentCommandOriginLabel = currentCommand
    ? sanitizeUnitIdentifiers(currentCommand.origin || 'unknown')
    : 'unknown'
  const currentCommandStats = currentCommand
    ? [
        { label: 'Origin', value: currentCommandOriginLabel },
        { label: 'Status', value: currentCommandStatusLabel },
        { label: 'Active Nodes', value: `${currentCommand.nodes}` },
        { label: 'Propagation', value: currentCommand.totalTime }
      ]
    : []
  const saveButtonLabel = activeScenarioInfo?.relative_path === 'swarm_initial_state.json'
    ? 'Save New Scenario'
    : 'Save Scenario'

  return (
    <div className="app min-h-screen bg-gray-900 text-white">
      <header className="bg-black border-b border-red-500 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">JARVIS Frontend Suite</h1>
            <p className="text-gray-400">
              {activeView.description}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {VIEW_OPTIONS.map((view) => {
                const isActive = activePage === view.id
                return (
                  <button
                    key={view.id}
                    type="button"
                    onClick={() => handlePageChange(view.id)}
                    className={`rounded border px-3 py-2 text-left transition ${
                      isActive
                        ? 'border-cyan-400 bg-cyan-500/15 text-cyan-100'
                        : 'border-gray-700 bg-gray-900 text-gray-300 hover:border-gray-500 hover:bg-gray-800'
                    }`}
                  >
                    <div className="text-xs font-bold uppercase tracking-[0.16em]">{view.label}</div>
                    <div className="mt-0.5 text-[10px] text-gray-400">{view.subtitle}</div>
                  </button>
                )
              })}
            </div>
          </div>
          <div className={`text-center rounded px-4 py-2 ${connectionStatus === 'connected' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'}`}>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] opacity-80">Live Backend</p>
            <p className="text-sm font-bold">
              {connectionStatus === 'connected' ? 'CONNECTED' : 'DISCONNECTED'}
            </p>
          </div>
        </div>
      </header>

      {activePage === PAGE_COMMAND_CENTER && currentCommand && (
        <div className={`sticky top-0 z-30 border-b-4 shadow-xl backdrop-blur ${currentCommandTone.bannerClass}`}>
          <div className={`px-4 md:px-6 ${missionBannerCollapsed ? 'py-3' : 'py-4'}`}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <p className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] ${currentCommandTone.missionBadgeClass}`}>
                    {currentCommandTone.missionLabel}
                  </p>
                  {currentCommand.inputSourceLabel && (
                    <p className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${currentCommand.inputSourceBadgeClass}`}>
                      {currentCommand.inputSourceLabel}
                    </p>
                  )}
                  <p className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${currentCommandTone.statusBadgeClass}`}>
                    {currentCommandStatusLabel}
                  </p>
                  {currentCommand.pendingExecute && (
                    <p className="inline-flex rounded-full border border-amber-200/60 bg-amber-300/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-50">
                      Awaiting Execute
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap items-start gap-3">
                  <h2 className={`min-w-0 truncate font-bold ${currentCommandTone.titleClass} ${missionBannerCollapsed ? 'text-2xl' : 'text-3xl md:text-[2rem]'}`}>
                    {currentCommand.target || 'UNKNOWN'}
                  </h2>
                </div>
                {!missionBannerCollapsed && (
                  <p className={`mt-2 max-w-3xl text-sm ${currentCommandTone.detailClass}`}>
                    {currentCommandTone.missionSummary}
                  </p>
                )}
              </div>
              <div className="ml-auto flex items-center gap-3 text-right text-sm text-gray-300">
                <div>
                  <p>{currentCommand.timestamp}</p>
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">
                    {currentCommand.goal.replace(/_/g, ' ')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setMissionBannerCollapsed((previous) => !previous)}
                  className="rounded border border-white/20 bg-black/20 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-100 transition hover:border-white/40 hover:bg-black/35"
                >
                  {missionBannerCollapsed ? 'Expand' : 'Collapse'}
                </button>
              </div>
            </div>

            {missionBannerCollapsed ? (
              <div className="mt-3 flex flex-wrap gap-2 text-sm text-gray-100">
                {currentCommandStats.map((item) => (
                  <span
                    key={item.label}
                    className={`inline-flex rounded-full border px-3 py-1 ${currentCommandTone.statCardClass}`}
                  >
                    <span className="mr-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400">{item.label}</span>
                    <span className="font-medium text-gray-100">{item.value}</span>
                  </span>
                ))}
                <span className={`inline-flex rounded-full border px-3 py-1 ${currentCommandTone.statCardClass}`}>
                  <span className="mr-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-400">Signal</span>
                  <span className="font-medium text-gray-100">{currentCommand.inputSourceSummary}</span>
                </span>
              </div>
            ) : (
              <div className="mt-4 flex flex-col gap-3">
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
                  <div className={`rounded-2xl border p-4 ${currentCommandTone.statCardClass}`}>
                    <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-gray-400">Signal Path</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <p className="text-lg font-bold text-white">{currentCommand.inputSourceSummary}</p>
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${currentCommand.inputSourceBadgeClass}`}>
                        {currentCommand.callsign}
                      </span>
                    </div>
                    <p className={`mt-2 text-sm ${currentCommandTone.detailClass}`}>
                      {currentCommand.inputSourceDetail}
                    </p>
                  </div>
                  <div className={`rounded-2xl border p-4 ${currentCommandTone.messageClass}`}>
                    <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-gray-400">Operator Message</p>
                    <p className={`mt-2 text-sm leading-6 ${currentCommand.message ? 'text-white' : currentCommandTone.detailClass}`}>
                      {currentCommand.message || 'Command received and pinned for live mission awareness.'}
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {currentCommandStats.map((item) => (
                    <div key={item.label} className={`rounded-2xl border p-4 ${currentCommandTone.statCardClass}`}>
                      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-gray-400">{item.label}</p>
                      <p className="mt-2 text-xl font-semibold text-white">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activePage === PAGE_COMMAND_CENTER ? (
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
                    <div className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-cyan-100">
                      {MAP_MODE_OPTIONS.find((option) => option.id === mapMode)?.label || 'Map'}
                    </div>
                  </div>

                  <div className="mt-3">
                    <CollapsiblePanel
                      title="Map Mode"
                      subtitle="Change symbol style, label visibility, and replay pacing."
                      collapsed={collapsedPanels.mapMode}
                      onToggle={() => togglePanel('mapMode')}
                      className="border-gray-600 bg-gray-950/70"
                      bodyClassName="p-2"
                    >
                      <div className="flex gap-2">
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
                      <div className="mt-3 rounded border border-gray-700 bg-gray-900/60 px-3 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-gray-300">Simulation Slowdown</div>
                            <div className="text-[10px] text-gray-500">Communication links replay against this factor and fade over 3 seconds.</div>
                          </div>
                          <div className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-cyan-100">
                            {simulationSlowdownLabel}
                          </div>
                        </div>
                        <label className="mt-3 block text-xs text-gray-300">
                          <span className="mb-1 block">Slowdown Factor: {simulationSlowdownFactor}x</span>
                          <input
                            type="range"
                            min="1"
                            max="100"
                            value={simulationSlowdownFactor}
                            onChange={(event) => {
                              void applySimulationSettingsMutation({ slowdown_factor: Number(event.target.value) })
                            }}
                            className="w-full"
                          />
                        </label>
                      </div>
                    </CollapsiblePanel>
                  </div>

                  <div
                    ref={mapShellRef}
                    className="map-shell mt-3 rounded border border-gray-700 bg-gray-950/40 p-3"
                  >
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-gray-500">
                        {mapFullscreenActive ? 'Fullscreen map active' : 'Expand map to fullscreen'}
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          void handleMapFullscreenToggle()
                        }}
                        className="rounded border border-cyan-500/60 bg-cyan-500/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-cyan-100 transition hover:bg-cyan-500/20"
                      >
                        {mapFullscreenActive ? 'Exit Full Screen' : 'Maximize Map'}
                      </button>
                    </div>

                    <div className="map-shell-frame">
                      <div className="map-shell-stage">
                        {swarmState ? (
                          <SwarmCanvas
                            state={swarmState}
                            communicationPlayback={communicationPlayback}
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
                          <div className="flex min-h-[24rem] items-center justify-center rounded bg-gray-900">
                            <p className="text-gray-500">Awaiting swarm state...</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <CollapsiblePanel
                    title="Scenario Loader"
                    subtitle={activeScenarioInfo
                      ? `Active: ${activeScenarioInfo.name}`
                      : 'Select a blank or saved scenario to load.'}
                    collapsed={collapsedPanels.scenarioLoader}
                    onToggle={() => togglePanel('scenarioLoader')}
                    className="border-gray-600 bg-gray-900/70"
                    bodyClassName="p-3"
                  >
                    <div className="rounded border border-gray-700 bg-gray-950/40 px-3 py-2 text-[10px] uppercase tracking-wide text-gray-400">
                      {activeScenarioInfo
                        ? `${activeScenarioInfo.node_count} nodes / ${activeScenarioInfo.structure_count} structures / ${activeScenarioInfo.suggested_command_count || 0} cmds`
                        : 'No active scenario loaded'}
                    </div>

                    <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                      <select
                        value={selectedScenarioKey}
                        onChange={(event) => {
                          setSelectedScenarioKey(event.target.value)
                          scenarioSelectionDirtyRef.current = true
                        }}
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
                          scenarioNameDirtyRef.current = true
                          setScenarioNameDirty(true)
                        }}
                        className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100"
                        placeholder="Scenario name"
                      />
                    </label>

                    <label className="mt-3 block text-xs text-gray-300">
                      <span className="mb-1 block">Suggested Commands</span>
                      <textarea
                        rows="5"
                        value={suggestedCommandsText}
                        onChange={(event) => {
                          setSuggestedCommandsText(event.target.value)
                          suggestedCommandsDirtyRef.current = true
                        }}
                        className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100"
                        placeholder={DEFAULT_SUGGESTED_COMMANDS_TEXT}
                      />
                    </label>

                    <div className="mt-2 text-[11px] text-gray-500">
                      Saving from the blank workspace creates a new scenario file in the library. Suggested commands are stored with the scenario metadata and shown in the side rail.
                    </div>
                  </CollapsiblePanel>

                  <CollapsiblePanel
                    title="Map Editor"
                    subtitle="Live scenario editing and save-to-config controls."
                    collapsed={collapsedPanels.mapEditor}
                    onToggle={() => togglePanel('mapEditor')}
                    className="border-gray-600 bg-gray-900/70"
                    bodyClassName="p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs text-gray-400">
                        Place, move, and remove units or map objects in the current scenario.
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
                  </CollapsiblePanel>
                </div>
              </div>

            </div>
          </div>

          <div className="w-full">
            <EventConsole events={events} maxVisible={20} />
          </div>
        </div>

        <div className="min-w-0 space-y-4">
          <div className="rounded border border-gray-700 bg-gray-800 p-4">
            <h3 className="mb-2 text-lg font-bold">Voice Command</h3>
            <p className="mb-4 text-xs text-gray-400">
              Use radio-style phrasing with sectors Alpha through Hotel and grid numbers 1 through 8.
            </p>
            <PushToTalkButton onCommand={handleVoiceCommand} activeSoldierLabel={activeSoldierLabel} />
          </div>

          <SoldierSelector
            activeSoldier={activeSoldier}
            availableSoldiers={availableSoldiers}
            onSoldierChange={handleSoldierChange}
            soldierStatus={soldierStatus}
          />

          <CollapsiblePanel
            title="System Status"
            subtitle="Connection health, mission state, and scenario diagnostics."
            collapsed={collapsedPanels.systemStatus}
            onToggle={() => togglePanel('systemStatus')}
            className="border-gray-700 bg-gray-800"
            bodyClassName="p-4"
          >
            <StatusPanel connectionStatus={connectionStatus} swarmState={swarmState} embedded />
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Suggested Commands"
            subtitle={activeScenarioInfo
              ? `Saved with ${activeScenarioInfo.name}`
              : 'Radio-style examples for Alpha-Hotel and grid 1-8.'}
            collapsed={collapsedPanels.suggestedCommands}
            onToggle={() => togglePanel('suggestedCommands')}
            className="border-gray-700 bg-gray-800"
            bodyClassName="p-4"
          >
            <div className="space-y-2">
              {displayedSuggestedCommands.map((command, index) => (
                <div key={`${command}-${index}`} className="rounded border border-cyan-500/30 bg-cyan-500/5 px-3 py-2">
                  <div className="text-[10px] font-bold uppercase tracking-wide text-cyan-200">
                    {currentSuggestedCommands.length > 0 ? `Suggestion ${index + 1}` : `Template ${index + 1}`}
                  </div>
                  <div className="mt-1 text-sm text-gray-100">{command}</div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-gray-500">
              Edit these in Scenario Loader, then save the scenario to persist them with the map.
            </p>
          </CollapsiblePanel>

          {selectedDroneRecord && (
            <CollapsiblePanel
              title="Selected Unit"
              subtitle={getEntityDisplayLabel(selectedDroneRecord)}
              collapsed={collapsedPanels.selectedUnit}
              onToggle={() => togglePanel('selectedUnit')}
              className="border-gray-700 bg-gray-800"
              bodyClassName="p-4"
            >
              <DroneStatusCard
                drone={selectedDroneRecord}
                commsStatus="online"
                embedded
              />
            </CollapsiblePanel>
          )}

          {selectedMapRecord && (
            <CollapsiblePanel
              title="Selected Map Object"
              subtitle={getEntityDisplayLabel(selectedMapRecord)}
              collapsed={collapsedPanels.selectedMapObject}
              onToggle={() => togglePanel('selectedMapObject')}
              className="border-gray-700 bg-gray-800"
              bodyClassName="p-4"
            >
              <div className="space-y-2">
                <div className="text-sm text-gray-300 capitalize">
                  {(selectedMapEntity?.kind || '').replace(/_/g, ' ')} / {(selectedMapRecord.subtype || selectedMapRecord.type || 'unknown').replace(/_/g, ' ')}
                </div>
                {Array.isArray(selectedMapRecord.position) && (
                  <div className="font-mono text-xs text-gray-400">
                    Position: {Math.round(selectedMapRecord.position[0])}, {Math.round(selectedMapRecord.position[1])}
                  </div>
                )}
              </div>
            </CollapsiblePanel>
          )}

          <CollapsiblePanel
            title="Legend"
            subtitle="Unit symbols, map markers, and interaction hints."
            collapsed={collapsedPanels.legend}
            onToggle={() => togglePanel('legend')}
            className="border-gray-700 bg-gray-800"
            bodyClassName="p-4"
          >
            <GridLegend activeDrones={swarmState?.nodes || []} mapMode={mapMode} embedded />
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Recent Commands"
            subtitle="Most recent voice and command-center requests."
            collapsed={collapsedPanels.recentCommands}
            onToggle={() => togglePanel('recentCommands')}
            className="border-gray-700 bg-gray-800"
            bodyClassName="p-4 min-h-[12rem] max-h-[20rem] overflow-y-auto"
          >
            {commandHistory.length === 0 ? (
              <p className="text-gray-500 text-sm">No commands yet</p>
            ) : (
              <div className="space-y-2">
                {commandHistory.slice(-5).map((cmd, index) => (
                  <div key={`${cmd.timestamp}-${index}`} className="bg-gray-900 p-2 rounded text-xs border-l-2 border-yellow-500">
                    <p className="text-[10px] uppercase tracking-wide text-amber-300">
                      {sanitizeUnitIdentifiers(cmd.origin || activeSoldier)}
                    </p>
                    <p className="font-mono text-gray-300">{cmd.command.substring(0, 40)}...</p>
                    <p className="text-xs text-blue-400">{cmd.goal}</p>
                    <p className="text-[10px] text-gray-500">{cmd.status} / {cmd.executionState}</p>
                  </div>
                ))}
              </div>
            )}
          </CollapsiblePanel>
        </div>
        </main>
      ) : activePage === PAGE_RELAY_COMPARISON ? (
        <ContestedRelayComparisonPage />
      ) : (
        <SwarmPropagationLabPage />
      )}
    </div>
  )
}

export default App
