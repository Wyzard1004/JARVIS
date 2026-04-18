# Richard Handoff and Development Plan

## What This Repo Actually Is

This repository is a planning scaffold for `JARVIS` (Joint Adaptive Resilient Voice Integrated Swarm), a hackathon project aimed at:

- swarm coordination in contested or disconnected environments
- local edge inference on a Jetson Orin
- a live demo that combines voice commands, backend orchestration, visualization, and ESP32 hardware

The strongest part of this handoff is the written architecture and work split.
The weakest part is implementation coverage: almost every code file in the repo is currently empty.

## What You Were Handed

The useful handoff materials are:

- `development_gameplan.md`
  - the original team execution plan with ownership by person
- `overview.md`
  - the project pitch, system architecture, and expected API/data contracts
- `repository_structure.md`
  - intended monorepo layout and folder ownership guidance
- `.gitignore`
  - basic ignore rules are already present

The current implementation state is:

- `base_station/api/main.py`: empty
- `base_station/core/ai_bridge.py`: empty
- `base_station/core/swarm_logic.py`: empty
- `base_station/core/mqtt_client.py`: empty
- `base_station/requirements.txt`: empty
- `command_center/package.json`: empty
- `command_center/tailwind.config.js`: empty
- `command_center/vite.config.js`: empty
- `hardware/gateway_node/gateway_node.ino`: empty
- `hardware/field_node/field_node.ino`: empty
- `simulations/tcp_vs_gossip.py`: empty
- `README.md`: empty
- `docs/mission_canvas.md`: empty

## Bottom-Line Assessment

This is not a working codebase yet.
It is a project brief plus a folder layout.

That is still valuable because it gives you:

- the intended architecture
- the hackathon story
- team role boundaries
- the target interfaces between modules
- a clear place for your workstream

## Richard's Assigned Lane

According to `development_gameplan.md`, Richard owns the AI pipeline bridge in:

- `base_station/core/ai_bridge.py`

Your responsibility is to turn raw text or speech-derived text into a safe command object and a spoken confirmation.

The intended flow is:

1. Receive transcribed text.
2. Send it to local Ollama on the Jetson.
3. Force the model to return strict JSON.
4. Validate and normalize the JSON.
5. Return a predictable command payload.
6. Generate a spoken confirmation.

Expected output shape from the docs:

```json
{
  "intent": "swarm_redeploy",
  "target_location": "Grid Alpha",
  "action_code": "RED_ALERT",
  "confidence": 0.95
}
```

## Recommended Game Plan

### Phase 1: Make the Repo Real

Before building AI logic, create the minimum runnable foundation:

1. Fill in `base_station/requirements.txt`.
2. Expand `base_station/.env` with the variables the code will actually need.
3. Put a minimal FastAPI app in `base_station/api/main.py`.
4. Add a useful root `README.md` with setup and demo steps.

Goal:
make the repository installable and understandable before adding intelligence.

### Phase 2: Build Richard's Module First

Implement `base_station/core/ai_bridge.py` as a standalone, testable module with one public function:

```python
process_voice_command(transcribed_text: str) -> dict
```

Inside that module, separate the responsibilities:

- `parse_intent_with_ollama(text)`
- `validate_command_payload(payload)`
- `synthesize_confirmation(text)`
- `process_voice_command(text)`

Goal:
let your module be tested before the web app, hardware, or UI are finished.

### Phase 3: Use Safe Fallbacks for Demo Reliability

Hackathon demos fail when external pieces are not ready.
Build fallback behavior from day one:

- If Ollama is down, return a mock but valid command payload.
- If the model returns invalid JSON, retry once and then fall back.
- If ElevenLabs is unavailable, return text only and log that audio was skipped.

Goal:
the system should degrade gracefully instead of crashing on stage.

### Phase 4: Lock the Contract Between Teams

Before the rest of the team builds around your module, freeze these interfaces:

- input to `process_voice_command`
- output JSON schema
- error response shape
- confirmation text format

Goal:
William can wire the API, Giulia can consume the command intent, and nobody has to guess.

### Phase 5: Add a Demo Mode

Create an environment-driven mock mode so the project can run even without:

- Jetson hardware
- local Ollama
- ElevenLabs credentials
- ESP32 devices

Goal:
you can still demo the full flow on a laptop using simulated outputs.

## Suggested Build Order for the Whole Project

If you want the fastest path from planning to something demoable, build in this order:

1. `base_station/requirements.txt`
2. `base_station/core/ai_bridge.py`
3. `base_station/api/main.py`
4. `base_station/core/swarm_logic.py` with mocked graph output first
5. `base_station/core/mqtt_client.py` with stub publish behavior first
6. `command_center/` basic Vite app
7. `simulations/tcp_vs_gossip.py`
8. ESP32 firmware last

Reason:
the backend contracts unlock almost everything else, while hardware can stay simulated until later.

## Practical First Tasks for Richard

These are the highest-leverage next tasks for you personally:

1. Define the command schema in plain English and Python terms.
2. Implement the Ollama request and response parsing.
3. Add strict JSON validation and fallback behavior.
4. Create a small local test script with sample phrases like:
   - `"Swarm, push to Grid Alpha"`
   - `"Send units to sector 4"`
   - `"Abort the current route"`
5. Return a consistent command object every time.
6. Only after that, wire in ElevenLabs.

## Risks in the Current Handoff

These are the main risks hidden inside the current repo:

- The architecture is documented, but no subsystem is implemented yet.
- The frontend is described, but there is no `src/` application code.
- The backend structure exists, but all Python files are placeholders.
- The hardware firmware files exist, but contain no logic.
- There are no tests, no pinned dependencies, and no setup instructions.
- The docs assume a multi-person team, but the current state requires a solo bootstrap mindset.

## Best Next Step

If you continue from this handoff, the best immediate move is:

build `ai_bridge.py` plus a tiny FastAPI health/test endpoint first.

That gives you:

- a real starting point
- an artifact tied directly to your assigned lane
- something the rest of the system can integrate with
- a clean foundation for future automation

## Automation-Friendly Follow-Up

Once planning is done, this repo is well suited for automation because the next tasks are separable and repeatable:

- bootstrap dependencies
- implement `ai_bridge.py`
- add mock/demo mode
- scaffold FastAPI routes
- create README/setup docs
- add simple tests for command parsing

That means you can later automate progress in small, low-risk chunks instead of trying to automate the whole project at once.
