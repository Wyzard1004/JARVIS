# Command Schema and Examples

This file documents the current parser contract implemented in [../base_station/core/ai_bridge.py](../base_station/core/ai_bridge.py).

It reflects the current JARVIS stack: Joint Autonomous Recon and Vision Integrated Swarm.

The schema now supports:

- callsign-first voice phrasing
- staged attack confirmation
- typed location detail alongside the legacy string fields
- a small set of radio-style command verbs

## Current Goals

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

## Current Callsign Support

Current default:

- `JARVIS`

The parser stores callsign in the output schema even when older-style phrases are used.

## Current Location IDs

The live voice/display grid now matches the GUI's 8×8 overlay:

- rows: `ALPHA` through `HOTEL`
- columns: `1` through `8`

Canonical location IDs include coarse row references such as:

- `GRID_ALPHA`
- `GRID_BRAVO`
- `GRID_CHARLIE`
- `GRID_DELTA`
- `GRID_ECHO`
- `GRID_FOXTROT`
- `GRID_GOLF`
- `GRID_HOTEL`

and numbered sectors such as:

- `GRID_ALPHA_1`
- `GRID_BRAVO_3`
- `GRID_DELTA_6`
- `GRID_GOLF_7`
- `GRID_HOTEL_8`

The parser also now returns typed detail objects such as:

```json
{
  "type": "named_sector",
  "canonical": "GRID_BRAVO_3",
  "label": "Grid Bravo 3",
  "sector": "BRAVO",
  "subsector": 3
}
```

Recon patrol routes can additionally set:

- `patrol_end_location`
- `patrol_end_location_detail`

## Output Schema

Example staged attack command:

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

## Important Behavior

### 1. Attack commands stage first

`ATTACK_AREA` does not immediately execute in the voice-driven path.

It stages as:

```json
{
  "goal": "ATTACK_AREA",
  "confirmation_required": true,
  "execution_state": "PENDING_EXECUTE"
}
```

Then a follow-up:

```text
JARVIS, execute, over.
```

releases the pending command.

### 2. Disregard cancels a staged command

```text
JARVIS, disregard last, over.
```

maps to:

```json
{
  "goal": "DISREGARD",
  "execution_state": "CANCELED"
}
```

### 3. Legacy string locations are still preserved

To avoid breaking older code paths, both formats are returned:

- `target_location`: legacy canonical string
- `target_location_detail`: typed location object

## Recommended Voice Style

Best current pattern:

```text
[CALLSIGN] [ACTION] [LOCATION] [OVER|OUT]
```

Examples:

1. `JARVIS, move to Grid Alpha, over.`
2. `JARVIS, scan Grid Alpha 2, over.`
3. `JARVIS, attack Grid Bravo, over.`
4. `JARVIS, recon patrol Bravo 1 to Bravo 3, over.`
5. `JARVIS, execute, over.`
6. `JARVIS, all units, abort, out.`

## Expected Mappings

### Move

Input:

```text
JARVIS, move to Grid Alpha, over.
```

Output:

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

### Staged attack

Input:

```text
JARVIS, attack Grid Bravo, over.
```

Output:

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

### Execute

Input:

```text
JARVIS, execute, over.
```

Output:

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

## Current Limitations

- only `JARVIS` is configured as a callsign by default
- phase lines, TRPs, and MGRS are not implemented yet
- patrol routes currently support a start sector plus one end sector
- `LOITER` and `MARK` are parser-level improvements, but they still map onto the existing swarm behaviors underneath
