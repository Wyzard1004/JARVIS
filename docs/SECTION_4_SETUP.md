# 4.0.0 Full-Stack Integration Setup Guide

> **Target**: William's section — Full-Stack Integration & Command UI

This guide walks you through everything needed to get the FastAPI backend and React frontend running in parallel with the core modules from Richard (ai_bridge) and Giulia (swarm_logic).

## What's Been Set Up

### Backend (Python / FastAPI)

**File**: [base_station/api/main.py](../base_station/api/main.py)

**Includes**:
- ✅ FastAPI app skeleton with CORS middleware
- ✅ Health check endpoint (`GET /health`)
- ✅ WebSocket connection manager for real-time UI syncing (`/ws/swarm`)
- ✅ Voice command intake endpoint (`POST /api/voice-command`)
- ✅ Swarm state query endpoint (`GET /api/swarm-state`)
- ✅ Lifecycle hooks (startup/shutdown)
- ✅ TodoPlaceholders for MQTT publisher, AI Bridge, and Swarm Logic integration

**Dependencies**: [base_station/requirements.txt](../base_station/requirements.txt)
- `fastapi`, `uvicorn`, `paho-mqtt`, `requests`, `python-dotenv`, `websockets`, `networkx`

### Frontend (React / Vite)

**Includes**:
- ✅ [command_center/src/App.jsx](../command_center/src/App.jsx) — Main app component with WebSocket listener
- ✅ [command_center/src/components/SwarmGraph.jsx](../command_center/src/components/SwarmGraph.jsx) — `react-force-graph` visualization
- ✅ [command_center/src/components/PushToTalkButton.jsx](../command_center/src/components/PushToTalkButton.jsx) — Microphone input + mock transcript
- ✅ [command_center/src/components/StatusPanel.jsx](../command_center/src/components/StatusPanel.jsx) — System status display
- ✅ Tailwind CSS + PostCSS configuration
- ✅ Vite dev server with proxy to FastAPI backend

**Dependencies**: [command_center/package.json](../command_center/package.json)
- `react`, `react-dom`, `react-force-graph`, `socket.io-client`, `axios`, `tailwindcss`

### Environment Variables

**File**: [.env](.env) (local development)

**Create from**: [.env.example](.env.example)

**Required keys**:
- `ELEVENLABS_API_KEY` - For TTS confirmations
- `OLLAMA_API_BASE_URL` - Local LLM endpoint
- `MQTT_BROKER_HOST` / `MQTT_BROKER_PORT` - MQTT settings
- `FASTAPI_HOST` / `FASTAPI_PORT` - Backend server config

---

## Getting Started (4.1 & 4.2)

### Step 1: Backend Setup (4.1.1 - 4.1.2)

```bash
cd base_station
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Test the API**:
```bash
cd base_station
python -m uvicorn api.main:app --reload
```

Navigate to http://localhost:8000/docs for the interactive FastAPI UI.

### Step 2: Frontend Setup (4.2.1)

```bash
cd command_center
npm install      # or yarn install
npm run dev      # Starts Vite dev server on port 5173
```

Open http://localhost:5173 in your browser.

---

## Integration Checkpoints

### Checkpoint 1: Backend ← Richard's AI Bridge (3.1 & 3.2)

**Where to plug in**: [base_station/api/main.py](../base_station/api/main.py) line ~85

```python
from core.ai_bridge import AIBridge

# In the voice_command endpoint:
parsed_intent = await ai_bridge.process_voice_command(transcribed_text)
```

### Checkpoint 2: Backend ← Giulia's Swarm Logic (2.1 & 2.2)

**Where to plug in**: [base_station/api/main.py](../base_station/api/main.py) line ~95

```python
from core.swarm_logic import SwarmLogic

# In the voice_command endpoint:
gossip_result = await swarm_logic.calculate_gossip_path(parsed_intent)
```

### Checkpoint 3: Backend → MQTT Publisher (Hardware)

**Where to plug in**: [base_station/api/main.py](../base_station/api/main.py) line ~102

```python
from core.mqtt_client import MQTTPublisher

# In startup event:
mqtt_publisher = MQTTPublisher(host, port, client_id)

# In voice_command endpoint:
await mqtt_publisher.publish("swarm/command", json.dumps(gossip_result))
```

### Checkpoint 4: Backend → React (WebSocket)

**Already implemented** in [App.jsx](../command_center/src/App.jsx#L14-L40)

The React app connects to `ws://localhost:8000/ws/swarm` and listens for real-time updates.

### Checkpoint 5: React Push-to-Talk (4.2.3)

**Current Status**: Mock implementation recording audio

**TODO**: Uncomment lines in [PushToTalkButton.jsx](../command_center/src/components/PushToTalkButton.jsx#L32-L37) once backend has `/api/transcribe` endpoint (Whisper integration).

---

## Running the Full Demo

### Terminal 1: Jetson Orin Backend
```bash
cd /path/to/jarvis/base_station
source venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: React Dev Server
```bash
cd /path/to/jarvis/command_center
npm run dev
```

### Terminal 3: MQTT Broker (Mosquitto)
```bash
# If Mosquitto is already running on your Jetson:
mosquitto -c /etc/mosquitto/mosquitto.conf

# Or start the service:
sudo systemctl start mosquitto
```

---

## Expected WebSocket Message Format (React ↔ Backend)

### Backend → React (Gossip Update)
```json
{
  "event": "gossip_update",
  "active_nodes": ["node_1", "node_2", "node_5"],
  "target_x": 150,
  "target_y": -50,
  "status": "swarming",
  "timestamp": "2026-04-18T12:00:00Z"
}
```

### React → Backend (Voice Command)
```json
{
  "transcribed_text": "JARVIS, re-route swarm to Grid Alpha"
}
```

---

## Testing Checklist

- [ ] FastAPI backend starts without errors
- [ ] React frontend loads at http://localhost:5173
- [ ] WebSocket connection shows "connected" status
- [ ] Push-to-Talk button records audio
- [ ] Mock transcript appears after releasing the button
- [ ] Network tab shows POST to `/api/voice-command`
- [ ] Command appears in "Recent Commands" list

---

## What's Next?

1. **Richard**: Implement [base_station/core/ai_bridge.py](../base_station/core/ai_bridge.py) with Ollama + ElevenLabs
2. **Giulia**: Implement [base_station/core/swarm_logic.py](../base_station/core/swarm_logic.py) with NetworkX Gossip protocol
3. **Sebastian**: Implement [base_station/core/mqtt_client.py](../base_station/core/mqtt_client.py) MQTT publisher
4. **William**: Integrate all three modules into main.py, refine React UI (4.3.1-4.3.2)

Good luck! 🚀
