# JARVIS New Architecture - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ with FastAPI, Uvicorn installed
- Node.js with npm/yarn for React frontend
- Ollama service running (optional, for voice commands)

---

## 📋 Startup Instructions

### 1. Backend Service

```bash
# Terminal 1: Start the FastAPI backend
cd /home/william/JARVIS/base_station
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
[STARTUP] JARVIS Base Station initializing...
 * Running on http://0.0.0.0:8000
 * SwarmCoordinator initialized
 * 15 drone nodes ready (2 soldiers, 2 compute, 5 recon, 6 attack)
 * 104 network edges configured
```

### 2. Frontend Service

```bash
# Terminal 2: Start the React development server
cd /home/william/JARVIS/command_center
npm install  # (if needed)
npm run dev
```

Access the frontend at: **http://localhost:5173**

---

## 🎮 Using the System

### 1. Soldier Selection

At the top of the right control panel, you'll see two buttons:
- **Soldier 1** (orange) - Left command operator
- **Soldier 2** (orange) - Right command operator

Click to switch which soldier you're controlling.

### 2. Visualization

The main canvas shows:
- **Orange circles (S)**: Soldiers (fixed at top)
- **Cyan circles (C)**: Compute drones (processing)
- **Cyan circles (R)**: Recon drones (sensors, scattered)
- **Red circles (A)**: Attack drones (weapons, scattered)

Lines show communication links between drones.

### 3. Voice Commands

Click the **Push to Talk** button and say commands like:
- "Send recon to Grid Alpha"
- "Engage target at Bravo"
- "Scan the area for threats"

The system will:
1. Transcribe your voice
2. Parse the intent
3. Route through soldier → compute (if image processing needed) → attack drones

### 4. API Endpoints

#### Compute Drone Operations

**Receive Image from Recon**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/receive-image \
  -H "Content-Type: application/json" \
  -d '{
    "image_report_id": "IMG-001",
    "recon_drone_id": "recon-1",
    "location_grid": "Grid Alpha 1",
    "image_data": {"quality": 0.95, "resolution": "1080p"}
  }'
```

**Process Queued Image**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/process-image \
  -H "Content-Type: application/json" \
  -d '{
    "image_reception_id": "compute-1-rx-IMG-001"
  }'
```

**Make Strike Decision**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/make-strike-decision \
  -H "Content-Type: application/json" \
  -d '{
    "target_key": "Grid Alpha 1-TGT-001",
    "soldier_approval": false,
    "soldier_priority_override": null
  }'
```

**Get Compute Drone Status**
```bash
curl http://localhost:8000/api/compute/compute-1/status
```

**Get Tracked Targets**
```bash
curl "http://localhost:8000/api/compute/compute-1/targets?threat_filter=high"
```

#### Soldier Controller Operations (Existing)

**Request Reconnaissance**
```bash
curl -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -H "Content-Type: application/json" \
  -d '{
    "area": "Grid Alpha",
    "priority": 2,
    "dwell_time_seconds": 150
  }'
```

**Request Attack**
```bash
curl -X POST http://localhost:8000/api/soldier/soldier-1/request-attack \
  -H "Content-Type: application/json" \
  -d '{
    "target_location": "Grid Alpha 1",
    "priority": 3,
    "expected_contacts": 15
  }'
```

**Get Soldier Status**
```bash
curl http://localhost:8000/api/soldier/soldier-1/status
```

---

## 🔍 Understanding the Architecture

### Command Flow: Full Pipeline

```
1. VOICE INPUT → Soldier 1
   "Send recon to Grid Alpha"

2. SOLDIER DECISION → Request Reconnaissance
   Creates recon mission, assigns recon-1 through recon-5

3. RECON SCANNING → Drones scan area
   Collect sensor data, detect targets

4. IMAGE TRANSMISSION → Send to Compute Drones
   Recon-1 → Compute-1/2
   Image reception queued at compute processors

5. IMAGE PROCESSING → Compute Drone Analysis
   - Detect targets (armor, personnel, etc.)
   - Classify threat levels (CRITICAL, HIGH, MEDIUM, LOW)
   - Generate confidence scores

6. STRIKE DECISION → Compute Processor
   - CRITICAL threat + HIGH confidence → AUTO-AUTHORIZE
   - Uncertain threats → HOLD for soldier review
   - Low threats → DENIED

7. SOLDIER APPROVAL → Check uncertain targets
   Soldier-1 reviews held targets, can override decisions

8. TARGETING RELAY → Send to Attack Drones
   Compute-1/2 → Attack-1 through Attack-6
   Each attack drone receives targeting package

9. STRIKE EXECUTION → Attack drones engage
   Execute strike with coordination across attack formation

10. BATTLE DAMAGE REPORT → Soldier reviews results
    Post-action analysis and status update
```

### Network Structure

**15 Total Nodes:**
- Soldiers (2): Command authority
- Compute (2): Image processors & decision making
- Recon (5): Sensor platforms
- Attack (6): Strike platforms

**104 Network Edges:**
- Soldier ↔ Compute: Command/report (high priority)
- Compute → Recon: Broadcast tasking
- Recon → Compute: Image sensor data
- Soldier → Recon: Tactical override
- Compute → Attack: Authorized strikes
- Soldier → Attack: Emergency override
- Recon ↔ Attack: Mesh relay coordination
- Attack ↔ Attack: Formation mesh

---

## 🧪 Testing the System

### Test 1: Check Initialization

```bash
python3 << 'EOF'
from core.swarm_logic import get_swarm
swarm = get_swarm()
state = swarm.get_state()
print(f"Nodes: {len(state['nodes'])}")
print(f"Edges: {len(state['edges'])}")
print("✅ System ready!")
EOF
```

### Test 2: Image Processing Pipeline

```bash
python3 << 'EOF'
from core.compute_drone_controller import ComputeDroneController
compute = ComputeDroneController("compute-1", 0.95)

# Receive image
reception = compute.receive_recon_image(
    image_report_id="IMG-001",
    recon_drone_id="recon-1",
    image_data={"quality": 0.95},
    location_grid="Grid Alpha 1"
)

# Process image
result = compute.process_image(reception['reception_id'])
print(f"Detected {len(result['detected_targets'])} targets")

# Make decision
for target in result['detected_targets']:
    key = f"{result['location_grid']}-{target['target_id']}"
    decision = compute.make_strike_decision(key)
    print(f"{target['target_id']}: {decision['decision']}")
EOF
```

### Test 3: Soldier Controller

```bash
python3 << 'EOF'
from core.demo_soldier_controller import SoldierControllerNode
soldier = SoldierControllerNode("soldier-1")

# Request recon
recon = soldier.request_reconnaissance("Grid Alpha", 150)
print(f"Recon mission: {recon['mission_id']}")

# Approve command
approval = soldier.approve_and_relay_command(recon['command_id'])
print(f"Approved: {approval['approval_status']}")

# Simulate recon report
report = soldier.process_recon_report(
    recon['mission_id'],
    enemies=[{"id": "TGT-001", "type": "armor"}],
    confidence=0.95
)
print(f"Report: {len(report.get('detected_targets', []))} targets found")
EOF
```

---

## 📊 Key Metrics & Status

### Real-Time Status from API

```bash
# Check overall swarm state
curl http://localhost:8000/api/swarm/state | jq '.nodes | length'

# Monitor compute drone queue
curl http://localhost:8000/api/compute/compute-1/status | jq '.images_queued'

# List high-threat targets
curl "http://localhost:8000/api/compute/compute-1/targets?threat_filter=high" | jq '.targets'

# Soldier command status
curl http://localhost:8000/api/soldier/soldier-1/status | jq '.pending_commands'
```

### Expected Performance

| Component | Metric | Value |
|-----------|--------|-------|
| Compute Drone 1 | Processor Capability | 95% |
| Compute Drone 2 | Processor Capability | 93% |
| Soldier-Compute Link | Latency | 22-38ms |
| Recon-Compute Link | Latency | 45-90ms |
| Compute-Attack Link | Latency | 52-92ms |
| Network Density | Edges | 104 |
| Simulation Canvas | Size | 1000×600 px |

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python3 --version  # Must be 3.10+

# Check dependencies
python3 -m pip install fastapi uvicorn pydantic networkx

# Check port conflict
netstat -tln | grep 8000  # Kill other process if needed
```

### Frontend Build Issues
```bash
# Clear node_modules and reinstall
cd command_center
rm -rf node_modules pnpm-lock.yaml
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

### WebSocket Connection Failed
```bash
# Ensure backend is running
curl http://localhost:8000/

# Check firewall (for SSH port forwarding)
ssh -L 8000:localhost:8000 user@server

# Monitor backend logs for errors
tail -f /path/to/backend.log
```

### Image Processing Not Working
```bash
# Check compute drone is initialized
curl http://localhost:8000/api/compute/compute-1/status

# Verify image was queued
# (should show non-zero in images_processed after processing)
```

---

## 🎯 Common Commands

### Switch Active Soldier
```javascript
// In browser console
// Click "Soldier 2" button in UI
// Or programmatically:
fetch(`/api/soldier/soldier-2/status`)
  .then(r => r.json())
  .then(data => console.log(data))
```

### Send Reconnaissance
```bash
curl -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -H "Content-Type: application/json" \
  -d '{"area": "Grid Alpha", "priority": 3}'
```

### Process Detected Targets
```bash
# 1. Receive image from recon
curl -X POST http://localhost:8000/api/compute/compute-1/receive-image \
  -d '{"image_report_id":"IMG-1","recon_drone_id":"recon-1","location_grid":"Grid Alpha 1","image_data":{}}'

# 2. Process the image
curl -X POST http://localhost:8000/api/compute/compute-1/process-image \
  -d '{"image_reception_id":"compute-1-rx-IMG-1"}'

# 3. Check targets detected
curl http://localhost:8000/api/compute/compute-1/targets
```

---

## 📖 Additional Resources

- **Architecture Overview**: [ARCHITECTURE_REBRAND_SUMMARY.md](./ARCHITECTURE_REBRAND_SUMMARY.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Soldier Controller Guide**: [SOLDIER_CONTROLLER_GUIDE.md](./SOLDIER_CONTROLLER_GUIDE.md)

---

## ✅ Verification Checklist

- [ ] Backend running on localhost:8000
- [ ] Frontend running on localhost:5173
- [ ] Soldier selector visible in right panel
- [ ] Swarm graph showing 15 nodes
- [ ] Compute drones visible as cyan "C" icons
- [ ] Attack drones scattered across canvas
- [ ] Recon drones scattered across canvas
- [ ] Can switch between soldiers
- [ ] API endpoints responding (`/api/compute/compute-1/status`)

---

## 🎉 You're Ready!

The JARVIS system is now running with:
- ✅ 15-node expanded drone fleet
- ✅ Intelligent compute processors
- ✅ Comprehensive image processing pipeline
- ✅ Soldier command interface with selection menu
- ✅ Full ISR-to-strike workflow

Begin operations now! 🚀
