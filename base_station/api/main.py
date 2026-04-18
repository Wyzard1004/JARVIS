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
import asyncio
import json
from typing import Dict, List, Set
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
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


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
    
    if not transcribed_text:
        return {"error": "No transcription provided"}
    
    # TODO: Integrate ai_bridge.process_voice_command(transcribed_text)
    # For now, use a mock intent that works with swarm_logic
    parsed_intent = {
        "intent": "swarm",
        "target": "Grid Alpha",
        "action": "RED_ALERT",
        "transcribed_text": transcribed_text
    }
    
    # Integrate swarm_logic.calculate_gossip_path(parsed_intent)
    swarm = get_swarm()
    gossip_result = swarm.calculate_gossip_path(parsed_intent)
    
    # TODO: Publish to MQTT via mqtt_client
    # await mqtt_publisher.publish("swarm/command", json.dumps(gossip_result))
    
    # Broadcast update to all connected React clients
    await manager.broadcast({
        "event": "gossip_update",
        "status": "propagating",
        "data": gossip_result,
        "transcribed_text": transcribed_text
    })
    
    return {
        "status": "propagating",
        "message": "Command executing via gossip protocol",
        "gossip_data": gossip_result
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
        "propagation_order": state.get("propagation_order", []),
        "status": state.get("status", "idle"),
        "timestamp": datetime.now().isoformat()
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
