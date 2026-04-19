# Proposed Changes

This file translates the research brief into concrete repo changes.

Project name: JARVIS (Joint Autonomous Recon and Vision Integrated Swarm)

It is split into:

- `Implemented now`: the highest-value changes already applied for the current demo
- `Good to have later`: features that improve realism further but add more implementation work

The live parser and schema are documented in [COMMAND_SCHEMA.md](COMMAND_SCHEMA.md). The first section below captures the short-list changes that were actually implemented from the research brief, while the second section stays proposal-only.

## Implemented Now

### 1. Add an explicit attack-confirmation flow

Why:

- best realism-per-effort improvement
- aligns with public autonomy guidance
- gives the demo a disciplined command cadence

What changed:

- add a staged state for destructive commands
- treat `ATTACK_AREA` and future `ENGAGE` commands as `pending_execute`
- require a follow-up `EXECUTE` utterance before dispatch
- allow `ABORT` or `DISREGARD` to cancel the pending command

Where:

- [../base_station/core/ai_bridge.py](../base_station/core/ai_bridge.py)
- [../base_station/api/main.py](../base_station/api/main.py)
- command-center UI components that show command state

### 2. Add callsign-first command parsing

Why:

- makes the system sound more like C2 software
- gives the parser a stable first token
- improves judge-facing language immediately

What changed:

- add `callsign` to the schema
- treat `JARVIS` as required at the front for voice commands
- keep the current button PTT flow, but expect `JARVIS` in spoken examples

Target schema addition:

```json
{
  "callsign": "JARVIS"
}
```

### 3. Expand the action vocabulary without breaking the current goals

Why:

- current schema is functional but too small for military-style phrasing
- several high-value radio terms map cleanly to existing behavior

Added now:

- `LOITER`
- `MARK`
- `EXECUTE`
- `STANDBY`
- `DISREGARD`

Keep current:

- `MOVE_TO`
- `ATTACK_AREA`
- `AVOID_AREA`
- `HOLD_POSITION`
- `SCAN_AREA`
- `ABORT`
- `NO_OP`

Mapping guidance:

- `LOITER` can initially map to `HOLD_POSITION`
- `MARK` can initially map to `SCAN_AREA`
- `EXECUTE` should only advance a staged attack command
- `STANDBY` can initially map to `HOLD_POSITION`
- `DISREGARD` cancels a staged command

### 4. Switch locations from plain strings toward typed locations

Why:

- this is the cleanest way to preserve the current system while opening the door to MGRS, TRPs, and phase lines later

Legacy-compatible field still returned:

```json
{
  "target_location": "GRID_BRAVO_2"
}
```

Implemented direction:

```json
{
  "target_location": {
    "type": "named_sector",
    "sector": "BRAVO",
    "subsector": 2
  }
}
```

Implemented compatibility compromise:

- keep existing string fields in API responses for compatibility
- add a parallel typed field such as `target_location_detail`

### 5. Adopt radio-style terminal tokens in examples and prompts

Why:

- improves consistency for STT and demos
- sounds much more natural to judges from a defense background

What changed:

- update prompt text in Ollama parsing to expect commands in the style:
  - `JARVIS, move to Sector Bravo 3, over.`
  - `JARVIS, all units, abort, out.`
- update test docs and judge demo scripts to use `over`, `out`, `execute`, `standby`

### 6. Document defensible network defaults

Why:

- the current code already exposes swarm behavior and parameters
- judges may ask why a given hop count, retry count, or lease exists

Documented baseline:

- fanout: `3`
- max hops: `5`
- retries: `3`
- lease / claim timeout: `10000 ms`

Documented demo mode:

- fanout: `5`
- max hops: `3`
- retries: `2`
- lease / claim timeout: `5000 ms`

## Good To Have Later

### 1. Machine-only MGRS support

What it means:

- operators still speak named sectors and control measures
- the system internally maps those to MGRS or lat/lon

Why it matters:

- much stronger credibility story
- cleaner path to realistic overlays and mission products

Detailed proposed solution:

- add a mission-overlay file that maps each named sector, TRP, or phase line to:
  - canonical display name
  - MGRS centroid
  - optional polygon or polyline
  - optional radius
- keep voice parsing aimed at named sectors
- resolve those names to MGRS only after parsing
- preserve both in payloads:
  - `target_location`: voice-facing canonical label
  - `target_location_detail`: structured object
  - `target_location_mgrs`: machine-facing precise coordinate
- leave operator speech untouched; do not require full spoken MGRS strings

### 2. Phase lines, TRPs, and named areas of interest

Examples:

- `Phase Line Blue`
- `TRP 234`
- `NAI 2`

Why it matters:

- sounds much more doctrinal than generic grid names
- works better in judge briefings and UI overlays

Detailed proposed solution:

- create a mission-control-measures config file with typed records:
  - `named_line`
  - `named_point`
  - `named_area`
- extend parser aliases to accept:
  - `phase line blue`
  - `trp two three four`
  - `nai two`
- resolve those names to typed location objects, not just strings
- render them in the command-center overlay so the operators and judges see the same references the parser uses

### 3. Read-back and confirmation UX

What it means:

- after a critical command, system says:
  - `Hammer flight engage Sector Bravo 3 pending execute, over.`
- operator answers:
  - `JARVIS, execute, over.`

Why it matters:

- adds professional command discipline
- reduces accidental execution

Detailed proposed solution:

- add a command-state model with:
  - `draft`
  - `pending_execute`
  - `executed`
  - `canceled`
- for destructive commands, synthesize a read-back string from the structured command
- show that read-back in three places:
  - UI banner
  - command history
  - optional TTS
- only clear the pending state after:
  - `EXECUTE`
  - `DISREGARD`
  - timeout expiration

### 4. Priority tiers

Suggested tiers:

- `FLASH`
- `IMMEDIATE`
- `ROUTINE`

Why it matters:

- gives you a credible QoS and message-preemption story
- easy to surface in the UI

Detailed proposed solution:

- add a `priority` field to the parser schema
- map priorities to network handling profiles:
  - `FLASH`
  - `IMMEDIATE`
  - `ROUTINE`
- reflect that priority in:
  - swarm dispatch metadata
  - UI badge color
  - command-history display
- reserve preemption for `FLASH` only so normal traffic is not starved

### 5. Link-quality-based adjacency

Why it matters:

- static range is fine for now, but link quality is a more believable DDIL model
- opens the door to graceful degradation demos

Detailed proposed solution:

- keep the current range model as a fallback
- add a `link_quality` score per edge computed from:
  - range utilization
  - packet-loss estimate
  - optional synthetic RSSI
- decide adjacency on a quality threshold instead of a hard range cutoff alone
- expose a UI slider that can artificially degrade the link budget during demos

### 6. Comms-loss failsafe

Recommended behavior:

- on link loss, drone enters `LOITER_AND_STORE`
- on reconnect, resumes or requests operator confirmation

Why it matters:

- strong DDIL story
- good safety and resilience narrative

Detailed proposed solution:

- track last-heard timestamps per node
- if silence exceeds threshold:
  - recon enters `LOITER_AND_STORE`
  - strike elements halt and await revalidation
  - relay nodes keep forwarding if still reachable
- on reconnect:
  - either auto-resume non-destructive tasks
  - or request operator confirmation for destructive tasks
- surface this explicitly in the UI as a degraded-comms state rather than silently failing

### 7. Doctrinal reporting language

Suggested additions:

- `SITREP`
- `SPOTREP`
- `BDA`
- `positive ID`
- `pending execute`

Why it matters:

- makes the system logs and UI sound much more like real C2 tooling

Detailed proposed solution:

- rename or add report types in the API/UI layer:
  - `SITREP`
  - `SPOTREP`
  - `BDA`
  - `positive_id`
  - `pending_execute`
- keep internal variable names simple where needed, but present doctrinal terms in:
  - response messages
  - event logs
  - command-center panels
  - demo scripts

## Recommended Implementation Order

If we are optimizing for strongest near-term demo impact:

1. Attack staging plus `EXECUTE`
2. Callsign-first commands
3. Expanded action vocabulary
4. Typed locations
5. Network default documentation
6. Read-back UX
7. Mission overlays with phase lines and TRPs

## What I Recommend We Actually Build Next

My recommended immediate code path is:

1. Keep the current named-grid system but rename it in docs and code as `named_sector`
2. Add `callsign`, `execute`, and staged attack confirmation
3. Update example phrases and prompt language to radio-style phrasing
4. Add a second-level typed location field without breaking current string compatibility
5. Add a small UI banner for `PENDING EXECUTE`

That gives you the biggest increase in realism without forcing a full parser rewrite all at once.
