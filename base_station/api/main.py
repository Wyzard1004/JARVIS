"""
JARVIS Base Station - FastAPI Main Application
Full-Stack Integration Hub (Section 4.0.0)

This is the nervous system of JARVIS:
- Integrates ai_bridge.py (Richard's LLM & Voice)
- Integrates swarm_logic.py (Giulia's Gossip Protocol)
- Publishes to MQTT for hardware (ESP32s)
- Streams WebSocket updates to React UI
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.ai_bridge import create_confirmation_text, process_audio_command, process_voice_command
from core.swarm_logic import get_swarm


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_STATION_DIR / ".env")


app = FastAPI(
    title="JARVIS Base Station",
    description="Voice-activated Swarm Coordinator for DDIL Environments",
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


def _build_swarm_event(consensus_result: Dict, transcribed_text: str, parsed_command: Dict | None, confirmation_text: str | None) -> Dict:
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
        "search_state": search_state,
        "target_tasks": search_state.get("target_tasks", []),
        "engagements": search_state.get("engagements", []),
        "object_reports": consensus_result.get("object_reports", []),
        "delivery_summary": consensus_result.get("delivery_summary", {}),
        "benchmark": consensus_result.get("benchmark", {}),
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
        "confirmation_text": confirmation_text,
        "data": consensus_result,
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

    event_payload = _build_swarm_event(
        consensus_result,
        transcribed_text,
        parsed_command,
        confirmation_text,
    )
    await manager.broadcast(event_payload)
    return event_payload


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
    """Real-time WebSocket connection for swarm state updates."""
    print(f"[WebSocket] Client connecting from {websocket.client}")
    try:
        await manager.connect(websocket)
        print("[WebSocket] Client connected successfully")
        
        # Send welcome message to confirm connection
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to JARVIS Base Station",
            "timestamp": datetime.now().isoformat()
        })
        
        # Send initial swarm topology
        swarm = get_swarm()
        initial_state = swarm.get_state()
        await websocket.send_json({
            "event": "swarm_state",
            "data": initial_state,
            "nodes": initial_state.get("nodes", []),
            "edges": initial_state.get("edges", []),
            "timestamp": datetime.now().isoformat()
        })
        print("[WebSocket] Sent initial swarm topology to client")
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    print(f"[WebSocket] Received: {message}")
                except json.JSONDecodeError:
                    print(f"[WebSocket] Invalid JSON: {data}")
            except WebSocketDisconnect:
                print("[WebSocket] Client disconnected gracefully")
                break
            
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected during handshake or message handling")
    except Exception as e:
        print(f"[WebSocket ERROR] {type(e).__name__}: {e}")
    
    finally:
        manager.disconnect(websocket)
        print(f"[WebSocket] Cleaned up connection for {websocket.client}")


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
