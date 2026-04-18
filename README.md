# JARVIS: Joint Adaptive Resilient Voice Integrated Swarm

> **Voice-Activated Swarm Coordinator for DDIL Environments**  
> Critical Ops Hackathon (April 2026)

## The Pitch

JARVIS is a hardware-in-the-loop swarm coordination system designed for **disconnected, denied, or intermittent (DDIL) communication environments**. Instead of a human operator micromanaging drone flight paths, the operator acts as a node in a decentralized network. 

The operator **speaks naturally**; a local edge-deployed LLM translates speech into strict JSON commands; and the swarm executes coordination logic using a resilient, **leaderless gossip protocol**. All processing happens **entirely offline** on an Nvidia Jetson Orin.

### Hackathon Challenge Statements

- **Primary**: Problem 10 - Swarm Coordination Protocol for Contested Environments
- **Secondary**: Problem 16 - Edge Inference on Resource-Constrained Hardware

---

## System Architecture

```
+-------------------------------------------+
|    OPERATOR (Human Node)                  |
|    speaks: "JARVIS, re-route to Alpha"    |
+-------------------------------------------+
              |
              | Audio (Whisper STT)
              v
  +-----------------------------+
  |  NVIDIA JETSON ORIN         |
  |  (Base Station)             |
  |  +---------------------+    |
  |  | FastAPI Backend     |    |
  |  | - ai_bridge.py      |    | You are here (4.0.0)
  |  | - swarm_logic.py    |    |
  |  | - mqtt_client.py    |    |
  |  +---------------------+    |
  |  +---------------------+    |
  |  | Ollama (Llama-3)    |    | JSON intent parsing
  |  +---------------------+    |
  |  +---------------------+    |
  |  | Mosquitto MQTT      |    | Hardware publishing
  |  +---------------------+    |
  +-----------------------------+
        |              |
        | WiFi         | ESP-NOW Radio
        v              v
  +----------+    +-----------+
  | REACT    |    | ESP32     |
  | FRONTEND |    | SWARM     |
  |          |    | (3x       |
  | Port:    |    | Gateways) |
  | 5173     |    | + LEDs    |
  |          |    |           |
  | - Graph  |    | (Visual   |
  |   (D3)   |    |  proof)   |
  |          |    |           |
  | - PTT    |    |           |
  |   Button |    |           |
  |          |    |           |
  | - Status |    |           |
  |   Panel  |    |           |
  +----------+    +-----------+
```

---

## Current Status (April 18, 2026)

### DONE Completed (4.0.0 - Full-Stack Integration)

- **FastAPI Backend** (Section 4.1)
  - DONE Health check endpoint (`GET /health`)
  - DONE WebSocket swarm updates (`/ws/swarm`)
  - DONE Voice command intake (`POST /api/voice-command`)
  - DONE Swarm state query (`GET /api/swarm-state`)
  - DONE CORS + lifecycle hooks
  - DONE Running successfully on `0.0.0.0:8000`

- **React Frontend** (Section 4.2)
  - DONE Vite + React 19 scaffold
  - DONE D3 force-graph visualization (SwarmGraph.jsx)
  - DONE Push-to-Talk button with mock transcript (PushToTalkButton.jsx)
  - DONE System status panel (StatusPanel.jsx)
  - DONE WebSocket listener (real-time updates)
  - DONE Tailwind CSS v4 styling
  - DONE Running successfully on `localhost:5173`

- **Environment Setup**
  - DONE `.env` configuration file created
  - DONE Local `base_station/.env` with required variables documented
  - DONE `.gitignore` configured (no secrets committed)

- **Dependencies Updated (April 18, 2026)**
  - DONE FastAPI 0.136.0 (latest)
  - DONE React 19.2.5 (latest)
  - DONE Vite 8.0.8 (latest)
  - DONE Tailwind CSS 4.2.2 (latest)
  - DONE All security vulnerabilities patched

### X In Progress / Blocked

- **AI Bridge** (Section 3.0 - Richard)
  - X Ollama JSON parsing not yet integrated
  - X ElevenLabs TTS not yet integrated
  - Waiting for `base_station/core/ai_bridge.py` implementation

- **Swarm Logic** (Section 2.0 - Giulia)
  - X NetworkX gossip protocol not yet integrated
  - X Benchmark simulation not yet integrated
  - Waiting for `base_station/core/swarm_logic.py` implementation

- **MQTT Publisher** (Section 1.0 - Sebastian)
  - X Hardware publishing not yet integrated
  - X ESP32 communication not yet configured
  - Waiting for `base_station/core/mqtt_client.py` implementation

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Virtual environment (venv)

### Backend Setup

```bash
cd base_station
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify**: Visit http://localhost:8000/docs - Interactive API explorer opens

### Frontend Setup

```bash
cd command_center
npm install
npm run dev
```

**Verify**: http://localhost:5173 - React UI loads with WebSocket "Connected" status

### Both Running

```bash
# Terminal 1: Backend
cd base_station && source venv/bin/activate && python -m uvicorn api.main:app --reload

# Terminal 2: Frontend
cd command_center && npm run dev
```

---

## API Endpoints

### Health & Status

```bash
GET /health
```

Response:
```json
{
  "status": "operational",
  "subsystems": {
    "api": "online"
  }
}
```

### Voice Command

```bash
POST /api/voice-command
Content-Type: application/json

{
  "transcribed_text": "JARVIS, re-route swarm to Grid Alpha"
}
```

### Swarm State

```bash
GET /api/swarm-state
```

Response:
```json
{
  "nodes": [
    {"id": "node_1", "status": "active", "x": 0, "y": 0},
    {"id": "node_2", "status": "idle", "x": 100, "y": 50}
  ],
  "edges": [
    {"source": "node_1", "target": "node_2"}
  ],
  "timestamp": "2026-04-18T12:00:00Z"
}
```

### WebSocket (Real-Time)

```
ws://localhost:8000/ws/swarm
```

Subscribe to gossip updates:
```json
{
  "event": "gossip_update",
  "active_nodes": ["node_1", "node_2"],
  "target_x": 150,
  "target_y": -50,
  "status": "swarming"
}
```

---

## Project Structure

```
jarvis-swarm/
+-- base_station/                    # Python FastAPI Backend
|   +-- api/
|   |   +-- main.py                 # FastAPI routes (DONE)
|   +-- core/
|   |   +-- ai_bridge.py            # LLM + TTS (TODO - Richard)
|   |   +-- swarm_logic.py          # Gossip protocol (TODO - Giulia)
|   |   +-- mqtt_client.py          # Hardware pub/sub (TODO - Sebastian)
|   +-- requirements.txt            # Python deps (DONE)
|
+-- command_center/                  # React Frontend (Vite)
|   +-- src/
|   |   +-- App.jsx                 # Main app (DONE)
|   |   +-- main.jsx                # Entry point (DONE)
|   |   +-- index.css               # Tailwind styles (DONE)
|   |   +-- components/
|   |       +-- SwarmGraph.jsx      # D3 visualization (DONE)
|   |       +-- PushToTalkButton.jsx # Voice input (DONE)
|   |       +-- StatusPanel.jsx     # System status (DONE)
|   +-- index.html                  # HTML root (DONE)
|   +-- package.json                # Node deps (DONE)
|   +-- vite.config.js              # Vite config (DONE)
|   +-- tailwind.config.js          # Tailwind (DONE)
|
+-- hardware/                        # Arduino / C++
|   +-- gateway_node/
|   |   +-- gateway_node.ino        # ESP32-1 (TODO)
|   +-- field_node/
|       +-- field_node.ino          # ESP32-2/3 (TODO)
|
+-- simulations/                     # Math & Benchmarks
|   +-- tcp_vs_gossip.py            # Perf comparison (TODO)
|   +-- outputs/                    # Generated charts
|
+-- docs/
|   +-- mission_canvas.md           # Business logic
|   +-- SECTION_4_SETUP.md          # Detailed setup guide
|   +-- overview.md                 # High-level pitch
|
+-- base_station/.env               # Local config (DONE)
+-- .gitignore                       # Git setup (DONE)
+-- README.md                        # This file (DONE)
```

---

## Testing Checklist

- [x] FastAPI backend starts without errors
- [x] React frontend loads at http://localhost:5173
- [x] WebSocket connection shows "connected" status
- [x] Build completes with Tailwind CSS v4
- [x] All npm security vulnerabilities resolved
- [ ] Push-to-Talk button records audio
- [ ] Voice transcription via Whisper
- [ ] LLM intent parsing returns valid JSON
- [ ] Swarm graph updates from WebSocket
- [ ] ESP32 LEDs flash in gossip order
- [ ] Benchmark results generated and visualized

---

## What's Next

### Richard (Section 3.0 - AI Pipeline)

1. Implement `base_station/core/ai_bridge.py`
   - Connect to local Ollama API
   - Prompt engineer Llama-3 for JSON intent extraction
   - Integrate ElevenLabs SDK for TTS confirmations
   - Handle parsing errors gracefully

2. Expose: `process_voice_command(transcribed_text) -> Dict[intent, target, action]`

### Giulia (Section 2.0 - Swarm Logic)

1. Implement `base_station/core/swarm_logic.py`
   - Initialize NetworkX graph with drone nodes
   - Implement Gossip protocol propagation algorithm
   - Calculate multi-hop latency & bandwidth metrics
   - Compare TCP-based coordination vs. Gossip

2. Expose: `calculate_gossip_path(parsed_intent) -> Dict[nodes, edges, timestamps]`

3. Generate benchmark charts for the pitch deck

### Sebastian (Section 1.0 - Hardware)

1. Implement `base_station/core/mqtt_client.py`
   - Connect to Mosquitto broker
   - Publish commands to `swarm/command` topic
   - Handle connection failures gracefully

2. Program ESP32 firmware
   - Gateway node: Listen to MQTT, republish via ESP-NOW
   - Field nodes: Listen to ESP-NOW, toggle LEDs with staggered timing

3. Test radio propagation with mock delays

### William (Section 4.0 - Integration)

1. Wire together all three modules in `api.main:voice_command()`
2. Refine React animations (4.3.1 - 4.3.2)
3. Test end-to-end flow: Voice -> LLM -> Gossip -> ESP32s -> UI visualize
4. Polish UI and prepare demo script

---

## Demo Flow

1. **User**: Presses Push-to-Talk button and says: *"JARVIS, deploy swarm to Zone B"*
2. **Frontend**: Records audio, sends to backend
3. **Backend**: Whisper transcribes -> Ollama parses intent -> Gossip calculates path
4. **MQTT**: Command published to ESP32 Gateway
5. **Hardware**: ESP32-1 (Gateway) -> ESP32-2/3 (Field) via ESP-NOW, LEDs flash sequentially
6. **UI**: Real-time D3 graph pulses red, nodes drift toward target coordinates
7. **Speaker**: JARVIS confirms: *"Swarm deployed to Zone B. Gossip protocol active."*

---

## Tech Stack Summary

| Layer | Component | Tech | Status |
|-------|-----------|------|--------|
| **Edge Inference** | Base Station | Nvidia Jetson Orin + Ollama | Ready |
| **Backend** | API Server | FastAPI + Uvicorn | Running |
| **Frontend** | UI | React 19 + Vite 8 + Tailwind 4 | Running |
| **Visualization** | Graph | D3 force simulation | Active |
| **Voice** | STT/TTS | Whisper (TODO) / ElevenLabs (TODO) | Pending |
| **Swarm Logic** | Coordination | NetworkX + Gossip (TODO) | Pending |
| **Messaging** | Pub/Sub | Mosquitto MQTT (TODO) | Pending |
| **Hardware** | Drones | 3x ESP32 + LEDs (TODO) | Pending |

---

## References

- **Overview**: See [overview.md](overview.md) for full business case
- **Gameplan**: See [development_gameplan.md](development_gameplan.md) for section breakdown
- **Setup Guide**: See [docs/SECTION_4_SETUP.md](docs/SECTION_4_SETUP.md) for 4.0.0 details
- **Repository**: See [repository_structure.md](repository_structure.md) for folder conventions

---

## License

Internal hackathon project. All rights reserved.

---

**Last Updated**: April 18, 2026  
**Current Milestone**: 4.0.0 Framework Complete (DONE)  
**Next Milestone**: 3.0 AI Pipeline Integration (Richard)
