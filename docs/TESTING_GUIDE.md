# JARVIS Demo Testing Guide

Complete walkthrough for testing all system components end-to-end.

---

## Prerequisites

Ensure these are running before testing:

```bash
# Terminal 1: Ollama (should already be running as service)
systemctl status ollama
# Output: ● ollama.service - Ollama Service - Active: active (running)

# Terminal 2: FastAPI Backend
cd /home/william/JARVIS/base_station
source venv/bin/activate
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# Output: INFO:     Uvicorn running on http://0.0.0.0:8000

# Terminal 3: React Frontend
cd /home/william/JARVIS/command_center
npm run dev
# Output: Local:   http://localhost:5173/
```

---

## Test 1: Backend Health Check

**Goal**: Verify FastAPI is running and connected to Ollama

```bash
curl http://localhost:8000/health | python3 -m json.tool
```

**Expected Output**:
```json
{
  "status": "operational",
  "subsystems": {
    "api": "online"
  }
}
```

✅ **Pass**: HTTP 200, status = "operational"  
❌ **Fail**: Connection refused or error message

---

## Test 2: Ollama LLM Direct

**Goal**: Test Ollama can parse a command

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "prompt": "What is a gossip protocol?",
    "stream": false
  }' | python3 -m json.tool | head -20
```

**Expected Output**:
```json
{
  "model": "llama3.2:1b",
  "created_at": "2026-04-18T18:00:00.000Z",
  "response": "A gossip protocol is...",
  "done": true,
  "total_duration": 1234567890,
  "load_duration": 567890,
  "prompt_eval_duration": 234567,
  "eval_duration": 432100,
  "eval_count": 42
}
```

✅ **Pass**: Response contains text, `done: true`  
❌ **Fail**: Empty response or connection error

---

## Test 3: AI Bridge Intent Parser

**Goal**: Test LLM → JSON command parsing

```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, deploy swarm to Grid Alpha"}' | python3 -m json.tool
```

**Expected Output**:
```json
{
  "event": "gossip_update",
  "status": "propagating",
  "message": "Command executing via swarm consensus protocol",
  "algorithm": "gossip",
  "control_node": "soldier-1",
  "target_location": "Grid Alpha",
  "target_x": 0,
  "target_y": 0,
  "active_nodes": ["node_1", "node_2", "node_3"],
  "nodes": [
    {"id": "node_1", "status": "active", "x": 0, "y": 0},
    {"id": "node_2", "status": "idle", "x": 100, "y": 50},
    {"id": "node_3", "status": "idle", "x": -100, "y": -50}
  ],
  "edges": [
    {"source": "node_1", "target": "node_2"},
    {"source": "node_1", "target": "node_3"}
  ],
  "propagation_order": ["node_1", "node_2", "node_3"],
  "timestamps": [...]
}
```

✅ **Pass**: Contains nodes, edges, propagation_order, status="propagating"  
❌ **Fail**: Parsing error or empty response

**What this tests**:
- Ollama LLM intent parsing ✓
- Swarm gossip simulation ✓
- Serialization to JSON ✓

---

## Test 4: Swarm State Endpoint

**Goal**: Query current swarm topology

```bash
curl http://localhost:8000/api/swarm-state | python3 -m json.tool
```

**Expected Output**:
```json
{
  "nodes": [
    {"id": "node_1", "status": "active", "x": 0, "y": 0},
    {"id": "node_2", "status": "idle", "x": 100, "y": 50},
    {"id": "node_3", "status": "idle", "x": -100, "y": -50}
  ],
  "edges": [
    {"source": "node_1", "target": "node_2"},
    {"source": "node_1", "target": "node_3"}
  ],
  "timestamp": "2026-04-18T18:00:00Z"
}
```

✅ **Pass**: 3 nodes with coordinates, 2 edges  
❌ **Fail**: Empty nodes or parsing error

---

## Test 5: WebSocket Real-Time Connection

**Goal**: Verify WebSocket can receive gossip updates

### Option A: Using `websocat` (Simple)

```bash
# Install: brew install websocat (macOS) or apt-get install websocat (Linux)
websocat ws://localhost:8000/ws/swarm
# Then in another terminal, trigger a command:
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, attack zone Bravo"}'

# You should see real-time JSON messages in the websocat terminal
```

### Option B: Python Script

```bash
python3 << 'EOF'
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/swarm"
    async with websockets.connect(uri) as websocket:
        print("[WS] Connected!")
        
        # Receive welcome message
        msg = await websocket.recv()
        print(f"[WS] {json.loads(msg)['message']}")
        
        # Receive initial swarm state
        state = await websocket.recv()
        data = json.loads(state)
        print(f"[WS] Received {len(data.get('nodes', []))} nodes")
        
        print("[WS] Listening for updates...")
        # Keep listening for 10 seconds
        for _ in range(10):
            try:
                update = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                msg = json.loads(update)
                print(f"[WS] Event: {msg.get('event')} - Status: {msg.get('status')}")
            except asyncio.TimeoutError:
                print("[WS] Waiting...")

asyncio.run(test_websocket())
EOF
```

**Expected Output**:
```
[WS] Connected!
[WS] Connected to JARVIS Base Station
[WS] Received 3 nodes
[WS] Event: swarm_state with topology
[WS] Listening for updates...
```

✅ **Pass**: Receives connected, swarm_state, and update events  
❌ **Fail**: Connection refused or no messages received

---

## Test 6: Frontend Web UI

**Goal**: Verify React loads and connects to backend

1. **Open browser**: http://localhost:5173

2. **Verify UI loads**:
   - See "JARVIS Command Center" header ✓
   - See "System Status" panel with connection status ✓
   - See "Swarm Topology" D3 graph ✓
   - See "PUSH TO TALK" button ✓

3. **Check browser console** (F12 → Console):
   ```
   [App] Connected to JARVIS Base Station  ✓
   ```

4. **Check connection status**:
   - Status panel should show "CONNECTED" (green)
   - Active Nodes should show "3 / 3"

✅ **Pass**: UI loads, WebSocket says "Connected"  
❌ **Fail**: Connection error or graphical glitches

---

## Test 7: Push-to-Talk Button (Mock)

**Goal**: Test voice command intake flow

1. **In React UI**, click **"🎤 PUSH TO TALK"** button
   - Button turns red and says "🔴 STOP"
   - Browser says "Allow this site to use your microphone"

2. **Speak clearly**: "JARVIS, deploy swarm to Grid Charlie"

3. **Release button** (wait 2 seconds)
   - Button returns to "🎤 PUSH TO TALK"
   - Mock transcript appears in UI
   - "Recent Commands" list shows your command

4. **Check backend logs**:
   ```
   INFO:     127.0.0.1:XXXXX - "POST /api/voice-command HTTP/1.1" 200 OK
   ```

✅ **Pass**: Command processed, shows in list  
❌ **Fail**: Microphone permission denied or no HTTP request

---

## Test 8: Full End-to-End Flow (Automated)

**Goal**: Test entire pipeline: Speech → LLM → Gossip → UI Update

```bash
# Terminal command to simulate user input
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{
    "transcribed_text": "JARVIS, search grid alpha and bravo",
    "consensus_algorithm": "gossip"
  }' | python3 -m json.tool
```

**Expected Flow**: Watch for these in sequence:

1. **Backend receives command**: `POST /api/voice-command`
2. **Ollama parses intent**: Text → JSON with goal, target, action
3. **Swarm calculates gossip**: Identifies nodes, timestamps propagation
4. **WebSocket broadcasts**: Update sent to React UI
5. **D3 graph updates**: Nodes animate, colors change, edges highlight
6. **React "Recent Commands"**: New command appears in list

**Full expected output**:
```json
{
  "event": "gossip_update",
  "status": "propagating",
  "target_location": "Grid Alpha",
  "active_nodes": ["node_1", "node_2", "node_3"],
  "propagation_order": ["node_1", "node_2", "node_3"],
  "confirmation_text": "Search initiated in Grid Alpha and Bravo"
}
```

✅ **Pass**: All 5 steps complete, JSON matches expected structure  
❌ **Fail**: Missing nodes, empty edges, null confirmation_text

---

## Test 9: Error Handling

### Test 9a: Malformed Input

```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": ""}' 
```

**Expected**: HTTP 400 with message "No transcription provided"

### Test 9b: Invalid Command

```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "Lorem ipsum dolor sit amet"}'
```

**Expected**: HTTP 200 with status="ignored", message="Command could not be safely interpreted"

### Test 9c: Ollama Offline

```bash
# Stop Ollama
systemctl stop ollama

# Try command
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, deploy swarm"}' 
```

**Expected**: HTTP 502 or graceful fallback to rules-based parser

---

## Test 10: Performance & Benchmark

**Goal**: Measure latency and bandwidth for pitch deck

```bash
# Measure LLM response time
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "prompt": "Deploy to Grid Alpha",
    "stream": false
  }' > /dev/null 2>&1
```

**Expected**: First call ~2-5 seconds (model loading), subsequent calls <1 second

```bash
# Measure voice-command endpoint latency
time curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, engage target"}' > /dev/null 2>&1
```

**Expected**: <500ms after first warmup

---

## Test Summary Checklist

```
✓ Test 1: Health Check (Backend online)
✓ Test 2: Ollama LLM (Model responsive)
✓ Test 3: Intent Parser (LLM → JSON)
✓ Test 4: Swarm State (Graph topology)
✓ Test 5: WebSocket (Real-time updates)
✓ Test 6: Frontend UI (React loads)
✓ Test 7: Push-to-Talk (Voice input mock)
✓ Test 8: End-to-End (Full pipeline)
✓ Test 9: Error Handling (Graceful failures)
✓ Test 10: Performance (Latency/bandwidth)

DEMO READY: YES ✅
```

---

## Live Demo Script (5 minutes)

1. **"Here's JARVIS running on a local Jetson Orin with no cloud connectivity."**
   - Show Ollama running: `systemctl status ollama`

2. **"I'm going to speak a voice command."**
   - Click Push-to-Talk in React UI
   - Say: "JARVIS, deploy swarm to Grid Bravo"

3. **"Watch the command flow through our system in real-time."**
   - Show backend logs processing the command
   - Show WebSocket receiving gossip updates
   - Show D3 graph animating the swarm topology

4. **"The gossip protocol calculates the most efficient propagation path."**
   - Highlight `propagation_order` in the JSON response
   - Show timing comparison to TCP-based approach

5. **"Everything runs offline, on the edge, with minimal latency."**
   - Show curl test with timing

---

**All tests passing?** You're ready to present! 🎉
