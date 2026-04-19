# JARVIS Soldier Controller Demo - Quick Start

## What's New

A complete **puppetable soldier system** that demonstrates realistic military command chains:

```
Soldiers can request actions through operators
Operators approve and relay commands to drones
Recon drones report findings back
Soldiers authorize strikes based on intelligence
```

## Key Command Pipelines

| Pipeline | Description | When Used |
|----------|-------------|-----------|
| **Soldier → Operator → Recon** | Request surveillance through approval chain | Primary intelligence gathering |
| **Soldier → Operator → Attack** | Request strike with operator approval | Standard engagement (needs approval) |
| **Recon → Operator → Attack** | Threat-based strike authorization | React to detected threats with approval |
| **Soldier → Attack (Direct)** | Immediate strike without approval | Emergency response |
| **Soldier → Recon (Direct)** | Immediate reconnaissance request | Urgent intelligence needed |

## Files Created

1. **`core/demo_soldier_controller.py`** (1200+ lines)
   - `SoldierControllerNode` class with command routing
   - All 5 command pipelines implemented
   - Mission tracking and BDA processing
   - Tactical scenario simulation

2. **`SOLDIER_CONTROLLER_GUIDE.md`** (400+ lines)
   - Complete API documentation  
   - Detailed endpoint descriptions
   - Command priority system
   - Full usage examples

3. **`test_soldier_controller.sh`** (executable)
   - Comprehensive test suite
   - All 9 test cases included
   - Colored output for easy reading
   - Full tactical scenario walkthrough

4. **API Endpoints** (in `api/main.py`)
   - 8 new REST endpoints for soldier control
   - Request reconnaissance/attack
   - Approve and relay commands
   - Process reports and BDA
   - Get status and simulate scenarios

## Quick Start

### 1. Ensure API is Running
```bash
cd /home/william/JARVIS/base_station
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Run Full Test Suite
```bash
cd /home/william/JARVIS
bash test_soldier_controller.sh
```

### 3. Manual Test - Simple Flow
```bash
# Request reconnaissance
curl -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Alpha",
    "target_x": 150,
    "target_y": -50,
    "priority": "HIGH"
  }' | jq '.'
```

### 4. Get Soldier Status
```bash
curl http://localhost:8000/api/soldier/soldier-1/status | jq '.'
```

### 5. Simulate Tactical Scenario
```bash
curl -X POST http://localhost:8000/api/soldier/soldier-1/simulate-scenario \
  -H "Content-Type: application/json" \
  -d '{"area": "Grid Alpha"}' | jq '.'
```

## Example Workflow

### Step-by-Step Tactical Engagement

```bash
# 1. Soldier requests recon
RECON=$(curl -s -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area_label": "Grid Alpha",
    "target_x": 150,
    "target_y": -50,
    "priority": "HIGH"
  }')

CMD_ID=$(echo $RECON | jq -r '.command_id')
echo "Recon requested: $CMD_ID"

# 2. Operator approves
APPROVAL=$(curl -s -X POST http://localhost:8000/api/soldier/soldier-1/approve-command/$CMD_ID)
MISSION=$(echo $APPROVAL | jq -r '.mission_id')
echo "Mission approved: $MISSION"

# 3. Recon reports findings
REPORT=$(curl -s -X POST http://localhost:8000/api/soldier/soldier-1/process-recon-report \
  -H "Content-Type: application/json" \
  -d "{
    \"mission_id\": \"$MISSION\",
    \"enemies_detected\": [
      {\"id\": \"enemy-1\", \"type\": \"vehicle\", \"threat_level\": \"high\", \"x\": 200, \"y\": 0},
      {\"id\": \"enemy-2\", \"type\": \"personnel\", \"threat_level\": \"high\", \"x\": 100, \"y\": -50}
    ],
    \"coverage_percent\": 90,
    \"threat_level\": \"high\"
  }")

REPORT_ID=$(echo $REPORT | jq -r '.report_id')
echo "Found $(echo $REPORT | jq -r '.enemies_detected') enemies"

# 4. Authorize strike
STRIKE=$(curl -s -X POST http://localhost:8000/api/soldier/soldier-1/authorize-strike/$REPORT_ID \
  -H "Content-Type: application/json" \
  -d '{"priority": "CRITICAL"}')

STRIKE_MISSION=$(echo $STRIKE | jq -r '.mission_id')
echo "Strike authorized: $STRIKE_MISSION"

# 5. Process BDA
BDA=$(curl -s -X POST http://localhost:8000/api/soldier/soldier-1/process-bda \
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

echo "BDA: $(echo $BDA | jq -r '.damage_assessment | "✓\(.destroyed) destroyed"')"
```

## Command Priority Levels

```
CRITICAL (3) → Immediate threat response
HIGH (2)     → Tactical directive
MEDIUM (1)   → Routine reconnaissance
LOW (0)      → Informational
```

## Available Soldiers

- **soldier-1** (Primary operator)
- **soldier-2** (Secondary operator)

Both are independently puppetable with full command pipeline support.

## Integration Points

✓ **With Swarm Logic**: Commands translate to swarm operations
✓ **With Attack Drones**: Routes commands to attack-1, attack-2
✓ **With Recon Drone**: Routes recon requests to recon-1
✓ **With Command Center**: Can be called from UI (frontend)
✓ **With WebSocket**: Mission updates can stream in real-time

## Architecture

```
Command Center (Puppeteer)
    ↓
Soldier Controller (soldier-1/soldier-2)
    ├─→ Request Recon → Operator → Recon Drone
    ├─→ Request Attack → Operator → Attack Drones
    ├─→ Direct Commands → Drones (bypass operator)
    └─→ Process Reports ← Recon/Operator ← Recon Drone
```

## Testing All Pipelines

Run the comprehensive test suite:

```bash
cd /home/william/JARVIS
./test_soldier_controller.sh
```

This tests:
- ✅ Soldier → Operator → Recon
- ✅ Recon → Operator → Soldier (reports)
- ✅ Recon → Operator → Attack (authorization)
- ✅ Soldier → Attack (direct)
- ✅ Soldier → Recon (direct)
- ✅ Operator approval/relay
- ✅ BDA processing
- ✅ Status retrieval
- ✅ Tactical scenario simulation
- ✅ Multi-soldier operations

## Next Steps

1. **Frontend Integration**: Add UI components to puppet soldiers
2. **WebSocket Updates**: Stream mission status to React UI
3. **Voice Commands**: Integrate with voice pipeline
4. **Drone Behavior**: Add actual drone movement/engagement
5. **Network Simulation**: Add latency/packet loss effects

## Documentation

- **`SOLDIER_CONTROLLER_GUIDE.md`** - Full API documentation
- **`test_soldier_controller.sh`** - Test suite with examples
- **`core/demo_soldier_controller.py`** - Source implementation

