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
from pathlib import Path
from typing import Dict, Set
from datetime import datetime
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
BASE_STATION_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_STATION_DIR / ".env")

# Import our core modules (once they're built by Richard & Giulia)
from core.ai_bridge import process_audio_command, process_voice_command, create_confirmation_text
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


def _humanize_location(location: str | None) -> str | None:
    if not location:
        return None
    return location.replace("_", " ").title()


def _to_swarm_intent(parsed_command: Dict, transcribed_text: str) -> Dict:
    goal = parsed_command.get("goal", "NO_OP")
    target_location = parsed_command.get("target_location")
    avoid_location = parsed_command.get("avoid_location")

    return {
        "intent": parsed_command.get("intent", "swarm_command"),
        "target": _humanize_location(target_location or avoid_location),
        "action": goal,
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
    }


def _build_active_nodes(gossip_result: Dict) -> list[str]:
    return [
        node["id"]
        for node in gossip_result.get("nodes", [])
        if node.get("status") == "active"
    ]


async def _dispatch_command(transcribed_text: str, parsed_command: Dict) -> Dict:
    confirmation_text = create_confirmation_text(parsed_command)

    if parsed_command.get("goal") == "NO_OP":
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
    gossip_result = swarm.calculate_gossip_path(_to_swarm_intent(parsed_command, transcribed_text))
    active_nodes = _build_active_nodes(gossip_result)

    event_payload = {
        "event": "gossip_update",
        "status": "propagating",
        "message": "Command executing via gossip protocol",
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
        "confirmation_text": confirmation_text,
        "data": gossip_result,
        "nodes": gossip_result.get("nodes", []),
        "edges": gossip_result.get("edges", []),
        "active_nodes": active_nodes,
    }

    await manager.broadcast(event_payload)
    return event_payload


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
        raise HTTPException(status_code=400, detail="No transcription provided")

    parsed_command = process_voice_command(transcribed_text)
    return await _dispatch_command(transcribed_text, parsed_command)


@app.post("/api/transcribe-command")
async def transcribe_command(audio: UploadFile = File(...)):
    """
    Process recorded microphone audio from the React UI.

    Flow:
    1. Upload audio blob from browser
    2. Send to ElevenLabs Speech-to-Text
    3. Parse transcript with ai_bridge.process_voice_command()
    4. Dispatch resulting command through the swarm pipeline
    """
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

    return await _dispatch_command(
        command_result["transcribed_text"],
        command_result["parsed_command"],
    )


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
        "active_nodes": _build_active_nodes(state),
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
