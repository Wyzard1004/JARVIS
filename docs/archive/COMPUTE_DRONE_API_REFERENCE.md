# Compute Drone API Reference

Complete API documentation for the image processing pipeline and compute drone operations.

---

## Overview

The compute drone endpoints handle the image processing pipeline:

```
Recon Image → Receive → Process → Analyze → Decide → Relay → Attack
```

All requests use JSON with REST conventions.

---

## Endpoints

### 1. Receive Image from Recon Drone

**Endpoint:** `POST /api/compute/{compute_id}/receive-image`

**Purpose:** Queue an image from a recon drone for processing.

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID (e.g., "compute-1")

**Request Body:**
```json
{
  "image_report_id": "string (required)",
  "recon_drone_id": "string (required)",
  "location_grid": "string (required)",
  "image_data": {
    "quality": "float (0.0-1.0, optional)",
    "resolution": "string (optional)"
  }
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/receive-image \
  -H "Content-Type: application/json" \
  -d '{
    "image_report_id": "IMG-001",
    "recon_drone_id": "recon-1",
    "location_grid": "Grid Alpha 1",
    "image_data": {
      "quality": 0.95,
      "resolution": "1080p"
    }
  }'
```

**Response (200 OK):**
```json
{
  "status": "received",
  "reception_id": "compute-1-rx-IMG-001",
  "queue_position": 1,
  "compute_processor": "compute-1"
}
```

**Error Responses:**
- `404 Not Found`: Compute drone not found
- `400 Bad Request`: Missing required fields

---

### 2. Process Queued Image

**Endpoint:** `POST /api/compute/{compute_id}/process-image`

**Purpose:** Process a queued image - detect targets, classify threats, assess priority.

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID

**Request Body:**
```json
{
  "image_reception_id": "string (required)"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/process-image \
  -H "Content-Type: application/json" \
  -d '{
    "image_reception_id": "compute-1-rx-IMG-001"
  }'
```

**Response (200 OK):**
```json
{
  "processing_id": "compute-1-proc-IMG-001",
  "location_grid": "Grid Alpha 1",
  "detected_targets": [
    {
      "target_id": "TGT-Grid Alpha 1-1",
      "type": "armor",
      "threat_level": 4,
      "confidence": 0.77,
      "position": {
        "grid": "Grid Alpha 1",
        "estimated_coords": [42, 87]
      },
      "size_estimate": "convoy",
      "movement": "moderate",
      "personnel_estimate": null
    },
    {
      "target_id": "TGT-Grid Alpha 1-2",
      "type": "personnel",
      "threat_level": 2,
      "confidence": 0.79,
      "position": {
        "grid": "Grid Alpha 1",
        "estimated_coords": [55, 91]
      },
      "size_estimate": "small-group",
      "movement": "stationary",
      "personnel_estimate": 25
    }
  ],
  "targets_count": 2,
  "processor_confidence": 0.95,
  "status": "processed"
}
```

**Threat Levels:**
- `5`: CRITICAL (Command posts, anti-air)
- `4`: HIGH (Armor, vehicles)
- `3`: MEDIUM (Logistics, infrastructure)
- `2`: LOW (Personnel)
- `1`: UNKNOWN

**Target Types:**
- `armor`: Vehicles and armored platforms
- `command-post`: Headquarters or command locations
- `anti-air`: Air defense systems
- `personnel`: Individual combatants or groups
- `logistics`: Supply and support elements
- `infrastructure`: Buildings, bridges, etc.
- `unknown`: Unclassified

---

### 3. Make Strike Decision

**Endpoint:** `POST /api/compute/{compute_id}/make-strike-decision`

**Purpose:** Analyze a target and decide whether to authorize strike with intelligent logic.

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID

**Request Body:**
```json
{
  "target_key": "string (required)",
  "soldier_approval": "boolean (optional, default: false)",
  "soldier_priority_override": "integer or null (optional)"
}
```

**Example Request - Autonomous Decision:**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/make-strike-decision \
  -H "Content-Type: application/json" \
  -d '{
    "target_key": "Grid Alpha 1-TGT-Grid Alpha 1-1",
    "soldier_approval": false,
    "soldier_priority_override": null
  }'
```

**Example Request - Soldier Override:**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/make-strike-decision \
  -H "Content-Type: application/json" \
  -d '{
    "target_key": "Grid Alpha 1-TGT-Grid Alpha 1-2",
    "soldier_approval": true,
    "soldier_priority_override": 2
  }'
```

**Response (200 OK):**
```json
{
  "decision_id": "compute-1-dec-TGT-Grid Alpha 1-1",
  "target_id": "TGT-Grid Alpha 1-1",
  "decision": "hold",
  "reasoning": "High threat but confidence insufficient (77%)",
  "soldier_approved": false,
  "status": "pending-relay"
}
```

**Decision Values:**
- `authorize`: Strike is authorized
- `hold`: Hold fire, requires soldier confirmation
- `denied`: Strike is denied
- `needs-clarification`: Requires soldier decision

**Decision Logic:**
```
IF soldier override + soldier approval → AUTHORIZE
ELSE IF threat is CRITICAL and confidence ≥ 85% → AUTHORIZE
ELSE IF threat is CRITICAL and confidence < 85% → NEEDS CLARIFICATION
ELSE IF threat is HIGH and confidence ≥ 90% → AUTHORIZE
ELSE IF threat is HIGH and confidence < 90% → HOLD
ELSE IF threat is MEDIUM and soldier approved → AUTHORIZE
ELSE IF threat is MEDIUM and not approved → NEEDS CLARIFICATION
ELSE → DENIED
```

---

### 4. Relay Targeting to Attack Drones

**Endpoint:** `POST /api/compute/{compute_id}/relay-targeting`

**Purpose:** Send authorized strike targeting to assigned attack drones.

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID

**Request Body:**
```json
{
  "decision_id": "string (required)",
  "assigned_attack_drones": ["string", "string", ...]
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/compute/compute-1/relay-targeting \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "compute-1-dec-TGT-Grid Alpha 1-1",
    "assigned_attack_drones": ["attack-1", "attack-2", "attack-3"]
  }'
```

**Response (200 OK):**
```json
{
  "relay_id": "compute-1-relay-compute-1-dec-TGT-Grid Alpha 1-1",
  "target_id": "TGT-Grid Alpha 1-1",
  "assigned_attack_drones": ["attack-1", "attack-2", "attack-3"],
  "status": "transmitted"
}
```

**Error Responses:**
- `404 Not Found`: Decision not found
- `400 Bad Request`: Decision not authorized (must be "authorize" status)

---

### 5. Get Compute Drone Status

**Endpoint:** `GET /api/compute/{compute_id}/status`

**Purpose:** Retrieve status and metrics for a compute drone.

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID

**Example Request:**
```bash
curl http://localhost:8000/api/compute/compute-1/status
```

**Response (200 OK):**
```json
{
  "compute_drone_id": "compute-1",
  "status": "online",
  "processor_capability": 0.95,
  "images_queued": 0,
  "images_processed": 1,
  "targets_in_database": 3,
  "pending_strike_decisions": 3,
  "targets_high_threat": 1,
  "report_time": "2024-04-18T15:30:45.123456"
}
```

---

### 6. Get Tracked Targets

**Endpoint:** `GET /api/compute/{compute_id}/targets`

**Purpose:** Retrieve all targets tracked by a compute drone (optionally filtered by threat level).

**Path Parameters:**
- `compute_id` (string, required): Compute drone ID

**Query Parameters:**
- `threat_filter` (string, optional): Filter by threat level
  - `critical`: Threat level ≥ 5
  - `high`: Threat level ≥ 4
  - `medium`: Threat level ≥ 3
  - `low`: Threat level ≥ 2
  - `unknown`: Unclassified targets

**Example Requests:**
```bash
# Get all targets
curl http://localhost:8000/api/compute/compute-1/targets

# Get only high-threat targets
curl "http://localhost:8000/api/compute/compute-1/targets?threat_filter=high"

# Get critical threats only
curl "http://localhost:8000/api/compute/compute-1/targets?threat_filter=critical"
```

**Response (200 OK):**
```json
{
  "compute_drone_id": "compute-1",
  "targets_count": 3,
  "threat_filter": null,
  "targets": [
    {
      "target_id": "TGT-Grid Alpha 1-1",
      "type": "armor",
      "threat_level": 4,
      "confidence": 0.77,
      "position": {
        "grid": "Grid Alpha 1",
        "estimated_coords": [42, 87]
      },
      "size_estimate": "convoy",
      "movement": "moderate",
      "personnel_estimate": null,
      "first_detected": "2024-04-18T15:30:12.345678",
      "processing_id": "compute-1-proc-IMG-001"
    },
    {
      "target_id": "TGT-Grid Alpha 1-2",
      "type": "personnel",
      "threat_level": 2,
      "confidence": 0.79,
      "position": {
        "grid": "Grid Alpha 1",
        "estimated_coords": [55, 91]
      },
      "size_estimate": "small-group",
      "movement": "stationary",
      "personnel_estimate": 25,
      "first_detected": "2024-04-18T15:30:12.345678",
      "processing_id": "compute-1-proc-IMG-001"
    },
    {
      "target_id": "TGT-Grid Alpha 1-3",
      "type": "logistics",
      "threat_level": 3,
      "confidence": 0.9,
      "position": {
        "grid": "Grid Alpha 1",
        "estimated_coords": [68, 73]
      },
      "size_estimate": "formation",
      "movement": "slow",
      "personnel_estimate": null,
      "first_detected": "2024-04-18T15:30:12.345678",
      "processing_id": "compute-1-proc-IMG-001"
    }
  ]
}
```

**Targets sorted by threat level (highest first).**

---

## Complete Workflow Example

### Scenario: Recon detects armor convoy

```
1. RECEIVE IMAGE
   Request: POST /api/compute/compute-1/receive-image
   ├─ recon-1 sends image from Grid Alpha 1
   └─ Status: Reception ID = compute-1-rx-IMG-001

2. PROCESS IMAGE
   Request: POST /api/compute/compute-1/process-image
   ├─ Image processed by compute-1 (95% capability)
   ├─ Detects 3 targets:
   │  ├─ TGT-1: Armor convoy (threat=4, conf=77%)
   │  ├─ TGT-2: Infantry group (threat=2, conf=79%)
   │  └─ TGT-3: Supply depot (threat=3, conf=90%)
   └─ Status: Processing ID = compute-1-proc-IMG-001

3. MAKE DECISION (Armor Convoy)
   Request: POST /api/compute/compute-1/make-strike-decision
   ├─ Threat: HIGH (4)
   ├─ Confidence: 77% (insufficient for auto-auth)
   ├─ Decision: HOLD
   └─ Reasoning: "High threat but confidence insufficient (77%)"
   Status: PENDING-RELAY (waiting for soldier confirmation)

4. SOLDIER APPROVAL
   Request: POST /api/compute/compute-1/make-strike-decision
   ├─ soldier_approval: true
   ├─ soldier_priority_override: 2 (urgent)
   ├─ Decision: AUTHORIZE (override applied)
   └─ Status: PENDING-RELAY

5. RELAY TARGETING
   Request: POST /api/compute/compute-1/relay-targeting
   ├─ Target: TGT-Grid Alpha 1-1 (armor)
   ├─ Assigned: ["attack-1", "attack-2", "attack-3"]
   ├─ Relay ID: compute-1-relay-...
   └─ Status: TRANSMITTED (attack drones got targeting)

6. VERIFY STATUS
   Request: GET /api/compute/compute-1/status
   ├─ Images processed: 1
   ├─ Targets in database: 3
   ├─ Pending decisions: 2 (others still on HOLD)
   └─ Status: online

7. CHECK TARGETS
   Request: GET /api/compute/compute-1/targets?threat_filter=high
   ├─ Returns: Armor convoy (high threat)
   └─ Shows: Already relayed to attack drones
```

---

## Error Handling

### Common Errors

**404 - Compute Drone Not Found**
```json
{
  "detail": "Compute drone compute-99 not found"
}
```

**400 - Bad Request**
```json
{
  "detail": "Invalid threat level: super-critical"
}
```

**400 - Decision Not Authorized**
```json
{
  "detail": "Cannot relay non-authorized decisions: hold"
}
```

**400 - Image Not Found**
```json
{
  "detail": "Image not found in processing queue"
}
```

---

## Integration with Soldier Controller

The compute drone works alongside the soldier controller:

**Soldier Controls Path:**
```
Soldier Request → Compute Drone → Attack Drones
```

**Example: Soldier requests attack**

```bash
# 1. Soldier requests reconnaissance
curl -X POST http://localhost:8000/api/soldier/soldier-1/request-recon \
  -d '{"area": "Grid Alpha", "priority": 3}'

# 2. Recon drones transmit images to compute drones
# (Handled by system internals)

# 3. Compute drone processes images
curl -X POST http://localhost:8000/api/compute/compute-1/process-image \
  -d '{"image_reception_id": "compute-1-rx-IMG-001"}'

# 4. Get targets for soldier review
curl http://localhost:8000/api/compute/compute-1/targets?threat_filter=high

# 5. Soldier approves strike on specific target
curl -X POST http://localhost:8000/api/compute/compute-1/make-strike-decision \
  -d '{
    "target_key": "Grid Alpha 1-TGT-001",
    "soldier_approval": true,
    "soldier_priority_override": 3
  }'

# 6. Relay to attack drones
curl -X POST http://localhost:8000/api/compute/compute-1/relay-targeting \
  -d '{
    "decision_id": "compute-1-dec-TGT-Grid Alpha 1-1",
    "assigned_attack_drones": ["attack-1", "attack-2", "attack-3"]
  }'
```

---

## Rate Limits & Performance

No rate limits enforced. Expected performance:

- **Image Reception**: <1ms
- **Image Processing**: 10-50ms (depends on detection algorithm)
- **Decision Making**: <5ms
- **Targeting Relay**: <2ms
- **Status Query**: <1ms

Database maintained in memory; no persistence layer currently.

---

## WebSocket Integration

The compute drone status is published via WebSocket:

```javascript
// Browser console
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'compute_drone_update') {
    console.log(`Compute drone ${data.drone_id} status:`, data);
  }
}
```

---

## Security Notes

Current implementation is for demonstration. Production would include:
- Authentication/authorization
- Rate limiting
- Input validation
- Audit logging
- Network encryption

---

## Glossary

| Term | Definition |
|------|-----------|
| Reception ID | Unique identifier for incoming image |
| Processing ID | Unique identifier for processed image |
| Decision ID | Unique identifier for strike decision |
| Relay ID | Unique identifier for targeting transmission |
| Target Key | Grid location + target ID combo |
| Threat Level | Severity classification (1-5) |
| Confidence | AI confidence in detection (0-1) |
| Soldier Override | Operator forces decision regardless of AI logic |

---

## Example Python Client

```python
import requests
import json

BASE_URL = "http://localhost:8000"

class ComputeDroneClient:
    def __init__(self, compute_id="compute-1"):
        self.compute_id = compute_id
    
    def receive_image(self, report_id, recon_id, grid):
        response = requests.post(
            f"{BASE_URL}/api/compute/{self.compute_id}/receive-image",
            json={
                "image_report_id": report_id,
                "recon_drone_id": recon_id,
                "location_grid": grid,
                "image_data": {"quality": 0.95}
            }
        )
        return response.json()
    
    def process_image(self, reception_id):
        response = requests.post(
            f"{BASE_URL}/api/compute/{self.compute_id}/process-image",
            json={"image_reception_id": reception_id}
        )
        return response.json()
    
    def decide_strike(self, target_key, soldier_approved=False):
        response = requests.post(
            f"{BASE_URL}/api/compute/{self.compute_id}/make-strike-decision",
            json={
                "target_key": target_key,
                "soldier_approval": soldier_approved,
                "soldier_priority_override": None
            }
        )
        return response.json()
    
    def relay_targeting(self, decision_id, attack_drones):
        response = requests.post(
            f"{BASE_URL}/api/compute/{self.compute_id}/relay-targeting",
            json={
                "decision_id": decision_id,
                "assigned_attack_drones": attack_drones
            }
        )
        return response.json()
    
    def get_status(self):
        response = requests.get(
            f"{BASE_URL}/api/compute/{self.compute_id}/status"
        )
        return response.json()

# Usage
client = ComputeDroneClient("compute-1")
reception = client.receive_image("IMG-001", "recon-1", "Grid Alpha 1")
processed = client.process_image(reception["reception_id"])
print(f"Detected {len(processed['detected_targets'])} targets")
```

---

**API Version**: 1.0  
**Last Updated**: April 2024  
**Status**: Production Ready
