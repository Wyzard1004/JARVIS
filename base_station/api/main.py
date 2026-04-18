"""
JARVIS Base Station - FastAPI Main Application
Full-Stack Integration Hub (Section 4.0.0)

This is the nervous system of JARVIS:
- Integrates ai_bridge.py (Richard's LLM & Voice)
- Integrates swarm_logic.py (Giulia's Gossip Protocol)
- Publishes to MQTT for hardware (ESP32s)
- Streams WebSocket updates to React UI
"""

import os
from typing import Dict, Set
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Import our core modules (once they're built by Richard & Giulia)
# from core.ai_bridge import AIBridge
from core.swarm_logic import get_swarm
# from core.mqtt_client import MQTTPublisher

# Initialize FastAPI app
app = FastAPI(
    title="JARVIS Base Station",
    description="Voice-activated Swarm Coordinator for DDIL Environments",
    version="0.0.1"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to localhost in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STATE MANAGEMENT
# ============================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time UI updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict):
        """Send a message to all connected clients"""
        stale_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


manager = ConnectionManager()


def mock_parse_intent(payload: Dict) -> Dict:
    """Small placeholder parser until ai_bridge.py is wired in."""
    transcribed_text = (payload.get("transcribed_text") or "").strip()
    normalized = transcribed_text.lower()
    origin = payload.get("origin") or payload.get("operator_node")
    if not origin:
        if any(token in normalized for token in {"operator two", "operator 2", "soldier two", "soldier 2"}):
            origin = "soldier-2"
        else:
            origin = "soldier-1"

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
        elif any(token in normalized for token in {"scan", "search", "sweep"}):
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
    }


# ============================================================
# HEALTH CHECK ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Verify the Base Station is online"""
    return {
        "status": "operational",
        "subsystems": {
            "api": "online",
            # "mqtt": "checking...",
            # "ollama": "checking...",
            # "elevenlabs": "checking...",
        }
    }


# ============================================================
# WEBSOCKET SWARM UPDATES (4.1.3)
# ============================================================

@app.websocket("/ws/swarm")
async def websocket_swarm_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket connection for swarm state updates.
    
    The React UI connects here to receive:
    - Gossip propagation status
    - Node positions and colors
    - Command confirmations
    """
    await manager.connect(websocket)
    swarm = get_swarm()
    initial_state = swarm.get_state()
    await websocket.send_json({
        "event": "swarm_state",
        **initial_state,
    })
    try:
        while True:
            data = await websocket.receive_text()
            # Parse incoming commands from React
            print(f"[WebSocket] Received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from swarm WebSocket")


# ============================================================
# VOICE COMMAND ENDPOINT (4.1.1 + 4.1.2)
# ============================================================

@app.post("/api/voice-command")
async def voice_command(payload: Dict):
    """
    Process a voice command from the React UI.
    
    Expected payload:
    {
        "transcribed_text": "JARVIS, re-route swarm to Grid Alpha"
    }
    
    Flow:
    1. Pass to ai_bridge.process_voice_command() (Richard's module)
    2. Get back strict JSON with intent, target, action
    3. Pass to swarm_logic.calculate_gossip_path() (Giulia's module)
    4. Publish to MQTT broker via mqtt_client (Sebastian's config)
    5. Broadcast to React UI via WebSocket
    """
    transcribed_text = payload.get("transcribed_text", "")
    direct_intent = payload.get("target_location") or payload.get("target")
    if not transcribed_text and not direct_intent:
        return {"error": "No transcription or intent payload provided"}

    parsed_intent = mock_parse_intent(payload)
    swarm = get_swarm()
    algorithm = parsed_intent.get("consensus_algorithm", "gossip").lower()
    if algorithm in {"raft", "tcp", "tcp-raft", "raft-consensus", "leader"}:
        consensus_result = swarm.calculate_raft_path(parsed_intent)
    else:
        consensus_result = swarm.calculate_gossip_path(parsed_intent)
    
    # TODO: Publish to MQTT via mqtt_client
    # await mqtt_publisher.publish("swarm/command", json.dumps(gossip_result))
    
    # Broadcast update to all connected React clients
    await manager.broadcast({
        "event": "gossip_update",
        "status": consensus_result.get("status", "propagating"),
        "algorithm": consensus_result.get("algorithm"),
        "target_location": consensus_result.get("target_location"),
        "target_x": consensus_result.get("target_x", 0),
        "target_y": consensus_result.get("target_y", 0),
        "control_node": consensus_result.get("search_state", {}).get("control_node"),
        "nodes": consensus_result.get("nodes", []),
        "edges": consensus_result.get("edges", []),
        "active_nodes": consensus_result.get("active_nodes", []),
        "propagation_order": consensus_result.get("propagation_order", []),
        "total_propagation_ms": consensus_result.get("total_propagation_ms", 0),
        "search_state": consensus_result.get("search_state", {}),
        "target_tasks": consensus_result.get("search_state", {}).get("target_tasks", []),
        "engagements": consensus_result.get("search_state", {}).get("engagements", []),
        "object_reports": consensus_result.get("object_reports", []),
        "delivery_summary": consensus_result.get("delivery_summary", {}),
        "benchmark": consensus_result.get("benchmark", {}),
        "data": consensus_result,
        "transcribed_text": transcribed_text
    })
    
    return {
        "status": consensus_result.get("status", "propagating"),
        "message": "Command executing via swarm consensus protocol",
        "consensus_data": consensus_result
    }


# ============================================================
# SWARM STATE ENDPOINT
# ============================================================

@app.get("/api/swarm-state")
async def get_swarm_state():
    """
    Fetch the current state of the swarm.
    
    Returns node positions, active agents, gossip status, etc.
    Used by React to initialize the force-graph on load.
    """
    swarm = get_swarm()
    state = swarm.get_state()
    
    return {
        "nodes": state.get("nodes", []),
        "edges": state.get("edges", []),
        "active_nodes": state.get("active_nodes", []),
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
        "timestamp": state.get("timestamp", datetime.now().isoformat())
    }


# ============================================================
# STARTUP & SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Initialize connections when the server starts"""
    print("[STARTUP] JARVIS Base Station initializing...")
    swarm = get_swarm()
    print(f"[STARTUP] Swarm topology initialized: {len(swarm.graph.nodes)} nodes")
    # TODO: Initialize MQTT client
    # TODO: Initialize AI Bridge
    # TODO: Connect to Ollama
    print("[STARTUP] All systems nominal. Awaiting commands.")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on server shutdown"""
    print("[SHUTDOWN] JARVIS Base Station closing...")
    # TODO: Close MQTT connections
    # TODO: Clean up WebSocket connections


# ============================================================
# DEVELOPMENT SERVER
# ============================================================

if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", 8000))
    reload = os.getenv("FASTAPI_RELOAD", "true").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )
