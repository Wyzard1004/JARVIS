# Phase 4: Backend API & WebSocket Integration

## Overview
Phase 4 integrates the refactored swarm_logic with the FastAPI backend to provide real-time WebSocket updates to the frontend and handle mission commands via gossip protocol.

## Current Status

### ✅ Completed
- Refactored swarm_logic.py (1005 lines, core coordination only)
- Created gossip_protocol.py (message routing)
- Created drone_behaviors.py (movement/behavior)
- Created consensus_simulator.py (simulation code, optional)
- Created mission_simulator.py (mission simulation, optional)
- Fixed import paths for API context (relative imports)
- Enhanced get_state() to include topology for frontend
- Populated graph.nodes during initialization for API compatibility
- All Phase 3 tests still passing ✅

### 📋 Phase 4 Tasks

#### 1. WebSocket State Sync Loop (HIGH PRIORITY)
**File**: `/home/william/JARVIS/base_station/api/main.py` 
**Task**: Update `/ws/swarm` endpoint to:
- [ ] Send real-time topology updates when drones move
- [ ] Stream active gossip messages
- [ ] Broadcast acknowledgments
- [ ] Handle transmission graph updates
- [ ] Implement 100-200ms refresh interval

**Implementation Pattern**:
```python
@app.websocket("/ws/swarm")
async def websocket_swarm_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    swarm = get_swarm()
    
    # Initial state
    state = swarm.get_state()
    await websocket.send_json({
        "event": "swarm_state",
        "state": state,
        "timestamp": datetime.now().isoformat()
    })
    
    # Continuous updates
    while True:
        try:
            # Get latest state
            state = swarm.get_state()
            
            # Send updates
            await websocket.send_json({
                "event": "state_update",
                "nodes": state.get("nodes"),
                "edges": state.get("edges"),
                "gossip_messages": state.get("active_gossip_messages"),
                "spanning_tree": state.get("spanning_tree_edges"),
                "timestamp": datetime.now().isoformat()
            })
            
            # Handle incoming commands
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                # Process command
                await handle_mission_command(message, swarm)
            except asyncio.TimeoutError:
                pass  # Continue loop if no message
                
        except WebSocketDisconnect:
            break
```

#### 2. Mission Command Handler (HIGH PRIORITY)
**Task**: Implement command processing pipeline
- [ ] Parse mission intent from frontend
- [ ] Broadcast via gossip protocol
- [ ] Track command delivery
- [ ] Report status back to frontend

**Command Types to Support**:
- `soldier_command` - Direct soldier instruction
- `recon_mission` - Send recon drones to scan area
- `engage_target` - Attack drone coordination
- `sync_state` - Request full state update
- `change_algorithm` - Switch gossip vs raft

#### 3. Frontend State Visualization Updates (MEDIUM PRIORITY)
**Task**: Enhance frontend to handle new state format
- [ ] Update SwarmGraph component to use new node/edge structure
- [ ] Display gossip message propagation
- [ ] Show spanning tree overlay
- [ ] Real-time position updates

**State Format** (from get_state()):
```json
{
  "nodes": [
    {
      "id": "soldier-1",
      "role": "operator-node",
      "status": "active",
      "grid_position": [13, 5],
      "transmission_range": 3
    }
  ],
  "edges": [
    {
      "source": "soldier-1",
      "target": "soldier-2",
      "quality": 0.85,
      "in_spanning_tree": true
    }
  ],
  "spanning_tree_root": "compute-1",
  "spanning_tree_edges": [
    {"source": "compute-1", "target": "soldier-1"}
  ],
  "active_gossip_messages": [
    {
      "message_id": "gossip-000001",
      "sender_id": "soldier-1",
      "delivered_to": ["soldier-2", "recon-1"],
      "pending_drones": ["attack-1", "attack-2"]
    }
  ],
  "drone_positions": {
    "soldier-1": [13, 5],
    "soldier-2": [15, 7]
  }
}
```

#### 4. Continuous Position Updates (MEDIUM PRIORITY)
**Task**: Integrate drone_behaviors movement with WebSocket
- [ ] Call update_drone_positions() on interval
- [ ] Publish position changes to PushToTalkButton component
- [ ] Update grid display in real-time
- [ ] Show path/waypoints when drones are moving

#### 5. Gossip Message Tracking UI (MEDIUM PRIORITY)
**Task**: Add gossip visualization
- [ ] Show message propagation paths
- [ ] Display ACK/retry events
- [ ] Highlight failed transmissions
- [ ] Timeline of gossip events

## Testing Strategy

### Unit Tests (Phase 4)
```bash
# Test WebSocket connectivity
python3 -m pytest tests/test_websocket.py -v

# Test command handling
python3 -m pytest tests/test_command_handler.py -v

# Test state updates
python3 -m pytest tests/test_state_sync.py -v
```

### Integration Tests
```bash
# Test full API with refactored swarm_logic
python3 -m pytest tests/test_api_integration.py -v

# Test frontend WebSocket communication
npm run test --prefix=command_center
```

### Manual Testing
```bash
# Start backend
cd base_station && python3 api/main.py

# Start frontend in another terminal
cd command_center && npm run dev

# Test with WebSocket client
wscat -c ws://localhost:8000/ws/swarm
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│           (command_center/src/App.jsx & components)          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SwarmGraph | PushToTalkButton | StatusPanel          │   │
│  └──────────────┬──────────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────────┘
                  │ WebSocket (/ws/swarm)
                  │ JSON state updates
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI (api/main.py)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ WebSocket Manager                                    │   │
│  │  - ConnectionManager                                 │   │
│  │  - State sync loop (100ms)                          │   │
│  │  - Command handler                                   │   │
│  └──────────────┬──────────────────────────────────────┘   │
└─────────────────┼──────────────────────────────────────────┘
                  │ Python API
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   SwarmCoordinator                           │
│           (base_station/core/swarm_logic.py)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Core Services:                                       │   │
│  │  - calculate_transmission_graph()                    │   │
│  │  - compute_spanning_tree()                           │   │
│  │  - broadcast_message() / handle_gossip_ack()        │   │
│  │  - update_drone_positions()                          │   │
│  │  - get_state()                                        │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │ Dependencies:                                        │   │
│  │  - GossipProtocol (message routing)                 │   │
│  │  - GridCoordinateSystem (NATO grid)                 │   │
│  │  - EventBus (mission timeline)                       │   │
│  │  - DroneMovement (behavior tracking)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Success Criteria

- [ ] WebSocket endpoint streams state updates reliably
- [ ] Frontend displays real-time topology changes
- [ ] Mission commands execute via gossip protocol
- [ ] Gossip message propagation visible in UI
- [ ] Drone positions update smoothly
- [ ] No memory leaks in long-running connections
- [ ] Performance: < 200ms latency for state updates
- [ ] Handles 10+ concurrent WebSocket connections

## Next Steps

1. **Immediate**: Implement WebSocket state sync loop
2. **Today**: Add mission command handler
3. **Tomorrow**: Update frontend SwarmGraph component
4. **Week**: Add comprehensive Phase 4 tests
5. **Then**: Move to Phase 5 (MQTT hardware integration)

## Files to Modify

- `base_station/api/main.py` - WebSocket endpoint, command handler
- `command_center/src/App.jsx` - Add state subscription
- `command_center/src/components/SwarmGraph.jsx` - Update to use new state format
- `command_center/src/components/StatusPanel.jsx` - Show gossip messages
- `base_station/core/swarm_logic.py` - Already enhanced ✅

## Related Documentation

- [PHASE_3_COMPLETE.md](./PHASE_3_COMPLETE.md) - Previous phase summary
- [QUICKSTART_NEW_ARCHITECTURE.md](./QUICKSTART_NEW_ARCHITECTURE.md) - Architecture overview
- [SOLDIER_CONTROLLER_GUIDE.md](./SOLDIER_CONTROLLER_GUIDE.md) - Command format reference
