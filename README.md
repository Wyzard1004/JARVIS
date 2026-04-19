# JARVIS: Joint Adaptive Relay for Variable Interoperable Swarms

> **Swarm Consensus and Coordination for DDIL Environments**  
> Critical Ops Hackathon (April 2026)

## The Pitch

JARVIS is a hardware-in-the-loop swarm coordination system for **disconnected, denied, or intermittent (DDIL) environments**. The core problem is not voice control by itself; it is resilient coordination across human operators, relay nodes, and autonomous platforms when links degrade, partition, or disappear.

The current repo is centered on a contested-environment simulation that compares a **leaderless adaptive gossip protocol** against a **leader-based TCP/Raft-style baseline**, visualizes propagation in real time, and reports benchmark data for latency, control-plane bandwidth, and fault tolerance. A local LLM and audio path still exist, but they are best understood as **optional operator interfaces** into the swarm rather than the identity of the project.

### Hackathon Challenge Statements

- **Primary**: Problem 10 - Swarm Coordination Protocol for Contested Environments
- **Secondary**: Problem 16 - Edge Inference on Resource-Constrained Hardware

---

## What Is Working Now

- **Consensus runtime** in `base_station/core/swarm_logic.py`
  - Adaptive gossip simulation with retries, TTL, relay fanout, and disruption handling
  - TCP/Raft-style baseline for comparison
  - Delivery summaries, mission/search state, object reports, and built-in benchmark data
- **FastAPI backend** in `base_station/api/main.py`
  - `GET /health`
  - `GET /api/swarm-state`
  - `POST /api/voice-command` for direct structured payloads or text commands
  - `POST /api/transcribe-command` for optional audio upload
  - `ws://localhost:8000/ws/swarm` for real-time updates
- **React command center**
  - WebSocket-driven graph visualization
  - Status panel and command history
  - Push-to-talk UI still present as an optional demo path
- **Optional AI bridge**
  - Rule-based and Ollama-backed command parsing
  - ElevenLabs speech-to-text and text-to-speech helpers

---

## System Architecture

```text
+-------------------------------------------+
| OPERATOR / CONTROL NODE                   |
| - direct structured command               |
| - optional text or audio command          |
+-------------------------------------------+
                    |
                    v
  +---------------------------------------+
  | NVIDIA JETSON ORIN (Base Station)     |
  | FastAPI + swarm_logic + ai_bridge      |
  | - adaptive gossip                      |
  | - TCP/Raft baseline                    |
  | - benchmark + mission state            |
  +---------------------------------------+
          |                         |
          v                         v
  +------------------+      +------------------+
  | React UI         |      | MQTT / ESP-NOW   |
  | - graph view     |      | - gateway node   |
  | - status panel   |      | - field nodes    |
  | - command input  |      | - LED proof      |
  +------------------+      +------------------+
```

The current demo topology in code includes:

- a gateway relay
- two human operator nodes
- one recon drone
- two attack drones

That topology can expand later, but the implemented repo today is already organized around contested mesh coordination and consensus behavior.

---

## Current Status (April 18, 2026)

### Implemented

- **Swarm coordination runtime**
  - Adaptive gossip and TCP/Raft-style baseline are both implemented
  - Benchmark data is surfaced through the runtime and API responses
  - Search state, propagation order, delivery summaries, and disruption modeling are live
- **Backend integration**
  - Swarm logic is wired into FastAPI
  - Direct payloads can bypass voice parsing
  - Algorithm selection is supported through request payloads
- **Frontend integration**
  - React app connects to the backend over WebSocket
  - Real-time state is rendered in the graph and status panel
  - Command history updates when commands are dispatched
- **AI bridge**
  - `ai_bridge.py` is implemented with safe fallbacks, rule parsing, and optional Ollama use
  - Audio transcription and confirmation helpers exist, but they are not the primary focus

### In Progress

- Wiring MQTT publishing into the live FastAPI dispatch loop
- Completing ESP32 hardware sync for the physical propagation demo
- Rebalancing the UI so structured swarm commands are first-class instead of voice-first
- Expanding scenarios, node types, and contested-network behaviors beyond the current demo topology

### Secondary / Optional

- Ollama prompt tuning and parser refinement
- Audio transcription reliability and TTS polish

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Virtual environment support

### Backend Setup (PowerShell)

```powershell
cd base_station
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

If you prefer bash:

```bash
cd base_station
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```powershell
cd command_center
npm install
npm run dev
```

### Remote Tailscale Setup

If the backend is running on another machine, point the command center and Jetson listener at that host instead of `localhost`.

Frontend example:

```bash
cd command_center
cp env.remote.example .env.local
```

Set `VITE_API_BASE_URL` to the backend machine's Tailscale IP or MagicDNS name, for example:

```bash
VITE_API_BASE_URL=http://philly-backend.example.ts.net:8000
```

The app will derive the WebSocket URL automatically unless you also set `VITE_WEBSOCKET_URL`.

Jetson example:

```bash
export JARVIS_LISTENER_API_URL=http://philly-backend.example.ts.net:8000/api/transcribe-command
export JARVIS_OPERATOR_NODE=soldier-1
```

### Deploy The Command Center On Vercel

Vercel is a good fit for the `command_center` React app, but it is **not a good primary host for the current FastAPI backend**.

Why the split matters:

- the backend keeps live swarm state in memory
- `ws://.../ws/swarm` is a real server-managed WebSocket, not a hosted pub/sub service
- map overlays and saved scenarios are written to local disk under `base_station/`

That means the practical deployment shape is:

- **Vercel** for `command_center/`
- **a stateful host** for `base_station/` such as a VM, Jetson, Railway, Fly.io, or Render service with persistent storage and WebSocket support

This repo now includes a root `vercel.json` that builds the Vite app from `command_center/`.

Recommended Vercel environment variables:

```bash
VITE_API_BASE_URL=https://your-backend.example.com
# Optional if your websocket endpoint is on a different host/path.
VITE_WEBSOCKET_URL=wss://your-backend.example.com/ws/swarm
```

Production checklist:

- `Required`: `VITE_API_BASE_URL`
- `Optional`: `VITE_WEBSOCKET_URL` if your websocket endpoint is not simply `/ws/swarm` on the same backend host
- `Template`: `command_center/.env.vercel.example`

Deploy steps:

1. Push this repo to GitHub, GitLab, or Bitbucket.
2. In Vercel, create a new project from that repo.
3. Keep the project's **Root Directory** at the repo root so Vercel uses the included `vercel.json`.
4. Add `VITE_API_BASE_URL` pointing at your deployed backend.
5. Add `VITE_WEBSOCKET_URL` if the websocket host/path differs from the API host.
6. Deploy. Vercel will run the root build, install from `command_center/`, and publish `command_center/dist`.

Notes:

- if `VITE_WEBSOCKET_URL` is omitted, the app derives it from `VITE_API_BASE_URL`
- if neither variable is set, the frontend now falls back to same-origin `/api` and `/ws`, which works well behind a reverse proxy
- the existing `command_center/env.remote.example` file is a good starting point for Vercel env setup

If you want to experiment with putting the backend on Vercel anyway, expect to rework the WebSocket transport, persistent state handling, and scenario/overlay storage first.

### Deploy The Backend On Render

The repo now includes:

- `base_station/Dockerfile` for the FastAPI service
- `base_station/requirements.deploy.txt` with cloud-friendly backend dependencies
- `render.yaml` for a Render Blueprint deployment
- `base_station/.env.render.example` with a copy/paste env template

Recommended Render flow:

1. Push the repo to GitHub.
2. In Render, create a new Blueprint or Web Service from the repo.
3. If you use the Blueprint, Render will pick up `render.yaml` and configure the Docker deploy, `/health` health check, and a persistent disk mounted at `/data`.
4. If you create the service manually instead, point Render at `base_station/Dockerfile`, set `PORT=10000`, `JARVIS_DATA_DIR=/data`, and attach a persistent disk at `/data`.
5. Set optional secrets only if you use them in production, such as `ELEVENLABS_API_KEY`, `OLLAMA_BASE_URL`, or MQTT-related env vars.
6. After the backend is live, copy its public HTTPS URL into Vercel as `VITE_API_BASE_URL`.

Important deployment behavior:

- `JARVIS_DATA_DIR=/data` redirects saved scenarios and uploaded overlay images into writable persistent storage
- `JARVIS_RELAY_ENABLED=false` is a sensible default for hosted demos unless you are also exposing the relay bridge path intentionally
- if you skip the persistent disk, scenario saves and uploaded overlays will be ephemeral across restarts/redeploys

Production checklist:

- `Required`: `PORT=10000`
- `Required`: `JARVIS_DATA_DIR=/data`
- `Recommended`: `JARVIS_RELAY_ENABLED=false`
- `Recommended`: `JARVIS_NETWORK_PROFILE=baseline`
- `Optional`: `OLLAMA_BASE_URL` and `OLLAMA_MODEL` if the hosted service can reach an Ollama instance
- `Optional`: `ELEVENLABS_API_KEY` if you want speech transcription / TTS
- `Optional`: `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, and `MQTT_CLIENT_ID` for hardware messaging
- `Template`: `base_station/.env.render.example`

### Verify

- FastAPI docs open at [http://localhost:8000/docs](http://localhost:8000/docs)
- React UI opens at [http://localhost:5173](http://localhost:5173)
- WebSocket state appears in the command center

---

## API Endpoints

### Health

```http
GET /health
```

### Command Intake

```http
POST /api/voice-command
Content-Type: application/json
```

The route name is legacy from the earlier demo framing, but it already supports **direct structured swarm commands** in addition to transcribed text.

Example direct payload:

```json
{
  "origin": "soldier-1",
  "target_location": "Grid Alpha",
  "action_code": "SEARCH",
  "consensus_algorithm": "gossip"
}
```

Example text payload:

```json
{
  "transcribed_text": "JARVIS, move to Grid Alpha, over.",
  "consensus_algorithm": "raft"
}
```

Current parser highlights:

- callsign-first phrasing such as `JARVIS, move to Grid Alpha, over.`
- staged attack flow:
  - `JARVIS, attack Grid Bravo, over.` -> `command_pending`
  - `JARVIS, execute, over.` -> live dispatch
- typed location detail is returned alongside legacy string fields

### Optional Audio Path

```http
POST /api/transcribe-command
Content-Type: multipart/form-data
```

Uploads microphone audio, runs the optional transcription/parsing path, and dispatches the resulting swarm intent.

### Swarm State

```http
GET /api/swarm-state
```

Returns nodes, edges, active nodes, propagation order, delivery summary, benchmark data, and supported algorithms.

### WebSocket

```text
ws://localhost:8000/ws/swarm
```

Current event naming still uses `gossip_update` for compatibility with the existing frontend, even when the selected algorithm is the TCP/Raft baseline.

Additional lifecycle events now used by staged commands:

- `command_pending`
- `command_canceled`

---

## Project Structure

The repo root intentionally stays small now. Supporting documentation lives under `docs/`, and older implementation notes are kept in `docs/archive/` instead of crowding the top level.

```text
jarvis-swarm/
+-- base_station/
|   +-- api/
|   |   +-- main.py                 # FastAPI routes and dispatch
|   +-- core/
|   |   +-- ai_bridge.py            # Optional text/audio command adapter
|   |   +-- swarm_logic.py          # Consensus simulation and benchmark runtime
|   |   +-- mqtt_client.py          # Hardware messaging client
|   +-- requirements.txt
|
+-- command_center/
|   +-- src/
|   |   +-- App.jsx
|   |   +-- components/
|   |       +-- SwarmGraph.jsx      # Real-time topology visualization
|   |       +-- PushToTalkButton.jsx # Optional audio input UI
|   |       +-- StatusPanel.jsx
|
+-- hardware/
|   +-- gateway_node/
|   +-- field_node/
|
+-- simulations/
|   +-- tcp_vs_gossip.py            # Standalone comparison utilities
|
+-- docs/
|   +-- README.md                 # Docs hub and source-of-truth index
|   +-- OVERVIEW.md              # Project framing and system blueprint
|   +-- SETUP.md                 # Local setup and integration notes
|   +-- TESTING.md               # End-to-end testing guide
|   +-- COMMAND_SCHEMA.md        # Command contract and examples
|   +-- ROADMAP.md               # Current execution plan
|   +-- reference/
|   |   +-- AI_BRIDGE_SKETCH.md  # Parser design notes
|   +-- archive/                 # Historical phase notes and superseded docs
|
+-- README.md
```

---

## Testing Checklist

- [x] FastAPI backend starts without errors
- [x] React frontend loads and connects over WebSocket
- [x] Swarm state endpoint returns nodes, edges, and benchmark data
- [x] Adaptive gossip and TCP/Raft baseline are both exposed by the backend
- [x] Benchmark results are attached to consensus responses
- [ ] MQTT publishing is wired into live dispatch
- [ ] ESP32 gateway and field-node demo are synchronized end to end
- [ ] Structured command controls are first-class in the UI
- [ ] Additional topology roles and scenarios are added beyond the current demo set

---

## Current Demo Story

1. An operator injects a command through the UI, either as a structured control payload or through the optional voice path.
2. The backend turns that input into a normalized swarm intent.
3. `swarm_logic.py` executes either adaptive gossip or the TCP/Raft-style baseline.
4. The result is broadcast to the React UI over WebSocket.
5. When hardware integration is connected, the same command path can be mirrored to ESP32 nodes over MQTT and ESP-NOW.
6. The benchmark layer reports why leaderless relay can outperform direct leader-based control in disrupted DDIL conditions.

---

## Next Steps

- Make direct structured swarm commands the primary UI path
- Wire `mqtt_client.py` into the FastAPI dispatch flow
- Expand disruption scenarios and operational topologies
- Add more node classes and mission roles as the simulation grows
- Keep voice, STT, and TTS as optional operator-interface layers instead of the main project story

---

## Tech Stack Summary

| Layer | Component | Tech | Status |
|-------|-----------|------|--------|
| Edge Inference | Base Station | Nvidia Jetson Orin + Ollama | Available |
| Backend | API Server | FastAPI + Uvicorn | Running |
| Frontend | UI | React 19 + Vite 8 + Tailwind 4 | Running |
| Visualization | Graph | D3 force simulation | Active |
| Consensus | Swarm Runtime | NetworkX + adaptive gossip + TCP/Raft baseline | Active |
| Operator Interface | Command Parsing | Direct payloads + rules/Ollama | Active |
| Audio | STT/TTS | ElevenLabs helpers | Optional |
| Messaging | Pub/Sub | Mosquitto MQTT | In progress |
| Hardware | Field Demo | ESP32 + ESP-NOW + LEDs | In progress |

---

## References

- **Docs Hub**: See [docs/README.md](docs/README.md)
- **Overview**: See [docs/OVERVIEW.md](docs/OVERVIEW.md)
- **Roadmap**: See [docs/ROADMAP.md](docs/ROADMAP.md)
- **Setup Guide**: See [docs/SETUP.md](docs/SETUP.md)
- **Testing Guide**: See [docs/TESTING.md](docs/TESTING.md)

Anything in `docs/archive/` is preserved for history but should not be treated as the current source of truth.

---

## License

Internal hackathon project. All rights reserved.

---

**Last Updated**: April 18, 2026  
**Current Milestone**: Consensus-first simulation and command center integration  
**Primary Narrative**: Swarm coordination in contested environments, with voice as an optional interface
