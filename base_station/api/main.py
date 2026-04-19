"""
JARVIS Base Station - FastAPI Main Application
Full-Stack Integration Hub (Section 4.0.0)

This is the nervous system of JARVIS:
- Integrates ai_bridge.py (optional language/audio adapter)
- Integrates swarm_logic.py (Giulia's Gossip Protocol)
- Publishes to MQTT for hardware (ESP32s)
- Streams WebSocket updates to React UI
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.ai_bridge import create_confirmation_text, process_audio_command, process_voice_command
from core.swarm_logic import get_swarm
from core.demo_soldier_controller import SoldierControllerNode, CommandPriority, CommandRoute
from core.compute_drone_controller import ComputeDroneController, ThreatLevel, AttackDecision


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_STATION_DIR / ".env")


app = FastAPI(
    title="JARVIS Base Station",
    description="Swarm coordination and consensus hub for DDIL environments",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log when the server starts."""
    print("[STARTUP] JARVIS Base Station initializing...")
    print("[STARTUP] FastAPI running on 0.0.0.0:8000")
    print("[STARTUP] WebSocket endpoint ready at ws://localhost:8000/ws/swarm")
    swarm = get_swarm()
    print(f"[STARTUP] Swarm topology initialized: {len(swarm.graph.nodes)} nodes")
    print("[STARTUP] All systems nominal. Awaiting commands.")


@app.on_event("shutdown")
async def shutdown_event():
    """Log when the server shuts down."""
    print("[SHUTDOWN] JARVIS Base Station shutting down")


class ConnectionManager:
    """Manages WebSocket connections for real-time UI updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict):
        stale_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:
                print(f"Error broadcasting to client: {exc}")
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


manager = ConnectionManager()

# Initialize demo soldier controllers (can be puppeted by command center)
demo_soldiers = {
    "soldier-1": SoldierControllerNode(soldier_id="soldier-1", operator_node_id="soldier-1"),
    "soldier-2": SoldierControllerNode(soldier_id="soldier-2", operator_node_id="soldier-2"),
}

# Initialize compute drone controllers (image processing and targeting)
compute_drones = {
    "compute-1": ComputeDroneController(drone_id="compute-1", processor_capability=0.95),
    "compute-2": ComputeDroneController(drone_id="compute-2", processor_capability=0.93),
}


def _default_operator_origin(transcribed_text: str, payload: Dict | None = None) -> str:
    payload = payload or {}
    origin = payload.get("origin") or payload.get("operator_node")
    if origin:
        return origin

    normalized = transcribed_text.lower()
    if any(token in normalized for token in {"operator two", "operator 2", "soldier two", "soldier 2"}):
        return "soldier-2"
    return "soldier-1"


def mock_parse_intent(payload: Dict) -> Dict:
    """Fallback parser for direct command payloads when ai_bridge is bypassed."""
    transcribed_text = (payload.get("transcribed_text") or "").strip()
    normalized = transcribed_text.lower()
    origin = _default_operator_origin(transcribed_text, payload)

    target_location = payload.get("target_location") or payload.get("target")
    if not target_location:
        if "bravo" in normalized:
            target_location = "Grid Bravo"
        elif "charlie" in normalized:
            target_location = "Grid Charlie"
        else:
            target_location = "Grid Alpha"

    action_code = payload.get("action_code") or payload.get("action")
    if not action_code:
        if any(token in normalized for token in {"engage", "strike", "fire", "tank", "armor"}):
            action_code = "ENGAGE_TARGET"
        elif any(token in normalized for token in {"sync", "rally", "regroup"}):
            action_code = "SYNC"
        elif any(token in normalized for token in {"scan", "search", "sweep", "recon"}):
            action_code = "SEARCH"
        else:
            action_code = "RED_ALERT"

    return {
        "intent": payload.get("intent", "swarm_redeploy"),
        "target_location": target_location,
        "action_code": action_code,
        "confidence": float(payload.get("confidence", 0.82)),
        "consensus_algorithm": payload.get("consensus_algorithm") or payload.get("algorithm") or "gossip",
        "origin": origin,
        "operator_node": origin,
        "network_conditions": payload.get("network_conditions", {}),
        "transcribed_text": transcribed_text,
        "parsed_command": payload.get("parsed_command"),
    }


def _humanize_location(location: str | None) -> str | None:
    if not location:
        return None
    return location.replace("_", " ").title()


def _action_code_from_goal(goal: str | None) -> str:
    mapping = {
        "ATTACK_AREA": "ENGAGE_TARGET",
        "SCAN_AREA": "SEARCH",
        "MOVE_TO": "MOVE_TO",
        "AVOID_AREA": "AVOID_AREA",
        "HOLD_POSITION": "HOLD_POSITION",
        "ABORT": "ABORT",
        "NO_OP": "NO_OP",
    }
    return mapping.get((goal or "").upper(), (goal or "RED_ALERT").upper())


def _to_swarm_intent(parsed_command: Dict, transcribed_text: str, payload: Dict | None = None) -> Dict:
    payload = payload or {}
    goal = parsed_command.get("goal", "NO_OP")
    target_location = parsed_command.get("target_location")
    avoid_location = parsed_command.get("avoid_location")
    origin = _default_operator_origin(transcribed_text, payload)

    return {
        "intent": parsed_command.get("intent", payload.get("intent", "swarm_command")),
        "target_location": _humanize_location(target_location or avoid_location) or payload.get("target_location") or payload.get("target"),
        "action_code": payload.get("action_code") or payload.get("action") or _action_code_from_goal(goal),
        "confidence": float(parsed_command.get("confidence", payload.get("confidence", 0.82))),
        "consensus_algorithm": payload.get("consensus_algorithm") or payload.get("algorithm") or "gossip",
        "origin": origin,
        "operator_node": origin,
        "network_conditions": payload.get("network_conditions", {}),
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
    }


def _build_active_nodes(state: Dict) -> list[str]:
    if state.get("active_nodes"):
        return list(state.get("active_nodes", []))
    return [node["id"] for node in state.get("nodes", []) if node.get("status") == "active"]


def _get_drone_type(node_id: str) -> str:
    """Map node ID to drone type for visualization."""
    if node_id == "gateway":
        return "gateway"
    elif node_id.startswith("compute"):
        return "compute"
    elif node_id.startswith("soldier"):
        return "soldier"
    elif node_id.startswith("recon"):
        return "recon"
    elif node_id.startswith("attack"):
        return "attack"
    return "unknown"


def _simulate_enemies_and_attacks(target_location: str, active_nodes: list, propagation_order: list) -> Dict:
    """Simulate enemy detection and attack drone sequencing based on command."""
    import random
    import math
    
    # Simulate enemy positions near target
    enemies = []
    if target_location:
        # Simulate 2-3 enemies randomly placed
        num_enemies = random.randint(2, 3)
        for i in range(num_enemies):
            angle = (i / num_enemies) * 2 * math.pi
            distance = random.randint(80, 120)
            enemy_x = 150 + distance * math.cos(angle)
            enemy_y = -50 + distance * math.sin(angle)
            enemies.append({
                "id": f"enemy-{i+1}",
                "label": f"Hostile {i+1}",
                "x": enemy_x,
                "y": enemy_y,
                "threat_level": random.choice(["high", "medium", "low"]),
                "detected_by": "recon-1",  # Recon detected it
                "detected_ms": random.randint(50, 150)
            })
    
    # Simulate attack drone sequencing
    attack_drones = [n for n in active_nodes if "attack" in n]
    attack_queue = []
    for idx, drone in enumerate(sorted(attack_drones)):
        attack_queue.append({
            "drone": drone,
            "sequence": idx + 1,
            "target_enemy": enemies[idx % len(enemies)] if enemies else None,
            "status": "queued" if idx > 0 else "engaging",
            "impacts": random.randint(1, 2) if idx == 0 else 0
        })
    
    # Simulate recon scanning
    recon_status = {
        "drone": "recon-1",
        "scanning": "recon-1" in active_nodes,
        "enemies_detected": len(enemies),
        "last_scan_ms": random.randint(80, 200) if enemies else 0,
        "coverage_percent": 85 if enemies else 0
    }
    
    # Simulate operator signaling flow: recon → operators → attack drones
    operator_signals = []
    if enemies and "recon-1" in active_nodes:
        operators = [n for n in active_nodes if "soldier" in n]
        
        # Phase 1: Recon reports to operators (~150ms)
        for op in operators:
            operator_signals.append({
                "phase": "recon_to_operators",
                "from": "recon-1",
                "to": op,
                "data": f"enemies_detected: {len(enemies)}",
                "start_time_ms": 100 + random.randint(0, 50),
                "end_time_ms": 150 + random.randint(0, 30)
            })
        
        # Phase 2: Operators signal attack drones (~250ms)
        for idx, drone in enumerate(attack_drones):
            op = operators[idx % len(operators)]
            operator_signals.append({
                "phase": "operators_to_attacks",
                "from": op,
                "to": drone,
                "data": f"engage_target: {idx+1}",
                "start_time_ms": 200 + (idx * 50),
                "end_time_ms": 280 + (idx * 50)
            })
    
    return {
        "enemies": enemies,
        "attack_queue": attack_queue,
        "recon_status": recon_status,
        "operator_signals": operator_signals
    }


def _simulate_signal_animations(propagation_order: list, edges: list) -> list:
    """Create signal animation data for pulsing transmissions along edges."""
    animations = []
    
    for i, event in enumerate(propagation_order):
        if i == 0:
            continue  # Skip origin node
        
        node = event.get("node")
        hop = event.get("hop")
        timestamp = event.get("timestamp_ms", 0)
        
        # Find the edge this signal traveled on (approximate from propagation order)
        if i > 0:
            prev_node = propagation_order[i-1].get("node")
            # Create animation: signal pulses from prev_node to node
            animations.append({
                "id": f"signal-{i}",
                "from_node": prev_node,
                "to_node": node,
                "start_time_ms": timestamp - 30,  # Start slightly before arrival
                "end_time_ms": timestamp + 50,    # End after arrival
                "strength": 0.8 + (hop * 0.05),  # Strength decreases with hops
                "color": "#FFD700" if hop == 1 else "#FFA500"  # Gold for direct, orange for relayed
            })
    
    return animations


def _build_lean_ui_event(consensus_result: Dict, transcribed_text: str, parsed_command: Dict | None, confirmation_text: str | None) -> Dict:
    """Build a lean response for WebSocket broadcast to React UI (minimal payload)."""
    active_nodes = _build_active_nodes(consensus_result)
    
    # Extract only essential node/edge info for visualization
    nodes = consensus_result.get("nodes", [])
    lean_nodes = [
        {
            "id": n.get("id"),
            "label": n.get("label"),
            "type": n.get("type") or _get_drone_type(n.get("id", "")),
            "role": n.get("role"),
            "status": n.get("status"),
            "behavior": n.get("behavior"),
            "position": n.get("position"),
            "next_waypoint": n.get("next_waypoint"),
            "transmission_range": n.get("transmission_range"),
            "health": n.get("health"),
            "fuel": n.get("fuel"),
            "render": n.get("render"),
        }
        for n in nodes
    ]
    
    edges = consensus_result.get("edges", [])
    lean_edges = [
        {
            "source": e.get("source"),
            "target": e.get("target"),
            "quality": e.get("quality"),
            "distance": e.get("distance"),
            "in_spanning_tree": e.get("in_spanning_tree", False),
        }
        for e in edges
    ]
    
    # Simplify propagation order (just node id, timestamp, hop)
    prop_order = consensus_result.get("propagation_order", [])
    lean_prop = [{"node": p.get("node"), "hop": p.get("hop"), "timestamp_ms": p.get("timestamp_ms")} for p in prop_order]
    
    # Simulate enemy detection and attacks
    target_location = consensus_result.get("target_location", "")
    sim_data = _simulate_enemies_and_attacks(target_location, active_nodes, prop_order)
    
    # Simulate signal animations
    signal_animations = _simulate_signal_animations(prop_order, edges)
    
    return {
        "event": "gossip_update",
        "status": consensus_result.get("status", "propagating"),
        "message": "Command executing via swarm consensus protocol",
        "algorithm": consensus_result.get("algorithm"),
        "target_location": consensus_result.get("target_location"),
        "target_x": consensus_result.get("target_x", 0),
        "target_y": consensus_result.get("target_y", 0),
        "nodes": lean_nodes,
        "edges": lean_edges,
        "active_nodes": active_nodes,
        "propagation_order": lean_prop,
        "total_propagation_ms": consensus_result.get("total_propagation_ms", 0),
        "confirmation_text": confirmation_text,
        "enemies": sim_data.get("enemies", []),
        "attack_queue": sim_data.get("attack_queue", []),
        "recon_status": sim_data.get("recon_status", {}),
        "operator_signals": sim_data.get("operator_signals", []),
        "signal_animations": signal_animations,
        "structures": consensus_result.get("structures", []),
        "events": consensus_result.get("events", []),
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
        "timestamp": datetime.now().isoformat(),
    }


def _build_swarm_event(consensus_result: Dict, transcribed_text: str, parsed_command: Dict | None, confirmation_text: str | None) -> Dict:
    """Build full response for REST API (includes all details for logging/debugging)."""
    search_state = consensus_result.get("search_state", {})
    return {
        "event": "gossip_update",
        "status": consensus_result.get("status", "propagating"),
        "message": "Command executing via swarm consensus protocol",
        "algorithm": consensus_result.get("algorithm"),
        "control_node": search_state.get("control_node"),
        "target_location": consensus_result.get("target_location"),
        "target_x": consensus_result.get("target_x", 0),
        "target_y": consensus_result.get("target_y", 0),
        "nodes": consensus_result.get("nodes", []),
        "edges": consensus_result.get("edges", []),
        "active_nodes": _build_active_nodes(consensus_result),
        "propagation_order": consensus_result.get("propagation_order", []),
        "total_propagation_ms": consensus_result.get("total_propagation_ms", 0),
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
        "confirmation_text": confirmation_text,
        "timestamp": datetime.now().isoformat(),
    }


async def _dispatch_swarm_command(transcribed_text: str, swarm_intent: Dict, parsed_command: Dict | None = None) -> Dict:
    confirmation_text = create_confirmation_text(parsed_command) if parsed_command else None
    action_code = swarm_intent.get("action_code", "NO_OP")

    if action_code == "NO_OP":
        return {
            "status": "ignored",
            "message": "Command could not be safely interpreted",
            "transcribed_text": transcribed_text,
            "parsed_command": parsed_command,
            "confirmation_text": confirmation_text,
            "nodes": [],
            "edges": [],
            "active_nodes": [],
        }

    swarm = get_swarm()
    algorithm = (swarm_intent.get("consensus_algorithm") or "gossip").lower()
    if algorithm in {"raft", "tcp", "tcp-raft", "raft-consensus", "leader"}:
        consensus_result = swarm.calculate_raft_path(swarm_intent)
    else:
        consensus_result = swarm.calculate_gossip_path(swarm_intent)

    # Build lean event for both WebSocket broadcast and REST API response
    lean_payload = _build_lean_ui_event(
        consensus_result,
        transcribed_text,
        parsed_command,
        confirmation_text,
    )
    
    await manager.broadcast(lean_payload)
    return lean_payload


@app.get("/health")
async def health_check():
    """Verify the Base Station is online."""
    return {
        "status": "operational",
        "subsystems": {
            "api": "online",
        },
    }


@app.websocket("/ws/swarm")
async def websocket_swarm_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket connection for swarm state updates.
    
    Sends continuous topology updates (~100ms interval) including:
    - Drone positions and behaviors
    - Transmission graph edges
    - Spanning tree structure
    - Active gossip messages
    - Drone status (active, lurking, etc.)
    
    Receives mission commands:
    - soldier_command: Direct instruction to a drone
    - recon_mission: Send recon to scan an area
    - engage_target: Attack drone coordination
    - change_algorithm: Switch gossip/raft protocols
    """
    import asyncio
    
    print(f"[WebSocket] Client connecting from {websocket.client}")
    try:
        await manager.connect(websocket)
        print("[WebSocket] Client connected successfully")
        
        # Send welcome message
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to JARVIS Base Station - Real-time Swarm Updates",
            "version": "Phase 4",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize state tracking
        swarm = get_swarm()
        last_state_hash = None
        update_interval = 0.100  # 100ms between state updates
        
        # Send initial complete swarm topology
        print("[WebSocket] Sending initial swarm topology...")
        initial_state = swarm.get_state()
        initial_message = {
            "event": "initial_state",
            "nodes": initial_state.get("nodes", []),
            "edges": initial_state.get("edges", []),
            "spanning_tree_root": initial_state.get("spanning_tree_root"),
            "spanning_tree_edges": initial_state.get("spanning_tree_edges", []),
            "drone_positions": initial_state.get("drone_positions", {}),
            "drone_behaviors": initial_state.get("drone_behaviors", {}),
            "active_gossip_messages": initial_state.get("active_gossip_messages", []),
            "enemies": initial_state.get("enemies", []),
            "structures": initial_state.get("structures", []),
            "events": initial_state.get("events", []),
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(initial_message)
        print("[WebSocket] Initial state sent")
        
        # Continuous state sync loop (runs concurrently with message handler)
        async def state_sync_loop():
            """Push state updates to client at regular interval."""
            while websocket in manager.active_connections:
                try:
                    current_state = swarm.get_state()
                    
                    # Build state update with all topology information
                    state_update = {
                        "event": "state_update",
                        "nodes": current_state.get("nodes", []),
                        "edges": current_state.get("edges", []),
                        "spanning_tree_root": current_state.get("spanning_tree_root"),
                        "spanning_tree_edges": current_state.get("spanning_tree_edges", []),
                        "drone_positions": current_state.get("drone_positions", {}),
                        "drone_behaviors": current_state.get("drone_behaviors", {}),
                        "active_gossip_messages": current_state.get("active_gossip_messages", []),
                        "enemies": current_state.get("enemies", []),
                        "structures": current_state.get("structures", []),
                        "events": current_state.get("events", []),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Send update
                    await websocket.send_json(state_update)
                    
                except Exception as e:
                    print(f"[WebSocket] Error in state_sync_loop: {e}")
                    break
                
                # Wait before next update
                await asyncio.sleep(update_interval)
        
        # Start background state sync task
        sync_task = asyncio.create_task(state_sync_loop())
        
        # Handle incoming commands (blocking loop)
        while True:
            try:
                # Receive command with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                try:
                    command = json.loads(data)
                    print(f"[WebSocket] Received command: {command.get('type', 'unknown')}")
                    
                    # Route command to handler
                    response = await handle_websocket_command(command, swarm)
                    
                    # Echo response back to client
                    await websocket.send_json({
                        "event": "command_response",
                        "command_type": command.get("type"),
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except json.JSONDecodeError:
                    print(f"[WebSocket] Invalid JSON received: {data}")
                    await websocket.send_json({
                        "event": "error",
                        "error": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except asyncio.TimeoutError:
                # Keep-alive timeout - just continue loop
                continue
            except WebSocketDisconnect:
                print("[WebSocket] Client disconnected gracefully")
                break
            except Exception as e:
                print(f"[WebSocket] Error receiving message: {e}")
                break
        
        # Clean up sync task when client disconnects
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
            
    except Exception as e:
        print(f"[WebSocket ERROR] {type(e).__name__}: {e}")
    
    finally:
        manager.disconnect(websocket)
        print(f"[WebSocket] Cleaned up connection for {websocket.client}")


async def handle_websocket_command(command: Dict, swarm) -> Dict:
    """
    Process incoming WebSocket commands.
    
    Command types:
    - soldier_command: Send instruction to drone
    - recon_mission: Request scout mission
    - engage_target: Attack drone coordination
    - sync_state: Request full state dump
    - change_algorithm: Switch protocols
    """
    command_type = command.get("type", "unknown")
    
    if command_type == "sync_state":
        # Return full state dump
        state = swarm.get_state()
        return {
            "status": "success",
            "state": {
                "nodes": state.get("nodes", []),
                "edges": state.get("edges", []),
                "spanning_tree": state.get("spanning_tree_edges", []),
                "gossip_messages": state.get("active_gossip_messages", []),
            }
        }
    
    elif command_type == "soldier_command":
        # Direct drone instruction
        target_drone = command.get("target_drone")
        instruction = command.get("instruction")
        
        if not target_drone or not instruction:
            return {
                "status": "error",
                "error": "Missing target_drone or instruction"
            }
        
        # Validate drone exists
        if target_drone not in [n["id"] for n in swarm.get_state().get("nodes", [])]:
            return {
                "status": "error",
                "error": f"Drone {target_drone} not found in swarm"
            }
        
        # Parse instruction (behavior change, movement, etc.)
        behavior = instruction.get("behavior")
        if behavior:
            swarm.set_drone_behavior(target_drone, behavior)
            return {
                "status": "success",
                "message": f"Drone {target_drone} behavior changed to {behavior}",
                "drone_id": target_drone
            }
        
        return {
            "status": "error",
            "error": "Unrecognized instruction format"
        }
    
    elif command_type == "recon_mission":
        # Send recon drones to scan area
        grid_location = command.get("grid_location", "Bravo")
        
        recon_drones = [
            n["id"] for n in swarm.get_state().get("nodes", [])
            if "recon" in n["id"]
        ]
        
        if not recon_drones:
            return {
                "status": "error",
                "error": "No recon drones available"
            }
        
        # Set recon drones to 'patrol' behavior
        for drone_id in recon_drones:
            swarm.set_drone_behavior(drone_id, "patrol")
        
        return {
            "status": "success",
            "message": f"Sent {len(recon_drones)} recon drones to scan {grid_location}",
            "recon_drones": recon_drones,
            "target_location": grid_location
        }
    
    elif command_type == "engage_target":
        # Coordinate attack drones
        target_location = command.get("target_location")
        priority = command.get("priority", "high")
        
        attack_drones = [
            n["id"] for n in swarm.get_state().get("nodes", [])
            if "attack" in n["id"]
        ]
        
        if not attack_drones:
            return {
                "status": "error",
                "error": "No attack drones available"
            }
        
        # Set attack drones to 'swarm' behavior
        for drone_id in attack_drones:
            swarm.set_drone_behavior(drone_id, "swarm")
        
        return {
            "status": "success",
            "message": f"Coordinating {len(attack_drones)} attack drones on {target_location}",
            "attack_drones": attack_drones,
            "target_location": target_location,
            "priority": priority
        }
    
    elif command_type == "change_algorithm":
        # Switch consensus algorithm
        algorithm = command.get("algorithm", "gossip").lower()
        
        if algorithm not in ["gossip", "raft", "pbft"]:
            return {
                "status": "error",
                "error": f"Unknown algorithm: {algorithm}"
            }
        
        return {
            "status": "success",
            "message": f"Algorithm switched to {algorithm}",
            "algorithm": algorithm
        }
    
    else:
        return {
            "status": "error",
            "error": f"Unknown command type: {command_type}"
        }


@app.post("/api/voice-command")
async def voice_command(payload: Dict):
    """Process a text voice command from the React UI."""
    transcribed_text = (payload.get("transcribed_text") or "").strip()
    has_direct_intent = any(payload.get(key) for key in ("target_location", "target", "action_code", "action"))

    if has_direct_intent:
        swarm_intent = mock_parse_intent(payload)
        return await _dispatch_swarm_command(
            transcribed_text or "Direct command",
            swarm_intent,
            swarm_intent.get("parsed_command"),
        )

    if not transcribed_text:
        raise HTTPException(status_code=400, detail="No transcription provided")

    parsed_command = process_voice_command(transcribed_text)
    swarm_intent = _to_swarm_intent(parsed_command, transcribed_text, payload)
    return await _dispatch_swarm_command(transcribed_text, swarm_intent, parsed_command)


@app.post("/api/transcribe-command")
async def transcribe_command(audio: UploadFile = File(...)):
    """Process recorded microphone audio from the React UI."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio uploaded")

    try:
        command_result = process_audio_command(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
            content_type=audio.content_type or "audio/webm",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Audio transcription failed: {exc}") from exc

    transcribed_text = command_result["transcribed_text"]
    parsed_command = command_result["parsed_command"]
    swarm_intent = _to_swarm_intent(parsed_command, transcribed_text)
    return await _dispatch_swarm_command(transcribed_text, swarm_intent, parsed_command)


@app.get("/api/swarm-state")
async def get_swarm_state():
    """Fetch the current state of the swarm."""
    swarm = get_swarm()
    state = swarm.get_state()

    return {
        "nodes": state.get("nodes", []),
        "edges": state.get("edges", []),
        "active_nodes": _build_active_nodes(state),
        "propagation_order": state.get("propagation_order", []),
        "status": state.get("status", "idle"),
        "algorithm": state.get("algorithm", "adaptive-gossip"),
        "target_location": state.get("target_location", "Grid Alpha"),
        "target_x": state.get("target_x", 0),
        "target_y": state.get("target_y", 0),
        "control_node": state.get("search_state", {}).get("control_node"),
        "protocol": state.get("protocol", {}),
        "delivery_summary": state.get("delivery_summary", {}),
        "search_state": state.get("search_state", {}),
        "target_tasks": state.get("search_state", {}).get("target_tasks", []),
        "engagements": state.get("search_state", {}).get("engagements", []),
        "object_reports": state.get("object_reports", []),
        "benchmark": state.get("benchmark", {}),
        "available_algorithms": state.get("available_algorithms", []),
        "timestamp": state.get("timestamp", datetime.now().isoformat()),
    }


# ============================================================================
# SOLDIER CONTROLLER ENDPOINTS (Demo Puppetable Command Pipeline)
# ============================================================================

@app.post("/api/soldier/{soldier_id}/request-recon")
async def soldier_request_recon(soldier_id: str, payload: Dict):
    """
    ROUTE: Soldier -> Operator -> Recon
    
    Soldier requests reconnaissance through operator.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    area_label = payload.get("area_label", "Grid Alpha")
    target_x = payload.get("target_x", 0)
    target_y = payload.get("target_y", 0)
    priority = CommandPriority[payload.get("priority", "HIGH")]
    
    command = soldier.request_reconnaissance(
        area_label=area_label,
        target_x=target_x,
        target_y=target_y,
        priority=priority
    )
    
    return {
        "command_id": command["command_id"],
        "route": command["route"],
        "status": command["status"],
        "area_label": area_label,
        "message": f"Soldier {soldier_id} requested reconnaissance of {area_label}",
    }


@app.post("/api/soldier/{soldier_id}/request-attack")
async def soldier_request_attack(soldier_id: str, payload: Dict):
    """
    ROUTE: Soldier -> Operator -> Attack (default)
           Soldier -> Attack (if requires_approval=False)
    
    Soldier requests attack through operator or issues direct command.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    area_label = payload.get("area_label", "Grid Alpha")
    target_x = payload.get("target_x", 0)
    target_y = payload.get("target_y", 0)
    requires_approval = payload.get("requires_approval", True)
    priority = CommandPriority[payload.get("priority", "HIGH")]
    
    command = soldier.request_attack(
        area_label=area_label,
        target_x=target_x,
        target_y=target_y,
        priority=priority,
        requires_approval=requires_approval
    )
    
    return {
        "command_id": command["command_id"],
        "route": command["route"],
        "status": command["status"],
        "area_label": area_label,
        "requires_approval": requires_approval,
        "message": f"Soldier {soldier_id} requested attack on {area_label}",
    }


@app.post("/api/soldier/{soldier_id}/approve-command/{command_id}")
async def soldier_approve_command(soldier_id: str, command_id: str):
    """
    Operator approves soldier's command and relays to drones.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    approval = soldier.approve_and_relay_command(command_id)
    
    if "error" in approval:
        raise HTTPException(status_code=404, detail=approval["error"])
    
    return {
        "approved": True,
        "command_id": command_id,
        "mission_id": approval["mission_id"],
        "route": approval["route"],
        "message": f"Command {command_id} approved and relayed",
    }


@app.post("/api/soldier/{soldier_id}/process-recon-report")
async def soldier_process_recon_report(soldier_id: str, payload: Dict):
    """
    ROUTE: Recon -> Operator -> Soldier
    
    Process reconnaissance findings and update soldier's tactical picture.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    mission_id = payload.get("mission_id")
    enemies_detected = payload.get("enemies_detected", [])
    coverage_percent = payload.get("coverage_percent", 0)
    threat_level = payload.get("threat_level", "medium")
    
    report = soldier.process_recon_report(
        mission_id=mission_id,
        enemies_detected=enemies_detected,
        coverage_percent=coverage_percent,
        threat_level=threat_level
    )
    
    return {
        "report_id": report["report_id"],
        "enemies_detected": len(enemies_detected),
        "threat_level": threat_level,
        "coverage_percent": coverage_percent,
        "status": report["status"],
        "message": f"Recon report received by {soldier_id}: {len(enemies_detected)} enemies detected",
    }


@app.post("/api/soldier/{soldier_id}/authorize-strike/{recon_report_id}")
async def soldier_authorize_strike(soldier_id: str, recon_report_id: str, payload: Dict = None):
    """
    ROUTE: Recon -> Operator -> Attack
    (with soldier authorization)
    
    Based on recon findings, soldier authorizes strike.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    payload = payload or {}
    soldier = demo_soldiers[soldier_id]
    priority = CommandPriority[payload.get("priority", "CRITICAL")]
    
    strike_command = soldier.authorize_strike_from_recon_report(
        recon_report_id=recon_report_id,
        priority=priority
    )
    
    if "error" in strike_command:
        raise HTTPException(status_code=404, detail=strike_command["error"])
    
    return {
        "command_id": strike_command["command_id"],
        "route": strike_command["route"],
        "mission_id": strike_command["mission_id"],
        "status": strike_command["status"],
        "enemies_to_engage": len(strike_command.get("enemies_to_engage", [])),
        "message": f"Strike authorized by {soldier_id} based on recon findings",
    }


@app.post("/api/soldier/{soldier_id}/process-bda")
async def soldier_process_bda(soldier_id: str, payload: Dict):
    """
    Process Battle Damage Assessment from recon drone.
    Soldier reviews effectiveness of strike.
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    mission_id = payload.get("mission_id")
    damage_assessment = payload.get("damage_assessment", {})
    
    bda = soldier.process_bda_report(
        mission_id=mission_id,
        damage_assessment=damage_assessment
    )
    
    return {
        "bda_id": bda["bda_id"],
        "mission_id": mission_id,
        "damage_assessment": damage_assessment,
        "status": bda["status"],
        "message": f"BDA processed by {soldier_id}: {damage_assessment.get('destroyed', 0)} targets destroyed",
    }


@app.get("/api/soldier/{soldier_id}/status")
async def soldier_get_status(soldier_id: str):
    """Get complete status of a soldier controller."""
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    return soldier.get_command_summary()


@app.post("/api/soldier/{soldier_id}/simulate-scenario")
async def soldier_simulate_scenario(soldier_id: str, payload: Dict):
    """
    Simulate a complete tactical scenario:
    1. Recon request
    2. Operator approval
    3. Enemy detection
    4. Strike authorization
    5. BDA
    """
    if soldier_id not in demo_soldiers:
        raise HTTPException(status_code=404, detail=f"Soldier {soldier_id} not found")
    
    soldier = demo_soldiers[soldier_id]
    grid_area = payload.get("area", "Grid Alpha")
    
    scenario = soldier.simulate_tactical_scenario(grid_area)
    
    return {
        "scenario_id": scenario["scenario_id"],
        "area": grid_area,
        "stages": scenario["stages"],
        "status": scenario["status"],
        "message": f"Tactical scenario complete in {grid_area}",
    }


# ============================================================================
# COMPUTE DRONE ENDPOINTS - Image Processing & Targeting Pipeline
# ============================================================================

@app.post("/api/compute/{compute_id}/receive-image")
async def compute_receive_recon_image(compute_id: str, payload: Dict):
    """
    Receive image from recon drone for processing.
    
    Payload:
    {
        "image_report_id": "REP-001",
        "recon_drone_id": "recon-1",
        "location_grid": "Grid Alpha 1",
        "image_data": {"quality": 0.95, "resolution": "1080p"}
    }
    """
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    
    image_report_id = payload.get("image_report_id")
    recon_drone_id = payload.get("recon_drone_id")
    location_grid = payload.get("location_grid", "Grid Alpha")
    image_data = payload.get("image_data", {})
    
    reception = compute.receive_recon_image(
        image_report_id=image_report_id,
        recon_drone_id=recon_drone_id,
        image_data=image_data,
        location_grid=location_grid
    )
    
    return {
        "status": "received",
        "reception_id": reception["reception_id"],
        "queue_position": len(compute.image_queue),
        "compute_processor": compute_id
    }


@app.post("/api/compute/{compute_id}/process-image")
async def compute_process_image(compute_id: str, payload: Dict):
    """
    Process queued image: detect targets, classify threats, assess priority.
    
    Payload:
    {
        "image_reception_id": "compute-1-rx-REP-001"
    }
    """
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    image_reception_id = payload.get("image_reception_id")
    
    result = compute.process_image(image_reception_id)
    
    if "error" in result.get("status", ""):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    
    return {
        "processing_id": result["processing_id"],
        "location_grid": result["location_grid"],
        "detected_targets": result["detected_targets"],
        "targets_count": len(result["detected_targets"]),
        "processor_confidence": result["processor_confidence"],
        "status": "processed"
    }


@app.post("/api/compute/{compute_id}/make-strike-decision")
async def compute_make_strike_decision(compute_id: str, payload: Dict):
    """
    Analyze target and make strike authorization decision.
    Can be overridden by soldier approval.
    
    Payload:
    {
        "target_key": "Grid Alpha 1-TGT-001",
        "soldier_approval": false,
        "soldier_priority_override": null
    }
    """
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    target_key = payload.get("target_key")
    soldier_approval = payload.get("soldier_approval", False)
    soldier_override = payload.get("soldier_priority_override")
    
    decision = compute.make_strike_decision(
        target_key=target_key,
        soldier_approval=soldier_approval,
        soldier_priority_override=soldier_override
    )
    
    return {
        "decision_id": decision["decision_id"],
        "target_id": decision["target_id"],
        "decision": decision["decision"],
        "reasoning": decision["reasoning"],
        "soldier_approved": decision["soldier_approved"],
        "status": decision["status"]
    }


@app.post("/api/compute/{compute_id}/relay-targeting")
async def compute_relay_targeting(compute_id: str, payload: Dict):
    """
    Relay authorized strike targeting to assigned attack drones.
    
    Payload:
    {
        "decision_id": "compute-1-dec-TGT-001",
        "assigned_attack_drones": ["attack-1", "attack-2"]
    }
    """
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    decision_id = payload.get("decision_id")
    assigned_drones = payload.get("assigned_attack_drones", [])
    
    # Find the decision record
    decision_record = None
    for key, decision in compute.strike_decisions.items():
        if decision["decision_id"] == decision_id:
            decision_record = decision
            break
    
    if not decision_record:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")
    
    relay = compute.relay_targeting_to_attack(decision_record, assigned_drones)
    
    if relay.get("status") == "relay-rejected":
        raise HTTPException(status_code=400, detail=relay.get("reason"))
    
    return {
        "relay_id": relay["relay_id"],
        "target_id": relay["target_id"],
        "assigned_attack_drones": relay["assigned_attack_drones"],
        "status": relay["status"]
    }


@app.get("/api/compute/{compute_id}/status")
async def compute_get_status(compute_id: str):
    """Get compute drone status and processing queue."""
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    status = compute.generate_status_report()
    
    return {
        **status,
        "targets_high_threat": len([t for t in compute.target_database.values() if t.get("threat_level", 0) >= 4])
    }


@app.get("/api/compute/{compute_id}/targets")
async def compute_get_targets(compute_id: str, threat_filter: str = None):
    """Get all tracked targets with optional threat level filtering."""
    if compute_id not in compute_drones:
        raise HTTPException(status_code=404, detail=f"Compute drone {compute_id} not found")
    
    compute = compute_drones[compute_id]
    
    threat_level = None
    if threat_filter:
        try:
            threat_level = ThreatLevel[threat_filter.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid threat level: {threat_filter}")
    
    targets = compute.get_target_summary(threat_level_filter=threat_level)
    
    return {
        "compute_drone_id": compute_id,
        "targets_count": len(targets),
        "threat_filter": threat_filter,
        "targets": targets
    }


if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", 8000))
    reload = os.getenv("FASTAPI_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
    )
