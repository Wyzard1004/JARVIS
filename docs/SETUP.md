# Setup Guide

This guide matches the stack that is live in the repo right now:

- backend on the Jetson or a development machine
- React command center on a laptop or desktop
- optional Jetson serial listener for the ESP32 push-to-talk and relay bridge
- optional ESP32 gateway plus field nodes for the physical relay demo

## 1. Know The Current Startup Model

There are three distinct runtime pieces:

1. FastAPI backend in [../base_station/api/main.py](../base_station/api/main.py)
2. React frontend in [../command_center/src/App.jsx](../command_center/src/App.jsx)
3. Jetson listener / relay bridge in [../base_station/headless/serial_ptt_listener.py](../base_station/headless/serial_ptt_listener.py)

The relay hardware path depends on all three when you want the full demo.

## 2. Backend Setup

### Windows PowerShell or local development shell

```powershell
cd base_station
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Linux / Jetson

```bash
cd base_station
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Important note

The backend boots into the blank workspace by default. Load a populated scenario from the UI or use:

```bash
curl -X POST http://127.0.0.1:8000/api/scenarios/load \
  -H "Content-Type: application/json" \
  -d '{"scenario_key":"scenarios/village_reconnaissance_patrol.json"}'
```

## 3. Frontend Setup

```powershell
cd command_center
npm install
npm run dev
```

Open:

- `http://localhost:5173`

The frontend expects the backend over:

- `VITE_API_BASE_URL`
- `VITE_WEBSOCKET_URL` or an API-derived fallback

If the backend is on another machine, create `command_center/.env.local` from `command_center/env.remote.example`.

Example:

```bash
VITE_API_BASE_URL=http://100.108.243.35:8000
VITE_WEBSOCKET_URL=ws://100.108.243.35:8000/ws/swarm
```

## 4. Jetson Listener Setup

The Jetson listener does two jobs:

- reads push-to-talk events from the gateway ESP32 over USB serial
- exposes the local `/relay` and `/status` bridge used by the backend for hardware mirroring

Start it with:

```bash
cd base_station
source .venv/bin/activate
set -a
source .env
set +a
python headless/serial_ptt_listener.py
```

### Recommended `.env` fields

The most important runtime fields are:

- `JARVIS_SERIAL_PORT`
- `JARVIS_AUDIO_DEVICE_INDEX`
- `JARVIS_AUDIO_DEVICE_RATE`
- `JARVIS_LISTENER_API_URL`
- `JARVIS_OPERATOR_NODE`

On Jetson, prefer a stable serial path such as:

```bash
/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0
```

rather than `/dev/ttyUSB0`, which can move around.

## 5. ESP32 Hardware Setup

### Gateway

The gateway firmware lives in:

- [../hardware/gateway_node/src/main.cpp](../hardware/gateway_node/src/main.cpp)

It stays USB-connected to the Jetson and handles:

- PTT button events
- serial status feedback
- ESP-NOW relay transmission
- ACK / STATUS uplink back to the Jetson listener

### Field Nodes

The field-node firmware lives in:

- [../hardware/field_node/src/main.cpp](../hardware/field_node/src/main.cpp)

Current roles:

- `field_relay` = relay-capable node
- `field_leaf` = downstream leaf node

These are flashed through PlatformIO from:

- `hardware/field_node/platformio.ini`

## 6. Demo Startup Sequences

### A. Manual three-terminal flow

#### Terminal 1: backend

```bash
cd ~/JARVIS_repo/base_station
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### Terminal 2: listener

```bash
cd ~/JARVIS_repo/base_station
source .venv/bin/activate
set -a
source .env
set +a
python headless/serial_ptt_listener.py
```

#### Terminal 3: frontend

```powershell
cd command_center
npm run dev
```

### B. Windows launcher

For the current laptop-plus-Jetson workflow, use:

- [../scripts/start-demo-stack.ps1](../scripts/start-demo-stack.ps1)

That script opens the demo stack in separate terminals and is the easiest way to bring the system up repeatedly during the hackathon.

## 7. What Is Not Part Of The Current Deployment Path

The current docs intentionally do not treat MQTT as part of the primary relay story.

Why:

- the live backend mirrors relay commands to the listener over local HTTP
- the listener writes to the gateway over USB serial
- the gateway and field nodes use ESP-NOW

`mqtt_client.py` remains in the repo as an earlier or alternate transport experiment, but it is not the main path to explain or demonstrate right now.

## 8. First Smoke Checks

### Backend

```bash
curl http://127.0.0.1:8000/health
```

### Frontend

- open `http://localhost:5173`
- verify the connection badge becomes connected

### Listener

- verify it prints `Serial button listener online`
- verify it prints `Relay bridge listening on http://127.0.0.1:8765`

### Relay bridge

```bash
curl http://127.0.0.1:8765/status
```

## 9. Recommended GitHub-Facing Demo Narrative

If you need one setup sentence that matches the code:

> JARVIS currently runs as a local FastAPI base station with a React command center, a Jetson-hosted serial relay bridge, and an ESP-NOW hardware relay chain, while the compute-vision lane is present as an integrated scaffold that will be hardened after the hackathon.
