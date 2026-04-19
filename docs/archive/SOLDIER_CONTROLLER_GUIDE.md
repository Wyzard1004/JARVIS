# JARVIS Demo Soldier Controller System

## Overview

The demo soldier controller system enables the command center to puppet soldier nodes and execute a sophisticated command routing pipeline. Soldiers can request reconnaissance and attack operations, operators can approve commands, and reconnaissance drones report findings back for decision-making.

## Command Routing Pipeline

### 1. Soldier → Operator → Recon
**Primary reconnaissance request flow**

```
Soldier requests operator authorization to scout an area
  ↓
Operator approves command
  ↓
Command relayed to recon drone
  ↓
Recon drone scans area and detects enemies
  ↓
Findings reported back: Recon → Operator → Soldier
```

**Endpoint:**
```bash
POST /api/soldier/{soldier_id}/request-recon
{
  "area_label": "Grid Alpha",
  "target_x": 150,
  "target_y": -50,
  "priority": "HIGH"
}
```

---

### 2. Soldier → Operator → Attack
**Approval-required strike authorization**

```
Soldier requests operator authorization for strike
  ↓
Operator approves command
  ↓
Command relayed to attack drones
  ↓
Drones engage targets at location
```

**Endpoint:**
```bash
POST /api/soldier/{soldier_id}/request-attack
{
  "area_label": "Grid Alpha",
  "target_x": 150,
  "target_y": -50,
  "requires_approval": true,
  "priority": "HIGH"
}
```

---

### 3. Recon → Operator → Attack
**Threat-based strike authorization**

```
Recon drone detects enemies and reports findings
  ↓
Report flows: Recon → Operator → Soldier
  ↓
Soldier reviews threat assessment
  ↓
Soldier authorizes strike based on threat level
  ↓
Command relayed: Operator → Attack drones
  ↓
Drones engage identified enemies
```

**Flow:**
1. Recon report received: `POST /api/soldier/{soldier_id}/process-recon-report`
2. Strike authorized: `POST /api/soldier/{soldier_id}/authorize-strike/{recon_report_id}`

---

### 4. Soldier → Attack (Direct)
**Immediate strike without approval chain**

```
Soldier issues direct attack command
  ↓
No approval required
  ↓
Command immediately relayed to attack drones
  ↓
Drones engage targets
```

**Endpoint:**
```bash
POST /api/soldier/{soldier_id}/request-attack
{
  "area_label": "Grid Alpha",
  "target_x": 150,
  "target_y": -50,
  "requires_approval": false,
  "priority": "CRITICAL"
}
```

---

### 5. Soldier → Recon (Direct)
**Immediate reconnaissance without approval**

```
Soldier issues direct recon command
  ↓
No approval required
  ↓
Command immediately relayed to recon drone
  ↓
Drone scans area
  ↓
Findings reported back to soldier
```

**Endpoint:**
```bash
POST /api/soldier/{soldier_id}/request-recon
{
  "area_label": "Grid Charlie",
  "target_x": 30,
  "target_y": 120,
  "priority": "MEDIUM"
}
```

---

## Complete Tactical Scenario Example

The system can simulate a full tactical scenario:

### Stage 1: Recon Request
Soldier requests operator authorization to scout Grid Alpha
```
Command Route: Soldier → Operator → Recon
Status: Pending Operator Approval
```

### Stage 2: Operator Approval
Operator reviews request and approves
```
Status: Authorized
Mission ID: mission-xxxxx
```

### Stage 3: Recon Findings
Recon drone scans area and detects 2-4 enemies
```
Enemies Detected: 3
Coverage: 85%
Threat Level: HIGH
Route: Recon → Operator → Soldier
```

### Stage 4: Strike Authorization
Based on threat assessment, soldier authorizes strike
```
Command Route: Recon → Operator → Attack
Enemies to Engage: 3
Priority: CRITICAL
Status: Authorized
```

### Stage 5: Battle Damage Assessment (BDA)
Recon drone confirms target destruction
```
Targets Engaged: 3
Destroyed: 2-3
Damaged: 0-1
Status: Complete
```

---

## API Endpoints

### Request Commands

#### Request Reconnaissance
```bash
POST /api/soldier/{soldier_id}/request-recon

Body:
{
  "area_label": "Grid Alpha",
  "target_x": 150,
  "target_y": -50,
  "priority": "HIGH"  # HIGH, MEDIUM, LOW
}

Response:
{
  "command_id": "soldier-1-recon-0",
  "route": "soldier→operator→recon",
  "status": "pending_operator_approval",
  "area_label": "Grid Alpha"
}
```

#### Request Attack
```bash
POST /api/soldier/{soldier_id}/request-attack

Body:
{
  "area_label": "Grid Alpha",
  "target_x": 150,
  "target_y": -50,
  "requires_approval": true,  # true for approval chain, false for direct
  "priority": "HIGH"          # HIGH, MEDIUM, LOW, CRITICAL
}

Response:
{
  "command_id": "soldier-1-attack-1",
  "route": "soldier→operator→attack",
  "status": "pending_operator_approval",
  "requires_approval": true
}
```

### Approval & Relay

#### Approve Command
```bash
POST /api/soldier/{soldier_id}/approve-command/{command_id}

Response:
{
  "approved": true,
  "command_id": "soldier-1-recon-0",
  "mission_id": "mission-xxxxx",
  "route": "soldier→operator→recon"
}
```

### Report Processing

#### Process Recon Report
```bash
POST /api/soldier/{soldier_id}/process-recon-report

Body:
{
  "mission_id": "mission-xxxxx",
  "enemies_detected": [
    {"id": "enemy-1", "type": "vehicle", "threat_level": "high", "x": 100, "y": 50},
    {"id": "enemy-2", "type": "personnel", "threat_level": "high", "x": 120, "y": 60}
  ],
  "coverage_percent": 85,
  "threat_level": "high"
}

Response:
{
  "report_id": "recon-report-0",
  "enemies_detected": 2,
  "threat_level": "high",
  "status": "awaiting_authorization"
}
```

#### Authorize Strike from Recon
```bash
POST /api/soldier/{soldier_id}/authorize-strike/{recon_report_id}

Body:
{
  "priority": "CRITICAL"
}

Response:
{
  "command_id": "soldier-1-authorized-strike-xxx",
  "route": "recon→operator→attack",
  "mission_id": "mission-xxxxx",
  "status": "authorized",
  "enemies_to_engage": 2
}
```

#### Process BDA
```bash
POST /api/soldier/{soldier_id}/process-bda

Body:
{
  "mission_id": "mission-xxxxx",
  "damage_assessment": {
    "targets_engaged": 2,
    "destroyed": 2,
    "damaged": 0,
    "escaped": 0
  }
}

Response:
{
  "bda_id": "bda-0",
  "mission_id": "mission-xxxxx",
  "damage_assessment": {...},
  "status": "complete"
}
```

### Status & Simulation

#### Get Soldier Status
```bash
GET /api/soldier/{soldier_id}/status

Response:
{
  "soldier_id": "soldier-1",
  "status": "ready",
  "total_commands": 5,
  "active_missions": 2,
  "recon_reports": 3,
  "authorized_targets": 1,
  "commands": [...],
  "recent_recon_reports": [...]
}
```

#### Simulate Tactical Scenario
```bash
POST /api/soldier/{soldier_id}/simulate-scenario

Body:
{
  "area": "Grid Alpha"
}

Response:
{
  "scenario_id": "scenario-0",
  "area": "Grid Alpha",
  "stages": [
    {
      "stage": "recon_request",
      "command_id": "soldier-1-recon-0",
      "description": "Soldier requests reconnaissance via operator"
    },
    {
      "stage": "operator_approval",
      "mission_id": "mission-xxxxx"
    },
    {
      "stage": "recon_findings",
      "report_id": "recon-report-0",
      "enemies_count": 3
    },
    {
      "stage": "strike_authorization",
      "command_id": "soldier-1-authorized-strike-xxx",
      "drones": ["attack-1", "attack-2"]
    },
    {
      "stage": "bda_report",
      "bda_id": "bda-0",
      "damage": {"targets_engaged": 3, "destroyed": 2, ...}
    }
  ],
  "status": "complete"
}
```

---

## Usage Example: Complete Scenario

```bash
# 1. Soldier requests reconnaissance of Grid Alpha
RECON_RESP=$(curl -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Alpha",
    "target_x": 150,
    "target_y": -50,
    "priority": "HIGH"
  }')

COMMAND_ID=$(echo $RECON_RESP | jq -r '.command_id')
echo "Recon command created: $COMMAND_ID"

# 2. Operator approves the recon request
APPROVAL=$(curl -X POST http://localhost:8000/api/soldier/soldier-1/approve-command/$COMMAND_ID)
MISSION_ID=$(echo $APPROVAL | jq -r '.mission_id')
echo "Command approved. Mission: $MISSION_ID"

# 3. Recon drone reports findings
RECON_REPORT=$(curl -X POST http://localhost:8000/api/soldier/soldier-1/process-recon-report \
  -H "Content-Type: application/json" \
  -d "{
    \"mission_id\": \"$MISSION_ID\",
    \"enemies_detected\": [
      {\"id\": \"enemy-1\", \"type\": \"vehicle\", \"threat_level\": \"high\", \"x\": 200, \"y\": 0},
      {\"id\": \"enemy-2\", \"type\": \"personnel\", \"threat_level\": \"high\", \"x\": 100, \"y\": -50}
    ],
    \"coverage_percent\": 90,
    \"threat_level\": \"high\"
  }")

REPORT_ID=$(echo $RECON_REPORT | jq -r '.report_id')
echo "Recon findings received: $REPORT_ID (2 enemies detected)"

# 4. Soldier authorizes strike based on recon findings
STRIKE=$(curl -X POST http://localhost:8000/api/soldier/soldier-1/authorize-strike/$REPORT_ID \
  -H "Content-Type: application/json" \
  -d '{"priority": "CRITICAL"}')

STRIKE_MISSION=$(echo $STRIKE | jq -r '.mission_id')
echo "Strike authorized: $STRIKE_MISSION"

# 5. Process BDA from recon drone
BDA=$(curl -X POST http://localhost:8000/api/soldier/soldier-1/process-bda \
  -H "Content-Type: application/json" \
  -d "{
    \"mission_id\": \"$STRIKE_MISSION\",
    \"damage_assessment\": {
      \"targets_engaged\": 2,
      \"destroyed\": 2,
      \"damaged\": 0,
      \"escaped\": 0
    }
  }")

echo "BDA processed: $(echo $BDA | jq '.damage_assessment')"

# 6. Get complete soldier status
curl http://localhost:8000/api/soldier/soldier-1/status | jq '.'
```

---

## Command Priority Levels

- **CRITICAL** (3): Immediate threat response, highest priority
- **HIGH** (2): Tactical directive from soldier
- **MEDIUM** (1): Routine reconnaissance
- **LOW** (0): Informational

---

## Key Features

✅ **Puppetable Soldiers**: Command center can issue commands on behalf of soldiers
✅ **Multi-Hop Command Chain**: Commands route through operators to reach drones
✅ **Flexible Authorization**: Commands can require approval or bypass approval chain
✅ **Report Feedback**: Recon reports flow back through operator to soldier
✅ **BDA Tracking**: Battle damage assessments confirm strike effectiveness
✅ **Mission Tracking**: Each mission has unique ID for status queries
✅ **Tactical Scenarios**: Pre-built scenario simulation for testing
✅ **Audit Trail**: Complete command log for every soldier

---

## Integration Points

- **Swarm Logic**: Commands are translated to swarm operations
- **Attack Drones**: Routes commands to attack-1 and attack-2
- **Recon Drone**: Routes reconnaissance and BDA requests to recon-1
- **Operator Nodes**: Soldiers act as approval/relay nodes
- **WebSocket Broadcasting**: Mission updates streamed to UI

