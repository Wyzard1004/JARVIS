# Overview

Project Name: JARVIS (Joint Autonomous Recon and Vision Integrated Swarm)  
Hackathon: Critical Ops Hackathon (April 2026)

## 1. What The System Is

JARVIS is a local-first swarm command-and-relay stack for disconnected, denied, degraded, intermittent, or limited-bandwidth environments.

The repo is not just a UI mockup and it is not just a voice assistant. The working stack today combines:

- operator command intake
- swarm-state and mission dispatch logic
- a live React command center
- a Jetson-hosted serial relay bridge
- an ESP32 gateway plus field-node relay demo

The main story the code supports today is:

> an operator issues a command, the base station normalizes and dispatches it, the UI updates in real time, and the same command can be mirrored into a physical ESP-NOW relay chain.

## 2. What "Vision Integrated" Means Right Now

The new name reflects the codebase, but the docs should stay honest.

The repo already includes:

- compute-drone entities in scenarios
- compute-drone API endpoints in [../base_station/api/main.py](../base_station/api/main.py)
- simulated target detection and strike-decision logic in [../base_station/core/compute_drone_controller.py](../base_station/core/compute_drone_controller.py)

What is not yet fully deployed end to end is a production computer-vision pipeline on the live hardware relay demo. In this repo, the vision lane is a meaningful implemented scaffold and integration point, but it is not the primary live demo path yet.

## 3. Current Live Architecture

### A. Command Ingress

Commands enter through one of three live paths:

- browser push-to-talk in the React command center
- direct backend requests to `/api/voice-command`
- Jetson plus ESP32 push-to-talk through [../base_station/headless/serial_ptt_listener.py](../base_station/headless/serial_ptt_listener.py)

The route name `/api/voice-command` is legacy. It also accepts already-structured command payloads.

### B. Backend Runtime

The backend in [../base_station/api/main.py](../base_station/api/main.py) is the central integration hub.

It currently handles:

- command parsing and normalization
- staged execute flow for destructive commands
- scenario loading and map-editor persistence
- operator / soldier status routes
- compute-drone and image-processing routes
- WebSocket updates to the frontend
- relay mirroring to the Jetson listener's local `/relay` endpoint

The swarm runtime in [../base_station/core/swarm_logic.py](../base_station/core/swarm_logic.py) provides:

- adaptive gossip propagation
- a raft-style comparison path
- scenario-backed topology
- mission and propagation state
- delivery summaries and timing output

### C. Frontend Command Center

The UI in [../command_center/src/App.jsx](../command_center/src/App.jsx) is broader than a simple graph.

It currently includes:

- a canvas-based tactical map through [../command_center/src/components/SwarmCanvas.jsx](../command_center/src/components/SwarmCanvas.jsx)
- a pinned mission banner
- command history
- soldier selection
- scenario loading
- map editing and overlays
- suggested commands
- browser push-to-talk

### D. Relay Hardware Path

The current hardware path is:

1. backend sends a relayable command event
2. Jetson listener accepts it on local `/relay`
3. listener writes `RELAY ...` over USB serial to the gateway ESP32
4. gateway sends encrypted relay packets over ESP-NOW
5. field nodes acknowledge, report status, and optionally forward

This path is implemented in:

- [../base_station/headless/serial_ptt_listener.py](../base_station/headless/serial_ptt_listener.py)
- [../hardware/gateway_node/src/main.cpp](../hardware/gateway_node/src/main.cpp)
- [../hardware/field_node/src/main.cpp](../hardware/field_node/src/main.cpp)
- [../hardware/common/relay_protocol.h](../hardware/common/relay_protocol.h)

## 4. What Is Real Today Vs. What Is Still A Hackathon Shortcut

### Real Today

- local FastAPI backend
- live WebSocket UI
- command parsing with staged execute behavior
- scenario loading and map editing
- Jetson-based serial PTT path
- Jetson-to-ESP32 relay bridge
- ESP-NOW field-node relay behavior
- compute-drone and image-processing API scaffold

### Still A Shortcut Or Compatibility Artifact

- `gossip_update` is still the main UI event name even when the selected comparison path is not literally gossip-only
- `/api/voice-command` is still the name of the main command intake route
- `mqtt_client.py` exists, but it is not the primary live relay path
- some hardware validation is still best demonstrated through ACK / STATUS logs rather than a polished hardware telemetry panel in the UI

## 5. Deployment Framing

The best honest deployment framing for this repo is:

### Current deployment shape

- Jetson hosts the backend and the serial relay bridge
- laptop or desktop hosts the React command center
- gateway ESP32 stays tethered to the Jetson
- two field ESP32 nodes demonstrate bounded multi-hop relay

### Intended hardened deployment

- stronger task envelopes and authority checks
- explicit task versioning and cancellation semantics
- richer UI surfacing of hardware acknowledgements
- more mature compute-vision integration for recon-to-strike workflows

## 6. Why This Repo Exists

This repository is trying to prove three things at once:

1. command-and-control can stay local and resilient in DDIL conditions
2. swarm state and relay behavior can be made legible to operators in real time
3. the same architecture can grow into a more vision-driven recon-to-decision stack without changing the core control model
