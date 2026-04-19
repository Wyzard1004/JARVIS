# Testing Guide

This guide is for the current JARVIS stack:

- FastAPI backend
- React command center
- optional Jetson serial listener
- optional ESP32 gateway plus field-node relay demo

## 1. Baseline Runtime Checks

Start these first:

### Backend

```bash
cd ~/JARVIS_repo/base_station
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd command_center
npm run dev
```

### Optional Jetson listener

```bash
cd ~/JARVIS_repo/base_station
source .venv/bin/activate
set -a
source .env
set +a
python headless/serial_ptt_listener.py
```

## 2. Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected:

- HTTP 200
- `"status": "operational"`

## 3. Load A Populated Scenario

The backend starts on a blank workspace unless you load one.

```bash
curl -X POST http://127.0.0.1:8000/api/scenarios/load \
  -H "Content-Type: application/json" \
  -d '{"scenario_key":"scenarios/village_reconnaissance_patrol.json"}'
```

Then verify:

```bash
curl http://127.0.0.1:8000/api/swarm-state | python3 -m json.tool
```

Expected:

- non-empty `nodes`
- scenario metadata present

## 4. Direct Command Path

Test the main command endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, scan Grid Alpha 2, over."}' | python3 -m json.tool
```

Expected:

- `event: "gossip_update"`
- `parsed_command.goal: "SCAN_AREA"`
- `parsed_command.execution_state: "NONE"`

## 5. Staged Execute Flow

### Stage

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, attack Grid Bravo, over."}' | python3 -m json.tool
```

Expected:

- `event: "command_pending"`
- `status: "pending_execute"`
- `pending_execute.present: true`

### Execute

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, execute, over."}' | python3 -m json.tool
```

Expected:

- `event: "gossip_update"`
- `parsed_command.goal: "ATTACK_AREA"`
- `parsed_command.execution_state: "EXECUTED"`

### Cancel

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, disregard last, over."}' | python3 -m json.tool
```

Expected when something is staged:

- `event: "command_canceled"`

Expected when nothing is staged:

- `status: "ignored"`
- message explaining there is no pending destructive command

## 6. Frontend Smoke Test

Open:

- `http://localhost:5173`

Verify:

- header loads
- connection indicator becomes connected
- tactical map renders
- system-status panel shows live state
- mission banner updates when you issue a command

The current UI is built around `SwarmCanvas`, not just a simple force graph.

## 7. WebSocket Smoke Test

```bash
python3 - <<'PY'
import asyncio
import json
import websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/ws/swarm") as ws:
        print(await ws.recv())
        print(await ws.recv())
        update = await ws.recv()
        print(json.loads(update).get("event"))

asyncio.run(main())
PY
```

Expected:

- welcome message
- initial swarm state
- later command lifecycle events such as `gossip_update` or `command_pending`

## 8. Jetson Push-To-Talk Test

This tests the real button-driven command path.

Prerequisites:

- backend running on Jetson
- listener running on Jetson
- gateway ESP32 connected over USB
- audio device configured in `.env`

Expected listener startup lines include:

- `Serial button listener online`
- `Posting commands to http://127.0.0.1:8000/api/transcribe-command`
- `Relay bridge listening on http://127.0.0.1:8765`

Then:

1. hold the gateway button
2. speak `JARVIS, scan Grid Alpha 2, over.`
3. release

Expected:

- `PTT_DOWN`
- `PTT_UP`
- transcript line
- parsed goal line

## 9. Relay Hardware Test

This validates the current hardware bridge path:

- backend
- listener `/relay`
- gateway ESP32
- `drone-1`
- `drone-2`

### Check bridge status

```bash
curl http://127.0.0.1:8765/status | python3 -m json.tool
```

Expected fields:

- `last_packet_sent`
- `recent_acks`
- `field_status`

### Trigger a direct relayable command

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, recon Bravo three, over."}' | python3 -m json.tool
```

Expected listener output should include lines similar to:

- `Gateway STATUS: node=drone-1 state=RECEIVED_COMMAND`
- `Gateway STATUS: node=drone-1 state=FORWARDED`
- `Gateway STATUS: node=drone-2 state=RECEIVED_COMMAND`
- `Gateway ACK: packet=... node=drone-1 hop=0`
- `Gateway ACK: packet=... node=drone-2 hop=1`

### Trigger a staged destructive command

Stage:

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, attack Grid Bravo, over."}' | python3 -m json.tool
```

Execute:

```bash
curl -X POST http://127.0.0.1:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text":"JARVIS, execute, over."}' | python3 -m json.tool
```

Expected listener output should transition from `RECEIVED_STAGED` to `RECEIVED_EXECUTE`.

## 10. Compute / Vision Lane Smoke Test

This is not the main demo path yet, but it is part of the integrated codebase.

Check available compute endpoints by reviewing:

- [../base_station/api/main.py](../base_station/api/main.py)
- [../base_station/core/compute_drone_controller.py](../base_station/core/compute_drone_controller.py)

At minimum, verify one compute route responds when a scenario includes compute drones.

## 11. Current Pass Criteria

Treat the system as demo-ready when these all pass:

- backend health check
- populated scenario loaded
- direct command dispatch works
- staged execute flow works
- frontend connects and updates
- Jetson listener can transcribe and dispatch
- relay bridge reports ACK / STATUS from field nodes

## 12. Honest Demo Framing

Use this sentence if someone asks what is fully live:

> The command, relay, and visualization stack is live end to end today; the compute-vision lane is already integrated in the codebase but remains a scaffolded workflow rather than the primary hardware demo.
