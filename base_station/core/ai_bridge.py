from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_STATION_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


DEFAULT_GOALS = [
    "MOVE_TO",
    "ATTACK_AREA",
    "AVOID_AREA",
    "HOLD_POSITION",
    "SCAN_AREA",
    "ABORT",
    "NO_OP",
]

DEFAULT_LOCATIONS = [
    # Coarse-grained sectors
    "GRID_ALPHA",
    "GRID_BRAVO",
    "GRID_CHARLIE",
    # Fine-grained numbered sectors (Alpha 1-3, Bravo 1-3, Charlie 1-3)
    "GRID_ALPHA_1",
    "GRID_ALPHA_2",
    "GRID_ALPHA_3",
    "GRID_BRAVO_1",
    "GRID_BRAVO_2",
    "GRID_BRAVO_3",
    "GRID_CHARLIE_1",
    "GRID_CHARLIE_2",
    "GRID_CHARLIE_3",
]

SCHEMA_VERSION = "1.0"
ELEVENLABS_STT_MODEL = "scribe_v2"


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    values = [value.strip().upper() for value in raw.split(",") if value.strip()]
    return values or default


def _ollama_api_base() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return base


def _build_schema() -> dict[str, Any]:
    nullable_locations = [{"type": "string", "enum": ALLOWED_LOCATIONS}, {"type": "null"}]
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string"},
            "intent": {"type": "string", "enum": ["swarm_command"]},
            "goal": {"type": "string", "enum": ALLOWED_GOALS},
            "target_location": {"anyOf": nullable_locations},
            "avoid_location": {"anyOf": nullable_locations},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "schema_version",
            "intent",
            "goal",
            "target_location",
            "avoid_location",
            "confidence",
        ],
    }


def _canonicalize_location(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    if normalized in ALLOWED_LOCATIONS:
        return normalized
    return None


def _goal_requires_target(goal: str) -> bool:
    return goal in {"MOVE_TO", "ATTACK_AREA", "SCAN_AREA"}


def _goal_requires_avoid(goal: str) -> bool:
    return goal == "AVOID_AREA"


def _location_aliases() -> dict[str, str]:
    """Build comprehensive location aliases including number word variants."""
    aliases: dict[str, str] = {}
    
    # Map digits to their word forms
    digit_to_word = {
        "1": "one",
        "2": "two",
        "3": "three"
    }
    
    for canonical in ALLOWED_LOCATIONS:
        # Standard aliases
        human = canonical.lower().replace("_", " ")
        aliases[human] = canonical
        aliases[canonical.lower()] = canonical
        
        # Compact versions (remove "grid " and "sector " prefixes)
        compact = human
        if compact.startswith("grid "):
            compact = compact[5:]  # Remove "grid " prefix
        if compact.startswith("sector "):
            compact = compact[7:]  # Remove "sector " prefix
        
        aliases[compact] = canonical
        
        # Add variants with dashes and underscores
        compact_dash = compact.replace(" ", "-")
        compact_underscore = compact.replace(" ", "_")
        aliases[compact_dash] = canonical
        aliases[compact_underscore] = canonical
        
        # For numbered locations, add digit↔word variants
        # E.g., "bravo 2" ↔ "bravo two"
        has_digit = any(digit in compact for digit in "123")
        
        if has_digit:
            # Replace digits with words: "bravo 2" → "bravo two"
            for digit, word in digit_to_word.items():
                if digit in compact:
                    variant_word = compact.replace(digit, word)
                    aliases[variant_word] = canonical
                    # Also with separators
                    aliases[variant_word.replace(" ", "-")] = canonical
                    aliases[variant_word.replace(" ", "_")] = canonical
    
    return aliases


def _find_location_in_text(text: str) -> str | None:
    """Find location in text, preferring longer/more specific matches."""
    lowered = text.lower()
    
    # Find ALL matching aliases and return the longest one
    # (prefer "bravo 2" over "bravo")
    best_match = None
    best_length = 0
    
    for alias, canonical in LOCATION_ALIASES.items():
        if alias and alias in lowered:
            # Prefer longer aliases to avoid partial matches
            if len(alias) > best_length:
                best_match = canonical
                best_length = len(alias)
    
    return best_match


def build_safe_fallback() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "intent": "swarm_command",
        "goal": "NO_OP",
        "target_location": None,
        "avoid_location": None,
        "confidence": 0.0,
    }


def normalize_command(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "schema_version": str(payload.get("schema_version") or SCHEMA_VERSION),
        "intent": "swarm_command",
        "goal": str(payload.get("goal") or "NO_OP").upper(),
        "target_location": _canonicalize_location(payload.get("target_location")),
        "avoid_location": _canonicalize_location(payload.get("avoid_location")),
        "confidence": payload.get("confidence", 0.0),
    }

    try:
        normalized["confidence"] = max(0.0, min(1.0, float(normalized["confidence"])))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.0

    return normalized


def validate_command(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_command(payload)

    if normalized["goal"] not in ALLOWED_GOALS:
        return build_safe_fallback()

    if _goal_requires_target(normalized["goal"]) and not normalized["target_location"]:
        return build_safe_fallback()

    if _goal_requires_avoid(normalized["goal"]) and not normalized["avoid_location"]:
        return build_safe_fallback()

    if normalized["goal"] in {"ABORT", "HOLD_POSITION", "NO_OP"}:
        normalized["target_location"] = None
        normalized["avoid_location"] = None

    return normalized


def parse_with_rules(text: str) -> dict[str, Any] | None:
    lowered = text.lower().strip()
    if not lowered:
        return None

    location = _find_location_in_text(lowered)

    if any(term in lowered for term in ["abort", "cancel mission", "stop mission", "stand down"]):
        return validate_command(
            {
                "goal": "ABORT",
                "confidence": 0.99,
            }
        )

    if any(term in lowered for term in ["hold position", "stay put", "hold", "wait there"]):
        return validate_command(
            {
                "goal": "HOLD_POSITION",
                "confidence": 0.97,
            }
        )

    if any(
        term in lowered
        for term in [
            "avoid",
            "do not enter",
            "don't enter",
            "steer clear",
            "keep away from",
            "stay away from",
        ]
    ):
        if not location:
            return None
        return validate_command(
            {
                "goal": "AVOID_AREA",
                "avoid_location": location,
                "confidence": 0.94,
            }
        )

    if any(term in lowered for term in ["attack", "engage", "strike"]):
        if not location:
            return None
        return validate_command(
            {
                "goal": "ATTACK_AREA",
                "target_location": location,
                "confidence": 0.93,
            }
        )

    if any(term in lowered for term in ["scan", "search", "recon", "take a look at", "check out", "inspect"]):
        if not location:
            return None
        return validate_command(
            {
                "goal": "SCAN_AREA",
                "target_location": location,
                "confidence": 0.92,
            }
        )

    if any(
        term in lowered
        for term in [
            "move",
            "go to",
            "push",
            "reroute",
            "redeploy",
            "deploy",
            "send",
            "head to",
            "put the team on",
            "put the swarm on",
        ]
    ):
        if not location:
            return None
        return validate_command(
            {
                "goal": "MOVE_TO",
                "target_location": location,
                "confidence": 0.91,
            }
        )

    return None


def _ollama_messages(text: str) -> list[dict[str, str]]:
    schema_text = json.dumps(COMMAND_SCHEMA, indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You convert operator speech into command JSON for a drone swarm. "
                "Return only JSON that fits the provided schema. "
                f"Allowed goals: {', '.join(ALLOWED_GOALS)}. "
                f"Allowed locations: {', '.join(ALLOWED_LOCATIONS)}. "
                "If the request is unclear or unsafe, return goal NO_OP with null locations."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Schema:\n{schema_text}\n\n"
                f"Operator text: {text}\n"
                "Return only one JSON object."
            ),
        },
    ]


def parse_with_ollama(text: str, timeout: int = 20) -> dict[str, Any] | None:
    model = os.getenv("OLLAMA_MODEL", "").strip()
    if not model:
        return None

    response = requests.post(
        f"{_ollama_api_base()}/chat",
        json={
            "model": model,
            "messages": _ollama_messages(text),
            "stream": False,
            "format": COMMAND_SCHEMA,
            "options": {"temperature": 0},
        },
        timeout=timeout,
    )
    response.raise_for_status()

    body = response.json()
    content = body.get("message", {}).get("content", "")
    if not content:
        return None

    parsed = json.loads(content)
    return validate_command(parsed)


def process_voice_command(transcribed_text: str) -> dict[str, Any]:
    text = transcribed_text.strip()
    if not text:
        return build_safe_fallback()

    parser_mode = os.getenv("JARVIS_PARSER_MODE", "hybrid").strip().lower()

    if parser_mode in {"rules", "hybrid"}:
        rule_result = parse_with_rules(text)
        if rule_result:
            return rule_result

    if parser_mode in {"ollama", "hybrid"}:
        try:
            ollama_result = parse_with_ollama(text)
        except (requests.RequestException, json.JSONDecodeError, ValueError):
            ollama_result = None

        if ollama_result:
            return ollama_result

    return build_safe_fallback()


def transcribe_audio_with_elevenlabs(
    audio_bytes: bytes,
    filename: str = "recording.webm",
    content_type: str = "audio/webm",
    timeout: int = 60,
) -> dict[str, Any]:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing ElevenLabs credentials. Set ELEVENLABS_API_KEY.")

    response = requests.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": api_key},
        data={"model_id": ELEVENLABS_STT_MODEL},
        files={"file": (filename, audio_bytes, content_type)},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def process_audio_command(
    audio_bytes: bytes,
    filename: str = "recording.webm",
    content_type: str = "audio/webm",
) -> dict[str, Any]:
    transcript_result = transcribe_audio_with_elevenlabs(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
    )
    transcribed_text = str(transcript_result.get("text") or "").strip()
    parsed_command = process_voice_command(transcribed_text)

    return {
        "transcribed_text": transcribed_text,
        "parsed_command": parsed_command,
        "confirmation_text": create_confirmation_text(parsed_command),
        "transcript_result": transcript_result,
    }


def create_confirmation_text(command: dict[str, Any]) -> str:
    goal = command.get("goal")
    target = command.get("target_location")
    avoid = command.get("avoid_location")

    if goal == "MOVE_TO" and target:
        return f"Moving swarm to {target}."
    if goal == "ATTACK_AREA" and target:
        return f"Attacking area {target}."
    if goal == "AVOID_AREA" and avoid:
        return f"Avoiding area {avoid}."
    if goal == "SCAN_AREA" and target:
        return f"Scanning area {target}."
    if goal == "HOLD_POSITION":
        return "Holding position."
    if goal == "ABORT":
        return "Mission aborted."
    return "No action taken."


def synthesize_confirmation(text: str, output_path: str | Path | None = None, timeout: int = 20) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()

    if not api_key or not voice_id:
        raise ValueError("Missing ElevenLabs credentials. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "output_format": "mp3_44100_128",
        },
        timeout=timeout,
    )
    response.raise_for_status()

    audio_bytes = response.content
    if output_path:
        Path(output_path).write_bytes(audio_bytes)

    return audio_bytes


def check_ollama_connection(timeout: int = 5) -> dict[str, Any]:
    try:
        response = requests.get(f"{_ollama_api_base()}/tags", timeout=timeout)
        response.raise_for_status()
        models = [item.get("name") for item in response.json().get("models", [])]
        return {"ok": True, "models": models}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def check_elevenlabs_connection(timeout: int = 10) -> dict[str, Any]:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "ELEVENLABS_API_KEY is not set."}

    try:
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
            timeout=timeout,
        )
        response.raise_for_status()
        voices = response.json().get("voices", [])
        return {"ok": True, "voice_count": len(voices)}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


ALLOWED_GOALS = _parse_csv_env("JARVIS_ALLOWED_GOALS", DEFAULT_GOALS)
ALLOWED_LOCATIONS = _parse_csv_env("JARVIS_ALLOWED_LOCATIONS", DEFAULT_LOCATIONS)
LOCATION_ALIASES = _location_aliases()
COMMAND_SCHEMA = _build_schema()
