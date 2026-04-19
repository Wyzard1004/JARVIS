# JARVIS: Joint Autonomous Recon and Vision Integrated Swarm

> Hardware-in-the-loop command, relay, and reconnaissance stack for DDIL swarm demos.

This repository is the current hackathon implementation of JARVIS. The live codebase combines:

- a FastAPI base station that normalizes commands and runs swarm coordination
- a React command center with a tactical map, scenario tools, and live mission state
- a Jetson-side serial push-to-talk listener that also acts as the local relay bridge
- ESP32 gateway and field-node firmware that relay commands over ESP-NOW
- an early compute-drone and image-processing lane that supports the "vision integrated" part of the project story

## What The Repo Actually Does Today

The current deployment story is:

1. A command enters through the browser, a direct API request, or the Jetson/ESP32 push-to-talk path.
2. `base_station/api/main.py` normalizes the command and dispatches it through the swarm runtime.
3. The backend streams state updates to the React UI over WebSocket.
4. The backend mirrors relayable command events to the Jetson listener's local `/relay` bridge.
5. `base_station/headless/serial_ptt_listener.py` sends those packets over USB serial to the gateway ESP32.
6. The gateway rebroadcasts them over ESP-NOW to the field nodes, which acknowledge and optionally forward them.

That is the real deployed relay path in this repo right now. The docs below are written around that path, not around earlier MQTT-only plans.

## Current Reality Vs. Deployment Target

This repo was built under hackathon time pressure, so some internal names and modules are still legacy:

- `/api/voice-command` accepts direct structured commands too; the route name is historical
- `gossip_update` is still the main UI event name even when the backend is using the raft-style comparison path
- `mqtt_client.py` exists, but the live relay demo path is `serial_ptt_listener.py` plus ESP-NOW, not MQTT
- the project already includes compute-drone and image-processing endpoints, but the main live demo is still command, relay, and visualization rather than full autonomous onboard vision

The intended deployment direction is:

- hardened task envelopes and authority checks
- stronger hardware/UI timing synchronization
- richer compute-vision integration using the existing compute-drone lane
- broader scenario coverage and more realistic contested-network behavior

## Live Architecture

```text
+--------------------------------------------------------------+
| Operator Inputs                                              |
| - browser push-to-talk                                       |
| - typed / direct API command                                 |
| - Jetson + ESP32 push-to-talk                                |
+--------------------------------------------------------------+
                             |
                             v
+--------------------------------------------------------------+
| Jetson Base Station                                          |
| FastAPI + ai_bridge + swarm_logic                            |
| - command normalization                                      |
| - gossip / raft-style comparison                             |
| - mission state + scenarios + map editor state               |
| - WebSocket stream to UI                                     |
+--------------------------------------------------------------+
                 |                                  |
                 v                                  v
+------------------------------------+   +---------------------------+
| React Command Center               |   | Jetson Relay Bridge       |
| - SwarmCanvas tactical map         |   | serial_ptt_listener.py    |
| - mission banner + history         |   | /relay + /status          |
| - scenario loader + map editor     |   | USB serial to gateway     |
+------------------------------------+   +---------------------------+
                                                     |
                                                     v
                                      +------------------------------+
                                      | ESP32 Relay Demo             |
                                      | gateway -> drone-1 -> drone-2|
                                      | ESP-NOW + ACK / STATUS       |
                                      +------------------------------+
```

## Major Components

### Backend

- [base_station/api/main.py](base_station/api/main.py)
  - FastAPI routes
  - WebSocket broadcast
  - command lifecycle
  - scenario loading and map-editor endpoints
  - hardware relay mirroring
- [base_station/core/swarm_logic.py](base_station/core/swarm_logic.py)
  - topology and scenario state
  - adaptive gossip path
  - raft-style comparison path
  - delivery summaries and timing
- [base_station/core/ai_bridge.py](base_station/core/ai_bridge.py)
  - safe command parsing
  - radio-style phrasing support
  - staged execute flow for destructive commands
- [base_station/core/compute_drone_controller.py](base_station/core/compute_drone_controller.py)
  - simulated image reception
  - target detection / threat classification scaffold
  - strike-decision support objects

### Jetson Runtime

- [base_station/headless/serial_ptt_listener.py](base_station/headless/serial_ptt_listener.py)
  - serial PTT listener
  - audio upload to `/api/transcribe-command`
  - local `/relay` and `/status` bridge
  - gateway ACK / STATUS handling
- [base_station/headless/jetson_listener.py](base_station/headless/jetson_listener.py)
  - wake-word listener path
  - still present, but not the main hardware demo path right now

### Frontend

- [command_center/src/App.jsx](command_center/src/App.jsx)
  - application shell
  - WebSocket state handling
  - mission pinning
  - scenario and map editor controls
- [command_center/src/components/SwarmCanvas.jsx](command_center/src/components/SwarmCanvas.jsx)
  - canvas-based tactical map
  - communication playback overlay
  - continuous-world to 8x8 grid projection
- [command_center/src/components/PushToTalkButton.jsx](command_center/src/components/PushToTalkButton.jsx)
  - browser microphone path

### Hardware

- [hardware/gateway_node/src/main.cpp](hardware/gateway_node/src/main.cpp)
  - USB serial gateway
  - ESP-NOW transmit / receive
  - relay packet translation
- [hardware/field_node/src/main.cpp](hardware/field_node/src/main.cpp)
  - relay node and leaf node behavior
  - duplicate suppression
  - ACK / STATUS responses
  - bounded forwarding
- [hardware/common/relay_protocol.h](hardware/common/relay_protocol.h)
  - shared packet format
  - encrypted relay helpers

## What "Vision Integrated" Means In This Repo

The rename is accurate, but the implementation is staged.

Today, the codebase already has:

- compute-drone state in scenarios
- compute-drone API endpoints in `base_station/api/main.py`
- a simulated image-processing and threat-analysis controller in `base_station/core/compute_drone_controller.py`

What it does not yet have is a production-grade, fielded computer-vision inference pipeline running end to end on the live hardware demo. The markdown in this repo treats that lane as an implemented scaffold and a deployment target, not as something already fully operational in the field demo.

## Quick Start

### 1. Backend

```powershell
cd base_station
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend

```powershell
cd command_center
npm install
npm run dev
```

### 3. Jetson Listener / Relay Bridge

```bash
cd base_station
source .venv/bin/activate
set -a
source .env
set +a
python headless/serial_ptt_listener.py
```

### 4. Optional Windows Launcher

If you are running the website locally on a Windows laptop while targeting a Jetson backend, use:

- [scripts/start-demo-stack.ps1](scripts/start-demo-stack.ps1)

That script opens backend, listener, and frontend terminals for the current demo workflow.

## Important Current Notes

- The backend starts on a blank workspace unless you load a populated scenario.
- The UI is broader than a simple graph viewer now; it includes scenario loading, map editing, suggested commands, command history, and pinned mission state.
- The live relay hardware path is USB serial plus ESP-NOW.
- MQTT is not the primary deployment story in the current repo.

## Docs

- [docs/README.md](docs/README.md)
- [docs/OVERVIEW.md](docs/OVERVIEW.md)
- [docs/SETUP.md](docs/SETUP.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/COMMAND_SCHEMA.md](docs/COMMAND_SCHEMA.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/CHANGE_PROPOSAL.md](docs/CHANGE_PROPOSAL.md)
- [docs/EXAMPLES.md](docs/EXAMPLES.md)
- [docs/SOURCES.md](docs/SOURCES.md)

Anything under `docs/archive/` is preserved history, not the current source of truth.
