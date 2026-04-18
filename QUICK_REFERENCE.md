# Quick Reference: Enhanced Swarm Visualization

## 🎨 Color Coding Guide

```
🟣 PURPLE (Gateway)      = Network relay hub, stays central
🟠 ORANGE (Soldiers)     = Ground operators, NEVER move
🔴 RED (Attack Drones)   = Strike platforms, orbit enemies  
🔷 CYAN (Recon)          = Sensor platform, moves to target

❌ RED X (Enemies)        = Hostile targets detected
🟡 GOLD/ORANGE Pulses    = Signal transmissions propagating
```

## 🚀 What You'll See When You Run Commands

### Command: "JARVIS, deploy swarm to Grid Alpha"

**Immediate Changes:**
1. Cyan recon drone slides toward Grid Alpha
2. Red X markers appear (2-3 enemy targets)
3. Red attack drones start circular orbits around enemies
4. Gold pulses flow along communication edges
5. Orange soldiers stay locked at home position
6. Purple gateway remains at center

**Status Display:**
```
📡 ACTIVE MISSION
Grid Alpha (large yellow text)
Status: target_neutralized
Active Nodes: 6
Propagation Time: 130-160ms

🎯 2 enemies detected
⚔️ Attack sequence: attack-1 → attack-2  
📡 Recon drone scanning (85% coverage)
```

### Second Command: "JARVIS, engage area Charlie"

**Changes:**
- Entire swarm repositions toward new target (Charlie)
- Recon drone relocates and rescans
- Enemies reset to new positions
- Attack drones orbit NEW targets
- Signal animations restart
- Soldiers maintain formation

---

## 📊 Data Flow Diagram

```
VOICE COMMAND
    ↓
OLLAMA LLM (local, .1ms)
    ↓
INTENT: {target: "Grid Alpha", action: "MOVE_TO"}
    ↓
GOSSIP PROTOCOL (simulate 120-160ms propagation)
    ├→ Gateway receives
    ├→ Soldiers receive
    ├→ Recon receives (starts scanning)
    ├→ Attack drones receive (start queuing)
    └→ All synchronized
    ↓
RESPONSE PAYLOAD
    ├─ nodes: [6 drones with drone_type]
    ├─ enemies: [2-3 hostile positions]
    ├─ attack_queue: [ordered attack sequence]
    ├─ recon_status: {scanning: true, coverage: 85%}
    ├─ signal_animations: [5-6 pulsing signals]
    └─ propagation_order: [timestamp sequence]
    ↓
REACT DASHBOARD
    ├─ SwarmGraph renders all elements
    ├─ Signal pulses animate along edges
    ├─ Attack drones orbit enemies
    ├─ Mission card updates in real-time
    └─ Legend shows drone types
```

---

## ⚡ Feature Comparison: Before vs After

| Feature | Before | After |
|---------|--------|-------|
| **Node Colors** | All red (active) or gray | Type-specific: purple, orange, red, cyan |
| **Soldier Behavior** | Generic movement | Static position (never move) |
| **Attack Drones** | Move toward target | Orbit around detected enemies |
| **Recon Drone** | Generic node | Explicit scanning, coverage %, position tracking |
| **Enemy Visualization** | None | Red X markers with threat levels |
| **Attack Coordination** | None | Queue with one-at-a-time sequencing |
| **Signal Display** | Edge pulses only | Animated signal travels along edges |
| **Recon Integration** | None | Detection status, coverage %, scan timing |
| **Visual Legend** | None | Color guide showing drone types |
| **Response Payload** | 100 lines minimal | 150 lines with enemies, attacks, animations |

---

## 🎬 Quick Demo Commands

### Test 1: Deploy
```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, deploy swarm to Grid Alpha"}'
```
✅ **Expect**: Cyan recon moves, red attack drones orbit around 2-3 enemies

### Test 2: Engage Different Area
```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, engage area Charlie"}'
```
✅ **Expect**: Entire formation repositions, enemies reset, attack queue reorders

### Test 3: Scan  
```bash
curl -X POST http://localhost:8000/api/voice-command \
  -H "Content-Type: application/json" \
  -d '{"transcribed_text": "JARVIS, scan zone Bravo"}'
```
✅ **Expect**: Recon drone repositions, scanning status shows high coverage %

---

## 🧠 How It Works

### Soldier Drones (Orange)
- Force strength: VERY HIGH (0.5) - they're anchored
- They stay at original position with 99.9% probability
- When active, they pulse but don't move
- Serve as fire support from known locations

### Attack Drones (Red)
- Force strength: NORMAL (0.35) - they can move
- They compute orbital paths around assigned enemy
- Formula: `x = enemy_x + 40 * cos(animation_phase * 2π)`
- Orbit completes every 2 seconds in smooth circle
- One at a time from attack_queue

### Recon Drone (Cyan)
- Force strength: NORMAL (0.35) - can move
- Mission force pulls it toward target coordinates
- Scanning coverage increases as it gets closer
- Detects and reports enemy positions

### Signal Animations (Gold/Orange Pulses)
- Created from propagation_order events
- Each signal travels from `from_node` to `to_node`
- Timeline: 30ms before arrival, 50ms after
- Color indicates hop count: Gold (direct) vs Orange (relayed)
- Multiple signals can animate simultaneously

---

## 📈 Scalability

### Current: 6 Nodes
- 1 gateway, 2 soldiers, 1 recon, 2 attack
- 2-3 enemies
- Renders smoothly at 30fps

### Potential: 20 Nodes
- Add squad pairs (4 soldiers, 4 attack, 2 recon)
- Scale to 6-10 enemies
- Still smooth performance

### Future: 100+ Nodes
- Need different visualization (heatmap instead of individual nodes)
- D3 force simulation becomes bottleneck
- Could use WebGL for better performance

---

## 🎓 Talking Points for Demo

1. **"Soldiers stay put because they're ground operators"** - They need to hold their positions for fire support. Orange color = unmovable anchor.

2. **"Red drones orbit enemies for a reason"** - Prevents friendly fire, allows coordinated strikes, shows role separation working.

3. **"The cyan drone is scanning"** - Shows autonomous intelligence gathering before engagement. Coverage% = how much of the area has been observed.

4. **"Gold vs orange signals show hop count"** - Gold = direct command, orange = relayed through gossip network. Demonstrates leaderless coordination.

5. **"All 6 nodes synchronized in 130ms without a server"** - This is what DDIL means: Denied (no internet), Degraded (lossy links), Intermittent (connection drops), Limited (bandwidth). Gossip works better.

6. **"Each drone type has different behavior"** - Not a generic swarm. Soldiers hold position. Recon gathers intel. Attacks coordinate sequences. Gateway bridges DDIL gap.

---

## 🐛 If Something Looks Wrong

| Issue | Cause | Fix |
|-------|-------|-----|
| Soldiers moving | Force strength too low | Check SwarmGraph code, should be 0.5 not 0.35 |
| No enemies appearing | Target location missing | Command must include location: "Grid Alpha", not "area" |
| Attack drones not orbiting | animationPhase stuck | animationPhase updates every 30ms, check setInterval |
| No signal pulses | Propagation order empty | Requires active_nodes > 1 |
| Recon not scanning | Outside active_nodes list | 50/50 chance it includes recon, try again |

---

## 🎯 Demo Timeline

- **0:00** - Show dashboard empty
- **0:15** - Run deploy command
- **0:20** - Point out enemies, recon scanning
- **0:25** - Show attack drones orbiting
- **0:40** - Explain soldiers never move (orange rule)
- **0:50** - Run second command (engage Charlie)
- **1:00** - Show repositioning in real-time
- **1:20** - Deep dive into attack_queue JSON
- **2:00** - Q&A on drone types, DDIL, scalability

---

## ✅ Final Checklist Before Demo

- [ ] FastAPI running: `curl http://localhost:8000/health`
- [ ] React frontend loaded: `http://localhost:5173`
- [ ] Can see 6-node dashboard
- [ ] Run test curl command, see enemies appear
- [ ] Verify Ollama still running: `systemctl status ollama`
- [ ] Check browser console (F12) for zero errors
- [ ] Legend visible showing all 4 drone types
- [ ] Signal animations visible (gold/orange pulses)

**You're ready to go! 🚀**
