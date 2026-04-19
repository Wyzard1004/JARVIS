# Overview

Project Name: JARVIS (Joint Adaptive Relay for Variable Interoperable Swarms)
Hackathon: Critical Ops Hackathon (April 2026)

1. Target Problem Statements

Primary: Problem 10 (Swarm Coordination Protocol for Contested Environments)

"Build a multi-agent simulation in which a team of drones must collaboratively search a defined area and report objects of interest back to a base station while maintaining coordination even when individual agents lose communication intermittently. Implement and compare at least two swarm consensus algorithms. All results should be visualized and benchmarked."

Secondary: Problem 16 (Edge Inference)

"Optimize and deploy open-source AI models for real-time edge inference on resource-constrained hardware in disconnected, denied, or intermittent (DDIL) environments."

2. Project Overview and Mission

JARVIS is a contested-environment swarm coordination system designed for DDIL operations.

The current repo is centered on resilient coordination, not voice as the primary story. Human operators act as nodes in the command network, and commands can enter the system either as direct structured payloads or through an optional language/audio adapter. Once an intent is normalized, the swarm executes coordination logic using a leaderless adaptive gossip protocol or a leader-based TCP/Raft-style baseline for comparison.

The hackathon "wow" factor is that the core logic runs locally on an Nvidia Jetson Orin, broadcasts to a React command center in real time, and can be mirrored to ESP32 hardware for a physical propagation demo. That directly serves Problem 10's simulation, visualization, and benchmark requirements while still leaving room for Problem 16's edge inference story.

3. System Architecture and Tech Stack

A. Hardware Layer

Nvidia Jetson Orin: The edge compute node that hosts FastAPI, the consensus runtime, and optional local LLM tooling.

ESP32 Microcontrollers: Physical representatives of field nodes and relays for the hardware demo path.

B. Command and Intent Layer

Primary input: direct structured swarm commands submitted by the UI or tests.

Optional input: text or audio commands routed through `ai_bridge.py`.

LLM path: Ollama running a local model to normalize operator language into safe command JSON.

Audio path: ElevenLabs helpers for speech-to-text and text-to-speech when those interfaces are useful.

C. Backend and Communications

API: Python FastAPI for orchestration and integration.

Graph Logic: Python + NetworkX for topology, propagation, disruption handling, and consensus simulation.

Messaging: Mosquitto MQTT for hardware publishing when the ESP32 path is connected.

Sync: WebSockets from FastAPI to React for real-time state updates.

D. Frontend Command Center

Framework: React + Vite + Tailwind CSS.

Visualization: D3-based swarm graph and live state panels.

Role: Show topology, propagation order, node activity, and benchmark-driven state in a single operator-facing view.

4. Live Demo Flow

1. Operator issues a swarm command.
   - Preferred current framing: structured command from the UI or a test payload.
   - Optional framing: voice/text command converted by `ai_bridge.py`.
2. Backend normalizes the command into a safe swarm intent.
3. `swarm_logic.py` executes either adaptive gossip or the TCP/Raft-style baseline.
4. FastAPI broadcasts the resulting topology and state transitions to the React UI.
5. When hardware is enabled, the same command path can be mirrored to MQTT and ESP-NOW for a physical relay demo.
6. Benchmark outputs explain latency, bandwidth, and fault-tolerance tradeoffs between the two coordination approaches.

5. API and Data Contracts

Normalized command shape:

```json
{
  "intent": "swarm_command",
  "target_location": "Grid Alpha",
  "action_code": "SEARCH",
  "consensus_algorithm": "gossip",
  "origin": "soldier-1"
}
```

Representative WebSocket payload:

```json
{
  "event": "gossip_update",
  "algorithm": "gossip",
  "active_nodes": ["gateway", "recon-1", "attack-1"],
  "target_x": 150,
  "target_y": -50,
  "status": "propagating",
  "benchmark": {
    "latency": {
      "gossip_avg_ms": 0,
      "raft_avg_ms": 0
    }
  }
}
```

Note: the event name `gossip_update` remains in the current implementation for frontend compatibility, even when the selected algorithm is the TCP/Raft baseline.

The command lifecycle now also includes:

- `command_pending` when an `ATTACK_AREA` command is staged and waiting on `EXECUTE`
- `command_canceled` when a staged command is cleared by `DISREGARD`
