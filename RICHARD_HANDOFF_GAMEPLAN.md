# Richard Handoff and Development Plan

## What This Repo Actually Is

This repository is no longer just a planning scaffold. It now contains a runnable swarm-simulation stack for `JARVIS` (Joint Adaptive Relay for Variable Interoperable Swarms), centered on:

- swarm coordination in contested or disconnected environments
- adaptive gossip vs. TCP/Raft-style consensus comparison
- a React command center with live topology updates
- optional language/audio tooling on top of the command path
- an eventual hardware demo path through MQTT and ESP32 relays

The strongest part of the repo today is the swarm runtime and the backend/frontend integration around it.
The biggest remaining gaps are hardware wiring, UI rebalancing, and keeping the docs aligned with the code.

## Current Implementation Snapshot

As of April 18, 2026, the important files look like this:

- `base_station/api/main.py`
  - working FastAPI app
  - health endpoint, swarm-state endpoint, WebSocket updates
  - command dispatch wired to `swarm_logic.py`
  - legacy `POST /api/voice-command` route already accepts direct structured payloads
- `base_station/core/swarm_logic.py`
  - implemented adaptive gossip runtime
  - implemented TCP/Raft-style baseline
  - benchmark data, disruption modeling, mission state, delivery summaries
- `base_station/core/ai_bridge.py`
  - implemented rule-based parsing
  - optional Ollama-backed parsing
  - speech-to-text and text-to-speech helper functions
  - safe fallback behavior
- `base_station/core/mqtt_client.py`
  - implemented MQTT client utilities
  - not yet wired into the live FastAPI dispatch loop
- `command_center/src/`
  - working command center UI
  - graph, status panel, command history, WebSocket connection
  - push-to-talk still present, though the project story should now be consensus-first

## Richard's Assigned Lane

Richard's lane is still `base_station/core/ai_bridge.py`, but the framing should be updated:

your job is to maintain the **operator intent adapter**, not to make voice the center of the system.

That means:

1. Normalize operator language into a safe command object.
2. Support direct alignment with the shared swarm-command schema.
3. Use Ollama when available, but never make the system depend on it.
4. Keep audio optional and non-blocking.
5. Preserve graceful fallback behavior.

## Current Command Contract

The swarm path already works best when everything converges on a predictable payload like:

```json
{
  "intent": "swarm_command",
  "target_location": "Grid Alpha",
  "action_code": "SEARCH",
  "consensus_algorithm": "gossip",
  "origin": "soldier-1"
}
```

Your module should help produce and support that shape, but the backend can also receive it directly without the AI path.

## Recommended Priorities for Richard

### Phase 1: Protect the Schema

Treat the shared swarm intent schema as the primary contract.

Goals:

1. Keep location normalization stable.
2. Keep goal-to-action mapping predictable.
3. Keep confidence and fallback behavior consistent.
4. Make sure direct commands and AI-parsed commands land in the same downstream format.

### Phase 2: Keep the AI Path Optional

The current system already supports direct structured payloads. That is good and should stay true.

Goals:

1. If Ollama is unavailable, the command path still works.
2. If audio is unavailable, the command path still works.
3. If parsing fails, the system returns a safe fallback instead of crashing.

### Phase 3: Improve Reliability Before Polish

Hackathon demos fail when polish depends on fragile infrastructure.

Goals:

1. Test parser output on a small set of real command phrases.
2. Make sure `NO_OP` is returned for unclear or unsafe requests.
3. Keep the command path deterministic enough for live demos.
4. Only polish TTS after the command contract is stable.

## Suggested Build Order from Richard's Perspective

If Richard continues work from the current repo state, the best order is:

1. stabilize the command schema
2. strengthen AI fallback behavior
3. align `ai_bridge.py` output with direct payload expectations
4. add more tests/examples for operator phrasing
5. only then improve STT/TTS polish

## Practical First Tasks

These are the highest-leverage next tasks in Richard's lane:

1. Make sure `process_voice_command()` and direct payloads produce the same downstream intent shape.
2. Add or refine sample phrases for move, search, attack, avoid, hold, and abort behaviors.
3. Keep confidence and fallback behavior easy to reason about during the demo.
4. Avoid introducing any dependency that would block the swarm runtime when audio or LLM services are down.

## Risks to Watch

These are the real risks in the current repo:

- the route name `/api/voice-command` still suggests voice-first behavior even though direct commands already work
- the UI is still framed around push-to-talk more than structured swarm control
- MQTT exists as a module but is not yet in the live dispatch path
- some historical docs still described the repo as emptier or more voice-centric than it is

## Best Next Step

If you want the most leverage from Richard's lane, the best immediate move is:

keep `ai_bridge.py` reliable, optional, and schema-first while the rest of the project continues to center on swarm consensus.

That preserves the strong part of the current repo:

- consensus and visualization stay primary
- the AI path remains useful
- the system degrades gracefully
- teammates can build around a stable contract
