# 4.0.0 Full-Stack Integration Setup Guide

> **Target**: Command UI + backend integration for JARVIS

This guide reflects the repo as it exists now: a consensus-first swarm simulation with a working FastAPI backend, React command center, and optional AI/audio adapters.

## What Is Already Wired

### Backend

File: `base_station/api/main.py`

Current endpoints and behavior:

- `GET /health`
- `GET /api/swarm-state`
- `POST /api/voice-command`
  - legacy route name
  - accepts direct structured swarm payloads
  - also accepts text commands routed through `ai_bridge.py`
- `POST /api/transcribe-command`
  - optional audio upload path
- `ws://localhost:8000/ws/swarm`

The backend is already integrated with:

- `base_station/core/swarm_logic.py`
- `base_station/core/ai_bridge.py`

It is **not yet fully wired** to `mqtt_client.py` for hardware publishing.

### Frontend

Files:

- `command_center/src/App.jsx`
- `command_center/src/components/SwarmGraph.jsx`
- `command_center/src/components/StatusPanel.jsx`
- `command_center/src/components/PushToTalkButton.jsx`

Current frontend behavior:

- opens a WebSocket to the backend
- renders topology and swarm state in real time
- tracks command history
- still exposes push-to-talk as an input path

The frontend works today, but the repo narrative should treat direct swarm commands and consensus behavior as primary.

## Local Setup

### Backend (PowerShell)

```powershell
cd base_station
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd command_center
npm install
npm run dev
```

Open:

- [http://localhost:8000/docs](http://localhost:8000/docs)
- [http://localhost:5173](http://localhost:5173)

## Recommended Integration View

### 1. Direct Command Path

This is the cleanest current path for the swarm demo:

```json
{
  "origin": "soldier-1",
  "target_location": "Grid Alpha",
  "action_code": "SEARCH",
  "consensus_algorithm": "gossip"
}
```

Submit that payload to `POST /api/voice-command`.

Even though the route name says "voice", the backend will bypass language parsing when a structured payload is already present.

### 2. Optional Text Command Path

Example:

```json
{
  "transcribed_text": "JARVIS, move swarm to Grid Alpha",
  "consensus_algorithm": "raft"
}
```

The backend will:

1. run `process_voice_command()`
2. normalize the result into a swarm intent
3. dispatch through the requested consensus algorithm

### 3. Optional Audio Path

The audio route is:

```text
POST /api/transcribe-command
```

Use this only when you specifically want to demo audio input. It should not be treated as the architectural center of the project.

## What the Swarm Runtime Produces

`swarm_logic.py` already returns:

- nodes and edges
- active nodes
- propagation order
- total propagation time
- delivery summary
- search state and engagements
- benchmark data
- supported algorithms

The key comparison exposed today is:

- `gossip`
- `raft`

The runtime also advertises future candidates such as PBFT and epidemic push-pull, but those are not implemented yet.

## WebSocket Contract

The frontend listens on:

```text
ws://localhost:8000/ws/swarm
```

Representative update:

```json
{
  "event": "gossip_update",
  "algorithm": "gossip",
  "status": "propagating",
  "active_nodes": ["gateway", "recon-1", "attack-1"],
  "total_propagation_ms": 184,
  "benchmark": {
    "latency": {
      "gossip_avg_ms": 0,
      "raft_avg_ms": 0
    }
  }
}
```

Note: the event name is still `gossip_update` for compatibility, even when the backend dispatches the TCP/Raft baseline.

## What Is Still Missing

- MQTT publisher wired into live dispatch
- end-to-end ESP32 demo synchronization
- first-class structured command controls in the React UI
- broader mission scenarios and topology growth

## Suggested Next Moves for Section 4

1. Keep the backend route behavior as-is, but present it as command-first in docs and demos.
2. Add a structured command panel to the UI so gossip vs. raft can be compared directly.
3. Only rely on push-to-talk when the demo specifically benefits from it.
4. Wire MQTT after the control and visualization path is stable.
