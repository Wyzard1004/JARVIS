# JARVIS: Joint Adaptive Resilient Voice Integrated Swarm

> **Voice-Activated Swarm Coordinator for DDIL Environments**  
> Critical Ops Hackathon (April 2026)

## The Pitch

JARVIS is a hardware-in-the-loop swarm coordination system designed for **disconnected, denied, or intermittent (DDIL) communication environments**. Instead of a human operator micromanaging drone flight paths, the operator acts as a node in a decentralized network. 

The operator **speaks naturally**; a local edge-deployed LLM translates speech into strict JSON commands; and the swarm executes coordination logic using a resilient, **leaderless gossip protocol**. All processing happens **entirely offline** on an Nvidia Jetson Orin.

### Hackathon Challenge Statements

- **Primary**: Problem 10 Ã¢â‚¬â€ Swarm Coordination Protocol for Contested Environments
- **Secondary**: Problem 16 Ã¢â‚¬â€ Edge Inference on Resource-Constrained Hardware

---

## System Architecture

```
Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
Ã¢â€â€š                    OPERATOR (Human Node)                    Ã¢â€â€š
Ã¢â€â€š   speaks: "JARVIS, re-route swarm to Grid Alpha"           Ã¢â€â€š
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                     Ã¢â€â€š Audio (Whisper STT)
                     Ã¢â€“Â¼
         Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
         Ã¢â€â€š  NVIDIA JETSON ORIN       Ã¢â€â€š (Base Station)
         Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
         Ã¢â€â€š  Ã¢â€â€š  FastAPI Backend    Ã¢â€â€š  Ã¢â€â€š Ã¢â€ Â You are here (4.0.0)
         Ã¢â€â€š  Ã¢â€â€š  Ã¢â€Å“Ã¢â€â‚¬ ai_bridge.py    Ã¢â€â€š  Ã¢â€â€š (Richard's module - TODO)
         Ã¢â€â€š  Ã¢â€â€š  Ã¢â€Å“Ã¢â€â‚¬ swarm_logic.py  Ã¢â€â€š  Ã¢â€â€š (Giulia's module - TODO)
         Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬ mqtt_client.py  Ã¢â€â€š  Ã¢â€â€š (Sebastian's module - TODO)
         Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
         Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
         Ã¢â€â€š  Ã¢â€â€š Ollama (Llama-3)    Ã¢â€â€š  Ã¢â€â€š Ã¢â€ â€™ JSON intent parsing
         Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
         Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
         Ã¢â€â€š  Ã¢â€â€š Mosquitto MQTT      Ã¢â€â€š  Ã¢â€â€š Ã¢â€ â€™ Hardware publishing
         Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
         Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
              Ã¢â€â€š                  Ã¢â€â€š
        WiFi  Ã¢â€â€š                  Ã¢â€â€š ESP-NOW Radio
              Ã¢â€â€š                  Ã¢â€â€š
              Ã¢â€“Â¼                  Ã¢â€“Â¼
    Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â   Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
    Ã¢â€â€š  REACT FRONTEND  Ã¢â€â€š   Ã¢â€â€š  ESP32 SWARM     Ã¢â€â€š
    Ã¢â€â€š (Web 5173)       Ã¢â€â€š   Ã¢â€â€š  (3x Gateways)   Ã¢â€â€š
    Ã¢â€â€š Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€â€š   Ã¢â€â€š  + LEDs          Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š SwarmGraph   Ã¢â€â€š Ã¢â€â€š   Ã¢â€â€š (Visual proof)   Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š (D3 Visual)  Ã¢â€â€š Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
    Ã¢â€â€š Ã¢â€â€š              Ã¢â€â€š Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š Push-to-Talk Ã¢â€â€š Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š Button       Ã¢â€â€š Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š              Ã¢â€â€š Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€š Status Panel Ã¢â€â€š Ã¢â€â€š
    Ã¢â€â€š Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€š
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
```

---

## Current Status (April 18, 2026)

### Ã¢Å“â€¦ Completed (4.0.0 - Full-Stack Integration)

- **FastAPI Backend** (Section 4.1)
  - Ã¢Å“â€¦ Health check endpoint (`GET /health`)
  - Ã¢Å“â€¦ WebSocket swarm updates (`/ws/swarm`)
  - Ã¢Å“â€¦ Voice command intake (`POST /api/voice-command`)
  - Ã¢Å“â€¦ Swarm state query (`GET /api/swarm-state`)
  - Ã¢Å“â€¦ CORS + lifecycle hooks
  - Ã¢Å“â€¦ Running successfully on `0.0.0.0:8000`

- **React Frontend** (Section 4.2)
  - Ã¢Å“â€¦ Vite + React 18 scaffold
  - Ã¢Å“â€¦ D3 force-graph visualization (SwarmGraph.jsx)
  - Ã¢Å“â€¦ Push-to-Talk button with mock transcript (PushToTalkButton.jsx)
  - Ã¢Å“â€¦ System status panel (StatusPanel.jsx)
  - Ã¢Å“â€¦ WebSocket listener (real-time updates)
  - Ã¢Å“â€¦ Tailwind CSS styling
  - Ã¢Å“â€¦ Running successfully on `localhost:5173`

- **Environment Setup**
  - Ã¢Å“â€¦ `.env` configuration file created
  - local `base_station/.env` with required variables documented
  - Ã¢Å“â€¦ `.gitignore` configured (no secrets committed)

### Ã°Å¸â€â€ž In Progress / Blocked

- **AI Bridge** (Section 3.0 - Richard)
  - Ã¢ÂÂ³ Ollama JSON parsing not yet integrated
  - Ã¢ÂÂ³ ElevenLabs TTS not yet integrated
  - Waiting for `base_station/core/ai_bridge.py` implementation

- **Swarm Logic** (Section 2.0 - Giulia)
  - Ã¢ÂÂ³ NetworkX gossip protocol not yet integrated
  - Ã¢ÂÂ³ Benchmark simulation not yet integrated
  - Waiting for `base_station/core/swarm_logic.py` implementation

- **MQTT Publisher** (Section 1.0 - Sebastian)
  - Ã¢ÂÂ³ Hardware publishing not yet integrated
  - Ã¢ÂÂ³ ESP32 communication not yet configured
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

**Verify**: Visit http://localhost:8000/docs Ã¢â€ â€™ Interactive API explorer opens

### Frontend Setup

```bash
cd command_center
npm install
npm run dev
```

**Verify**: http://localhost:5173 Ã¢â€ â€™ React UI loads with WebSocket "Connected" status

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
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ base_station/                    # Python FastAPI Backend
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ api/
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ main.py                 # FastAPI routes (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ core/
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ai_bridge.py            # LLM + TTS (Ã¢ÂÂ³ TODO - Richard)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ swarm_logic.py          # Gossip protocol (Ã¢ÂÂ³ TODO - Giulia)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ mqtt_client.py          # Hardware pub/sub (Ã¢ÂÂ³ TODO - Sebastian)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ requirements.txt            # Python deps (Ã¢Å“â€¦ DONE)
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ command_center/                  # React Frontend (Vite)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ src/
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ App.jsx                 # Main app (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ main.jsx                # Entry point (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ components/
Ã¢â€â€š   Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ SwarmGraph.jsx      # D3 visualization (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€â€š       Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ PushToTalkButton.jsx # Voice input (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€â€š       Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ StatusPanel.jsx     # System status (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ index.html                  # HTML root (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ package.json                # Node deps (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ vite.config.js              # Vite config (Ã¢Å“â€¦ DONE)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ tailwind.config.js          # Tailwind (Ã¢Å“â€¦ DONE)
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ hardware/                        # Arduino / C++
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ gateway_node/
Ã¢â€â€š   Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ gateway_node.ino        # ESP32-1 (Ã¢ÂÂ³ TODO)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ field_node/
Ã¢â€â€š       Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ field_node.ino          # ESP32-2/3 (Ã¢ÂÂ³ TODO)
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ simulations/                     # Math & Benchmarks
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ tcp_vs_gossip.py            # Perf comparison (Ã¢ÂÂ³ TODO)
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ outputs/                    # Generated charts
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ docs/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ mission_canvas.md           # Business logic
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ SECTION_4_SETUP.md          # Detailed setup guide
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ overview.md                 # High-level pitch
Ã¢â€â€š
├── base_station/.env               # Local config (DONE)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ .gitignore                      # Git setup (Ã¢Å“â€¦ DONE)
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ README.md                       # This file (Ã¢Å“â€¦ DONE)
```

---

## Testing Checklist

- [x] FastAPI backend starts without errors
- [x] React frontend loads at http://localhost:5173
- [x] WebSocket connection shows "connected" status
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

2. Expose: `process_voice_command(transcribed_text) Ã¢â€ â€™ Dict[intent, target, action]`

### Giulia (Section 2.0 - Swarm Logic)

1. Implement `base_station/core/swarm_logic.py`
   - Initialize NetworkX graph with drone nodes
   - Implement Gossip protocol propagation algorithm
   - Calculate multi-hop latency & bandwidth metrics
   - Compare TCP-based coordination vs. Gossip

2. Expose: `calculate_gossip_path(parsed_intent) Ã¢â€ â€™ Dict[nodes, edges, timestamps]`

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
3. Test end-to-end flow: Voice Ã¢â€ â€™ LLM Ã¢â€ â€™ Gossip Ã¢â€ â€™ ESP32s Ã¢â€ â€™ UI visualize
4. Polish UI and prepare demo script

---

## Demo Flow

1. **User**: Presses Push-to-Talk button and says: *"JARVIS, deploy swarm to Zone B"*
2. **Frontend**: Records audio, sends to backend
3. **Backend**: Whisper transcribes Ã¢â€ â€™ Ollama parses intent Ã¢â€ â€™ Gossip calculates path
4. **MQTT**: Command published to ESP32 Gateway
5. **Hardware**: ESP32-1 (Gateway) Ã¢â€ â€™ ESP32-2/3 (Field) via ESP-NOW, LEDs flash sequentially
6. **UI**: Real-time D3 graph pulses red, nodes drift toward target coordinates
7. **Speaker**: JARVIS confirms: *"Swarm deployed to Zone B. Gossip protocol active."*

---

## Tech Stack Summary

| Layer | Component | Tech | Status |
|-------|-----------|------|--------|
| **Edge Inference** | Base Station | Nvidia Jetson Orin + Ollama | Ã¢Å“â€¦ Ready |
| **Backend** | API Server | FastAPI + Uvicorn | Ã¢Å“â€¦ Running |
| **Frontend** | UI | React 18 + Vite + Tailwind | Ã¢Å“â€¦ Running |
| **Visualization** | Graph | D3 force simulation | Ã¢Å“â€¦ Active |
| **Voice** | STT/TTS | Whisper (TODO) / ElevenLabs (TODO) | Ã¢ÂÂ³ Pending |
| **Swarm Logic** | Coordination | NetworkX + Gossip (TODO) | Ã¢ÂÂ³ Pending |
| **Messaging** | Pub/Sub | Mosquitto MQTT (TODO) | Ã¢ÂÂ³ Pending |
| **Hardware** | Drones | 3x ESP32 + LEDs (TODO) | Ã¢ÂÂ³ Pending |

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
**Current Milestone**: 4.0.0 Framework Complete Ã¢Å“â€¦  
**Next Milestone**: 3.0 AI Pipeline Integration (Richard)
