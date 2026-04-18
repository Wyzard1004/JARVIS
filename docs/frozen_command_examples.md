# Frozen Command Examples

This file is a starting point for Richard's `3.x.x` workstream.

Everything in this file is `EXAMPLE ONLY`.
Replace it after the team agrees on the final command contract.

## Where Real Secrets Go

Put your real local values in:

`base_station/.env`

Do not put real secrets in:

- markdown docs
- Python files
- git commits

## EXAMPLE ONLY: Goals

These are example enum values for the parser output:

- `MOVE_TO`
- `ATTACK_AREA`
- `AVOID_AREA`
- `HOLD_POSITION`
- `SCAN_AREA`
- `ABORT`
- `NO_OP`

## EXAMPLE ONLY: Locations

These are example canonical location IDs:

- `GRID_ALPHA`
- `GRID_BRAVO`
- `GRID_CHARLIE`
- `SECTOR_1`
- `SECTOR_2`
- `SECTOR_3`

## EXAMPLE ONLY: Output Schema

```json
{
  "schema_version": "1.0",
  "intent": "swarm_command",
  "goal": "ATTACK_AREA",
  "target_location": "GRID_ALPHA",
  "avoid_location": null,
  "confidence": 0.91
}
```

## EXAMPLE ONLY: Test Phrases

These are sample inputs Richard can use while building `ai_bridge.py`.

1. `"Move to Grid Alpha"`
2. `"Attack Grid Bravo"`
3. `"Avoid Grid Charlie"`
4. `"Hold position"`
5. `"Scan Sector 1"`
6. `"Abort mission"`
7. `"Push the swarm to Grid Alpha"`
8. `"Do not enter Grid Bravo"`
9. `"Attack the area around Sector 2"`
10. `"Stay put until further notice"`

## EXAMPLE ONLY: Expected Mappings

```json
[
  {
    "input": "Move to Grid Alpha",
    "output": {
      "schema_version": "1.0",
      "intent": "swarm_command",
      "goal": "MOVE_TO",
      "target_location": "GRID_ALPHA",
      "avoid_location": null,
      "confidence": 0.95
    }
  },
  {
    "input": "Avoid Grid Charlie",
    "output": {
      "schema_version": "1.0",
      "intent": "swarm_command",
      "goal": "AVOID_AREA",
      "target_location": null,
      "avoid_location": "GRID_CHARLIE",
      "confidence": 0.94
    }
  },
  {
    "input": "Abort mission",
    "output": {
      "schema_version": "1.0",
      "intent": "swarm_command",
      "goal": "ABORT",
      "target_location": null,
      "avoid_location": null,
      "confidence": 0.99
    }
  }
]
```

## What Needs Team Approval

Before Richard locks implementation, the team should approve:

- the exact goal enum
- the exact location IDs
- whether `avoid_location` is required in `v1`
- whether `confidence` is actually needed downstream
- what safe fallback should be used when parsing fails
