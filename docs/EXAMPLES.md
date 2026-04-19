# Operator Examples and Test Phrases

This file gives you realistic ways to talk to JARVIS during testing and demos.

Project name: JARVIS (Joint Autonomous Recon and Vision Integrated Swarm)

It is split into:

- `Works with the current parser today`: phrases supported by the implemented `2.0` schema
- `Good next-step phrases`: more doctrinal phrases that fit the direction of travel but are not fully implemented yet

Use this file for:

- Jetson button-to-talk tests
- command-center demos
- judge walkthroughs
- parser validation work

## How To Test In Practice

Current PTT flow with the ESP32 button:

1. Hold the button down
2. Speak the full command while holding
3. End cleanly
4. Pause briefly
5. Release the button

Best current speaking habits:

- speak in one short burst
- use the callsign first
- end with `over` or `out` when possible
- avoid filler words
- prefer one command per transmission

ESP32 LED meaning in the current button demo:

- slow heartbeat: powered on and ready for PTT
- solid on: currently recording while the button is held
- fast blink: processing the last transmission on the Jetson
- two short blinks: command accepted, then returns to ready heartbeat
- four short blinks: error, then returns to ready heartbeat

## Works With The Current Parser Today

These match the implemented parser in [../base_station/core/ai_bridge.py](../base_station/core/ai_bridge.py):

- `MOVE_TO`
- `ATTACK_AREA`
- `AVOID_AREA`
- `HOLD_POSITION`
- `SCAN_AREA`
- `LOITER`
- `MARK`
- `EXECUTE`
- `STANDBY`
- `DISREGARD`
- `ABORT`
- `NO_OP`

The live parser now returns:

- `schema_version: "2.0"`
- `callsign`
- legacy string locations such as `GRID_BRAVO_2`
- typed detail objects such as `target_location_detail`
- `confirmation_required`
- `execution_state`
- `terminal_proword`

### 1. Move command

Spoken:

```text
JARVIS, move to Grid Alpha, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "MOVE_TO",
  "target_location": "GRID_ALPHA",
  "avoid_location": null,
  "target_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_ALPHA",
    "label": "Grid Alpha",
    "sector": "ALPHA"
  },
  "avoid_location_detail": null,
  "confidence": 0.91,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 2. Staged attack command

Spoken:

```text
JARVIS, attack Grid Bravo, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "ATTACK_AREA",
  "target_location": "GRID_BRAVO",
  "avoid_location": null,
  "target_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_BRAVO",
    "label": "Grid Bravo",
    "sector": "BRAVO"
  },
  "avoid_location_detail": null,
  "confidence": 0.93,
  "confirmation_required": true,
  "execution_state": "PENDING_EXECUTE",
  "terminal_proword": "OVER"
}
```

Current system behavior:

1. The attack is staged first
2. The UI shows `Pending Execute`
3. The backend waits for a second transmission:

```text
JARVIS, execute, over.
```

### 3. Execute a staged action

Spoken:

```text
JARVIS, execute, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "EXECUTE",
  "target_location": null,
  "avoid_location": null,
  "target_location_detail": null,
  "avoid_location_detail": null,
  "confidence": 0.99,
  "confirmation_required": false,
  "execution_state": "EXECUTE_REQUESTED",
  "terminal_proword": "OVER"
}
```

### 4. Cancel a staged action

Spoken:

```text
JARVIS, disregard last, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "DISREGARD",
  "target_location": null,
  "avoid_location": null,
  "target_location_detail": null,
  "avoid_location_detail": null,
  "confidence": 0.98,
  "confirmation_required": false,
  "execution_state": "CANCELED",
  "terminal_proword": "OVER"
}
```

### 5. Avoid command

Spoken:

```text
JARVIS, avoid Grid Charlie, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "AVOID_AREA",
  "target_location": null,
  "avoid_location": "GRID_CHARLIE",
  "target_location_detail": null,
  "avoid_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_CHARLIE",
    "label": "Grid Charlie",
    "sector": "CHARLIE"
  },
  "confidence": 0.94,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 6. Recon / scan command

Spoken:

```text
JARVIS, scan Grid Alpha 2, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "SCAN_AREA",
  "target_location": "GRID_ALPHA_2",
  "avoid_location": null,
  "target_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_ALPHA_2",
    "label": "Grid Alpha 2",
    "sector": "ALPHA",
    "subsector": 2
  },
  "avoid_location_detail": null,
  "confidence": 0.92,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 7. Loiter command

Spoken:

```text
JARVIS, loiter Grid Alpha 3, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "LOITER",
  "target_location": "GRID_ALPHA_3",
  "avoid_location": null,
  "target_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_ALPHA_3",
    "label": "Grid Alpha 3",
    "sector": "ALPHA",
    "subsector": 3
  },
  "avoid_location_detail": null,
  "confidence": 0.93,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 8. Mark command

Spoken:

```text
JARVIS, mark Grid Bravo 2, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "MARK",
  "target_location": "GRID_BRAVO_2",
  "avoid_location": null,
  "target_location_detail": {
    "type": "named_sector",
    "canonical": "GRID_BRAVO_2",
    "label": "Grid Bravo 2",
    "sector": "BRAVO",
    "subsector": 2
  },
  "avoid_location_detail": null,
  "confidence": 0.9,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 9. Standby command

Spoken:

```text
JARVIS, standby, over.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "STANDBY",
  "target_location": null,
  "avoid_location": null,
  "target_location_detail": null,
  "avoid_location_detail": null,
  "confidence": 0.97,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OVER"
}
```

### 10. Abort command

Spoken:

```text
JARVIS, abort mission, out.
```

Expected JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "ABORT",
  "target_location": null,
  "avoid_location": null,
  "target_location_detail": null,
  "avoid_location_detail": null,
  "confidence": 0.99,
  "confirmation_required": false,
  "execution_state": "NONE",
  "terminal_proword": "OUT"
}
```

## Best Judge-Facing Demo Phrases Right Now

These are the lines I would actually use in front of judges with the current implementation:

1. `JARVIS, scan Grid Alpha 2, over.`
2. `JARVIS, loiter Grid Alpha 3, over.`
3. `JARVIS, mark Grid Bravo 2, over.`
4. `JARVIS, attack Grid Bravo, over.`
5. `JARVIS, execute, over.`
6. `JARVIS, disregard last, over.`
7. `JARVIS, all units, abort, out.`

These already sound more disciplined than plain conversational prompts and they line up with the parser you have today.

## Good Next-Step Phrases

These are the phrases I recommend we move toward because they sound better in front of military and national-security judges, but they need additional implementation work before they become first-class parser inputs.

### A. Named control measures

Spoken:

```text
JARVIS, hold at Phase Line Blue, over.
```

Recommended future parsed JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "HOLD_POSITION",
  "target_location": null,
  "target_location_detail": {
    "type": "named_line",
    "name": "PHASE_LINE_BLUE"
  },
  "avoid_location": null,
  "avoid_location_detail": null,
  "confirmation_required": false,
  "execution_state": "NONE",
  "confidence": 0.89,
  "terminal_proword": "OVER"
}
```

### B. Sector phrasing instead of grid phrasing

Spoken:

```text
JARVIS, move to Sector Bravo 3, over.
```

Recommended future parsed JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "MOVE_TO",
  "target_location": "GRID_BRAVO_3",
  "target_location_detail": {
    "type": "named_sector",
    "sector": "BRAVO",
    "subsector": 3
  },
  "avoid_location": null,
  "avoid_location_detail": null,
  "confirmation_required": false,
  "execution_state": "NONE",
  "confidence": 0.93,
  "terminal_proword": "OVER"
}
```

### C. TRP / NAI references

Spoken:

```text
JARVIS, Reaper flight, scan NAI two, over.
```

Recommended future parsed JSON:

```json
{
  "schema_version": "2.0",
  "callsign": "JARVIS",
  "intent": "swarm_command",
  "goal": "SCAN_AREA",
  "target_location": null,
  "target_location_detail": {
    "type": "named_area",
    "name": "NAI_2"
  },
  "avoid_location": null,
  "avoid_location_detail": null,
  "confirmation_required": false,
  "execution_state": "NONE",
  "confidence": 0.9,
  "terminal_proword": "OVER"
}
```

## Suggested Parser Test Matrix

Use this when validating future parser changes:

| Type | Spoken phrase | Expected goal |
|---|---|---|
| Move | `JARVIS, move to Grid Alpha, over.` | `MOVE_TO` |
| Scan | `JARVIS, scan Grid Alpha 2, over.` | `SCAN_AREA` |
| Loiter | `JARVIS, loiter Grid Alpha 3, over.` | `LOITER` |
| Mark | `JARVIS, mark Grid Bravo 2, over.` | `MARK` |
| Hold | `JARVIS, hold position, over.` | `HOLD_POSITION` |
| Attack stage | `JARVIS, attack Grid Bravo, over.` | `ATTACK_AREA` with `PENDING_EXECUTE` |
| Confirm | `JARVIS, execute, over.` | `EXECUTE` |
| Cancel | `JARVIS, disregard last, over.` | `DISREGARD` |
| Abort | `JARVIS, abort mission, out.` | `ABORT` |

## One-Sentence Demo Framing

If you need one clean line to explain the examples to judges:

> We are intentionally testing short radio-style commands with named sectors and explicit execute authority, because that is a better fit for speech recognition, operator workload, and DDIL command-and-control than forcing the operator to speak raw coordinate strings.
