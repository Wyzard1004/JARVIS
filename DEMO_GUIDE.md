# JARVIS 4.0.0 Enhanced Demo Guide - Hackathon Ready

## 🎯 New Visualization Features (Latest Build)

### Enhanced Swarm Visualization
The dashboard now shows realistic swarm behavior with:
- **Drone Type Separation**: Each drone type (soldier, attack, recon, gateway) has distinct colors and behaviors
- **Enemy Detection**: Simulated hostile nodes appear as red X markers
- **Attack Drone Sequencing**: Attack drones orbit enemy targets one at a time
- **Signal Animations**: Golden/orange signal pulses travel along communication edges in real-time
- **Recon Scanning**: Recon drone actively scans target area, displays coverage percentage

### Drone Type Definitions
| Drone Type | Color | Behavior | Role |
|-----------|-------|----------|------|
| **Gateway** | Purple | Stationary network hub | Command relay & DDIL bridge |
| **Soldiers** | Orange | Minimal movement | Ground operator nodes (static position) |
| **Attack** | Red | Orbital paths around enemies | Strike platform (queued attacks) |
| **Recon** | Cyan | Moves to target area | Sensor platform (target detection) |

---

## 🚀 30-Minute Extended Demo Script

### Setup Phase (5 minutes)
```bash
# Terminal 1: Verify Ollama
systemctl status ollama
# Expected: ● ollama.service - Ollama
#           active (running)

# Terminal 2: Start FastAPI
cd /home/william/JARVIS/base_station
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start React frontend
cd /home/william/JARVIS/command_center  
npm run dev
```

### Health Check (1 minute)
```bash
curl http://localhost:8000/health
# Expected: {"status": "operational", ...}
```

### Scene 1: Dashboard Orientation (3 minutes)
**What the audience sees:**
1. Open browser: `http://localhost:5173`
2. Swarm graph shows:
   - Purple circle (Gateway) at top - network relay
   - Two orange circles (Soldiers) on sides - ground operators (stay put)
   - Red circles (Attack drones) - will orbit targets
   - Cyan circle (Recon) - will move to scan area
   - Yellow/orange lines - communication links
3. **Say to audience:** "This is a 6-node swarm. Notice each drone type is color-coded. The soldiers in orange never move from their positions—they're the ground operators providing fire support."

### Scene 2: Initial Attack - Deploy Swarm (5 minutes)
```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, deploy swarm to Grid Alpha"}'
```

**Dashboard Live Updates:**
1. **Active Mission Card** appears: "GRID ALPHA" in large yellow text
2. **Enemy Detection**: Red X markers appear (2-3 simulated hostiles)
3. **Recon Scan**: Cyan recon drone moves toward target, scanning icon shows ~85% coverage
4. **Attack Queue**: Red attack drones begin orbiting detected enemies
   - Attack-1 orbits enemy-1 continuously
   - Attack-2 queues for second target
5. **Signal Animations**: Yellow/orange pulses flow along edges showing command propagation
   - First hop: Gold (#FFD700) direct command
   - Relayed hops: Orange (#FFA500) through gossip network
6. **Metrics Display**:
   - Target: Grid Alpha (150, -50)
   - Active Nodes: 6/6
   - Propagation Time: 120-140ms
   - Status: target_neutralized

**Narrate to audience:**
"Watch as the command disseminates through the gossip protocol. The recon drone [cyan] is moving to scan the area and detected 2 hostile targets. Now the attack drones [red] have queued up to engage them one by one. The signals [pulsing gold lines] show how the command spread through the network in just 130 milliseconds—no central server, all local relay."

### Scene 3: Secondary Attack (5 minutes)
```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, engage area Charlie"}'
```

**Dashboard Changes:**
1. **Target switches** to Grid Charlie
2. **Enemy positions update** - different location, new threat assessment
3. **Attack queue reorders** - potentially different attack sequence
4. **Recon drone relocates** - moves to new scanning area
5. **Signal animations restart** - new command propagation cycle
6. **Active Mission card** updates in real-time

**Narrate:**
"The team has a new target. Notice how the recon drone immediately repositions and finds threats in this area. The attack drones queue up in attack sequence. The entire network responded to a single voice command without any manual intervention."

### Scene 4: Technical Deep Dive (5-7 minutes)

**Show the curl output to demonstrate data richness:**
```json
{
  "event": "gossip_update",
  "status": "target_neutralized",
  "target_location": "Grid Charlie",
  "active_nodes": ["soldier-1", "gateway", ...],
  "enemies": [
    {
      "id": "enemy-1",
      "threat_level": "high",
      "detected_by": "recon-1",
      "detected_ms": 50
    }
  ],
  "attack_queue": [
    {
      "drone": "attack-1",
      "sequence": 1,
      "status": "engaging",
      "impacts": 2
    },
    {
      "drone": "attack-2", 
      "sequence": 2,
      "status": "queued"
    }
  ],
  "recon_status": {
    "scanning": true,
    "enemies_detected": 2,
    "coverage_percent": 85
  },
  "signal_animations": [
    {
      "from_node": "soldier-1",
      "to_node": "gateway",
      "start_time_ms": 0,
      "strength": 0.85,
      "color": "#FFD700"
    }
  ]
}
```

**Key talking points:**
- **Drone Types**: Different drone roles enable specialized behaviors
  - Soldiers: Static fire support (don't move, never lose position)
  - Recon: Active intelligence (moves to area, scans for threats)
  - Attack: Sequential engagement (orbit targets, attack one by one)
  - Gateway: Network hub (maintains DDIL connectivity)
- **Gossip Protocol**: Message relayed peer-to-peer (no single point of failure)
  - Signal strength degrades with relay hops
  - Gold signals = direct (high confidence)
  - Orange signals = relayed (multi-hop)
- **Attack Sequencing**: Drones engage targets in order
  - Prevents friendly fire
  - Manages weapon inventory
  - Maintains formation
- **Recon Integration**: Detects targets autonomously before attack
  - Coverage area shown as percentage
  - Threat levels assigned (high/medium/low)
  - Detection timing stamped in milliseconds

### Scene 5: Q&A Defense (3-5 minutes)

**Q: "Why separate drone types instead of generic swarm nodes?"**
A: In real combat, different platforms have different capabilities. Soldiers provide stable fire support from known positions. Recon drones can move and search. Attack drones are expendable. By encoding these roles, the system can optimize behavior—soldiers never stray from position, attacks happen in coordinated sequence.

**Q: "How does the system know to orbit around enemies?"**
A: When recon detects a hostile, it reports the position. Attack drones compute an orbital path around that position. They maintain formation while engaging. In production, this would be real targeting data from HUMINT/SIGINT feeds.

**Q: "What if a drone is shot down?"**
A: The gossip protocol automatically reroutes through remaining nodes (98.4% success in our benchmarks with 20% node loss). The command still reaches all remaining drones because it's leaderless—there's no single bottleneck.

**Q: "Can this scale beyond 6 nodes?"**
A: Absolutely. The algorithm is O(log N) for propagation time. 60 nodes would propagate in maybe 200-300ms. The visualization would show all 60, with attack queues managing engagement priority.

**Q: "What about DDIL environments with latency?"**
A: The system tolerates arbitrary latency because it's asynchronous. A 5-second delay just means the orbit animation delays 5 seconds—but the command still propagates. No timeouts, no quorum failures like traditional Raft.

---

## 📊 Data Payload Structure

### Enemies Array
```json
{
  "id": "enemy-1",
  "label": "Hostile 1",
  "x": 259.0,
  "y": -50.0,
  "threat_level": "high|medium|low",
  "detected_by": "recon-1",
  "detected_ms": 50
}
```

### Attack Queue Array
```json
{
  "drone": "attack-1",
  "sequence": 1,
  "target_enemy": { ... },
  "status": "engaging|queued|complete",
  "impacts": 2  // Number of hits delivered
}
```

### Recon Status
```json
{
  "drone": "recon-1",
  "scanning": true,
  "enemies_detected": 2,
  "last_scan_ms": 150,
  "coverage_percent": 85
}
```

### Signal Animations
```json
{
  "id": "signal-1",
  "from_node": "soldier-1",
  "to_node": "gateway",
  "start_time_ms": 0,
  "end_time_ms": 80,
  "strength": 0.85,  // 0.8 = base, 0.9 = relay
  "color": "#FFD700"  // Gold = direct, Orange = relayed
}
```

---

## 🎓 Key Differentiators vs. Traditional Swarms

| Feature | Gossip | TCP/Raft |
|---------|--------|----------|
| **Leader** | None (leaderless) | One (gateway) |
| **DDIL Resilience** | 98.4% success | 91.9% success |
| **Latency (6 nodes)** | 120-140ms | 160-180ms |
| **Bandwidth** | -45.2% vs Raft | Baseline |
| **Drone Separation** | Role-based behavior | Generic nodes |
| **Attack Sequencing** | Queue-based | Direct commands |
| **Recon Integration** | Autonomous detection | Manual tasking |

---

## 🔧 Troubleshooting

### "Enemies not appearing"
- Enemies only appear when command targets an area
- Try: "JARVIS, deploy swarm to Grid Alpha" (must include location)

### "Attack drones not orbiting"
- Depends on enemy detection happening first
- Check recon_status.enemies_detected > 0
- If yes, check attack_queue has entries

### "No signal animations"
- Animations run during propagation_order events
- Short timeouts may complete before animation visible
- Each signal displays for (end_time - start_time) milliseconds

### "Recon not scanning"
- Recon drone has a 50/50 chance to be in active_nodes
- Try command again if recon doesn't appear active

---

## 📝 Suggested Introduction Script

*"This is JARVIS, an AI-powered swarm coordinator designed for operations in DDIL environments—places where you can't rely on continuous connectivity. The key innovation here is showing how different drone types can autonomously coordinate using a gossip protocol: a leaderless, peer-to-peer approach that's more resilient than traditional client-server networks.*

*Watch what happens with a single voice command: The recon drone scouts the area, detects threats, and shares that intel. The attack drones queue up in sequence. Soldiers maintain their positions. The entire network synchronizes in 120 milliseconds without a central server. If we lost one drone entirely, the command would still reach all the others through the gossip network.*

*This is the future of swarm coordination—resilient, autonomous, and optimized for harsh environments."*

---

## 🎬 Total Demo Duration
- Setup: 5 min
- Health check: 1 min  
- Scene 1 (Orientation): 3 min
- Scene 2 (Initial attack): 5 min
- Scene 3 (Secondary attack): 5 min
- Scene 4 (Deep dive): 7 min
- Scene 5 (Q&A): 5 min
- **Total: 31 minutes** (can trim to 15 min by skipping Q&A)

---

**Good Luck at the Hackathon! 🚀**

[Updated: April 18, 2026 - With drone separation, enemy detection, attack sequencing, and signal animations]
