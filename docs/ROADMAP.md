# Roadmap

System: Joint Autonomous Recon and Vision Integrated Swarm  
Purpose: separate what is already shipped from what is still a deployment target.

## 1. Shipped In The Current Repo

### 1.1 Base station and control flow

- [x] FastAPI base station in [../base_station/api/main.py](../base_station/api/main.py)
- [x] command normalization through [../base_station/core/ai_bridge.py](../base_station/core/ai_bridge.py)
- [x] adaptive gossip path and raft-style comparison path in [../base_station/core/swarm_logic.py](../base_station/core/swarm_logic.py)
- [x] staged execute flow for destructive commands
- [x] WebSocket state streaming to the frontend

### 1.2 Command center

- [x] React command center shell in [../command_center/src/App.jsx](../command_center/src/App.jsx)
- [x] canvas-based tactical map through [../command_center/src/components/SwarmCanvas.jsx](../command_center/src/components/SwarmCanvas.jsx)
- [x] scenario loading and map editor controls
- [x] mission pinning and command history
- [x] browser push-to-talk path

### 1.3 Jetson and relay demo

- [x] Jetson serial listener in [../base_station/headless/serial_ptt_listener.py](../base_station/headless/serial_ptt_listener.py)
- [x] local `/relay` and `/status` bridge hosted by the listener
- [x] gateway ESP32 serial-to-ESP-NOW relay path
- [x] field relay node and leaf node roles
- [x] ACK / STATUS return path from field nodes to Jetson

### 1.4 Vision-integrated scaffold

- [x] compute-drone controller in [../base_station/core/compute_drone_controller.py](../base_station/core/compute_drone_controller.py)
- [x] compute and image-processing endpoints in [../base_station/api/main.py](../base_station/api/main.py)
- [x] compute entities present in populated scenarios

## 2. Highest-Value Next Work

### 2.1 Demo hardening

- [ ] Surface hardware relay ACK / STATUS more clearly in the frontend
- [ ] make startup and recovery more robust when the gateway resets on serial open
- [ ] add a cleaner "load default populated scenario" workflow for demos
- [ ] tighten the operator story around browser PTT vs Jetson PTT so judges see one primary flow

### 2.2 Command semantics

- [ ] move from basic staged execute to fuller task envelopes with versioning, expiry, and cancellation semantics
- [ ] add clearer operator authority / provenance metadata to the command lifecycle
- [ ] improve command-state wording so the UI differentiates recon, movement, and destructive tasks everywhere

### 2.3 Vision lane maturation

- [ ] replace or augment the simulated compute-drone logic with a real image-inference path
- [ ] connect compute outputs back into operator-facing mission state more directly
- [ ] make the recon-to-compute-to-strike flow a first-class demo rather than a secondary scaffold

## 3. Deployment Target

These are the things the markdown should describe as intended deployment behavior, not as already-finished hackathon polish.

### 3.1 Control and trust

- [ ] signed command envelopes
- [ ] anti-replay protection
- [ ] operator authority levels
- [ ] better multi-operator conflict handling

### 3.2 Relay behavior

- [ ] richer task envelopes for field nodes
- [ ] clearer task lifecycle synchronization
- [ ] stronger UI correlation between software propagation and hardware propagation

### 3.3 Vision integration

- [ ] real mission-facing CV inference on edge hardware
- [ ] tighter integration between detections, threat assessments, and staged tasking
- [ ] stronger scenario support for recon-driven target workflows

## 4. Explicitly De-Prioritized For The Current Story

### 4.1 MQTT as the main transport

`mqtt_client.py` remains in the repo, but it is not the primary deployment narrative for the current code.

The live relay path is:

- backend
- listener `/relay`
- USB serial
- gateway ESP32
- ESP-NOW field nodes

If MQTT comes back later, it should be framed as an alternate transport or integration path, not as the core story of the current implementation.

## 5. Recommended Pitch Framing

The cleanest current story is:

1. local-first command and control on Jetson
2. real-time operator visualization in the browser
3. physical relay proof through ESP32 gateway and field nodes
4. integrated compute-vision lane already present in the codebase and ready for hardening after the hackathon
