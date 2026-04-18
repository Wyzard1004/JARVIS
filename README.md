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
  "transcribed_text": "JARVIS, move swarm to Grid Alpha",
  "consensus_algorithm": "raft"
}
```

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

---

## Project Structure

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
|   +-- SECTION_4_SETUP.md
|   +-- frozen_command_examples.md
|   +-- richard_ai_bridge_sketch.md
|
+-- overview.md
+-- development_gameplan.md
+-- RICHARD_HANDOFF_GAMEPLAN.md
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

- **Overview**: See [overview.md](overview.md)
- **Gameplan**: See [development_gameplan.md](development_gameplan.md)
- **Setup Guide**: See [docs/SECTION_4_SETUP.md](docs/SECTION_4_SETUP.md)
- **Richard Handoff**: See [RICHARD_HANDOFF_GAMEPLAN.md](RICHARD_HANDOFF_GAMEPLAN.md)

---

## License

Internal hackathon project. All rights reserved.

---

**Last Updated**: April 18, 2026  
**Current Milestone**: Consensus-first simulation and command center integration  
**Primary Narrative**: Swarm coordination in contested environments, with voice as an optional interface
