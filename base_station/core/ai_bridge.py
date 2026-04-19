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
    "REVIEW_REPORTS",
    "LOITER",
    "MARK",
    "EXECUTE",
    "STANDBY",
    "DISREGARD",
    "ABORT",
    "NO_OP",
]

DEFAULT_CALLSIGNS = [
    "JARVIS",
]

DISPLAY_SECTORS = [
    "ALPHA",
    "BRAVO",
    "CHARLIE",
    "DELTA",
    "ECHO",
    "FOXTROT",
    "GOLF",
    "HOTEL",
]

DISPLAY_NUMBER_WORDS = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
}


def _default_locations() -> list[str]:
    locations: list[str] = []
    for sector in DISPLAY_SECTORS:
        locations.append(f"GRID_{sector}")
    for sector in DISPLAY_SECTORS:
        for column in range(1, 9):
            locations.append(f"GRID_{sector}_{column}")
    return locations


DEFAULT_LOCATIONS = _default_locations()

SCHEMA_VERSION = "2.0"
ELEVENLABS_STT_MODEL = "scribe_v2"
EXECUTION_STATES = ["NONE", "PENDING_EXECUTE", "EXECUTE_REQUESTED", "CANCELED", "EXECUTED"]
TERMINAL_PROWORDS = ["OVER", "OUT"]


def _parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    values = [value.strip().upper() for value in raw.split(",") if value.strip()]
    if not values:
        return default

    # Preserve new built-in schema values even if an older .env file still
    # carries a pre-upgrade allowlist.
    merged: list[str] = []
    for value in values + default:
        if value not in merged:
            merged.append(value)
    return merged


def _ollama_api_base() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return base


def _default_callsign() -> str:
    return ALLOWED_CALLSIGNS[0] if ALLOWED_CALLSIGNS else DEFAULT_CALLSIGNS[0]


def _location_detail_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["named_sector", "named_location"]},
            "canonical": {"type": "string"},
            "label": {"type": "string"},
            "sector": {"type": "string"},
            "subsector": {"type": "integer"},
        },
        "required": ["type", "canonical", "label"],
        "additionalProperties": True,
    }


def _build_schema() -> dict[str, Any]:
    nullable_locations = [{"type": "string", "enum": ALLOWED_LOCATIONS}, {"type": "null"}]
    nullable_location_details = [_location_detail_schema(), {"type": "null"}]
    nullable_prowords = [{"type": "string", "enum": TERMINAL_PROWORDS}, {"type": "null"}]
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string"},
            "callsign": {"type": "string", "enum": ALLOWED_CALLSIGNS},
            "intent": {"type": "string", "enum": ["swarm_command"]},
            "goal": {"type": "string", "enum": ALLOWED_GOALS},
            "target_location": {"anyOf": nullable_locations},
            "avoid_location": {"anyOf": nullable_locations},
            "target_location_detail": {"anyOf": nullable_location_details},
            "avoid_location_detail": {"anyOf": nullable_location_details},
            "patrol_end_location": {"anyOf": nullable_locations},
            "patrol_end_location_detail": {"anyOf": nullable_location_details},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "confirmation_required": {"type": "boolean"},
            "execution_state": {"type": "string", "enum": EXECUTION_STATES},
            "terminal_proword": {"anyOf": nullable_prowords},
        },
        "required": [
            "schema_version",
            "callsign",
            "intent",
            "goal",
            "target_location",
            "avoid_location",
            "confidence",
            "confirmation_required",
            "execution_state",
        ],
        "additionalProperties": True,
    }


def _canonicalize_location(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    if normalized in ALLOWED_LOCATIONS:
        return normalized
    return None


def _canonicalize_callsign(value: str | None) -> str:
    if not value:
        return _default_callsign()
    normalized = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    if normalized in ALLOWED_CALLSIGNS:
        return normalized
    return _default_callsign()


def _build_location_detail(canonical: str | None) -> dict[str, Any] | None:
    if not canonical:
        return None

    parts = canonical.split("_")
    detail: dict[str, Any] = {
        "type": "named_location",
        "canonical": canonical,
        "label": canonical.replace("_", " ").title(),
    }

    if len(parts) >= 2 and parts[0] == "GRID":
        detail["type"] = "named_sector"
        detail["sector"] = parts[1]
        if len(parts) >= 3:
            try:
                detail["subsector"] = int(parts[2])
            except ValueError:
                pass

    return detail


def _goal_requires_target(goal: str) -> bool:
    return goal in {"MOVE_TO", "ATTACK_AREA", "SCAN_AREA", "LOITER", "MARK"}


def _goal_requires_avoid(goal: str) -> bool:
    return goal == "AVOID_AREA"


def _location_aliases() -> dict[str, str]:
    """Build comprehensive location aliases including number word variants."""
    aliases: dict[str, str] = {}

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
        aliases[f"sector {compact}"] = canonical

        # Add variants with dashes and underscores
        compact_dash = compact.replace(" ", "-")
        compact_underscore = compact.replace(" ", "_")
        aliases[compact_dash] = canonical
        aliases[compact_underscore] = canonical
        aliases[f"sector-{compact_dash}"] = canonical
        aliases[f"sector_{compact_underscore}"] = canonical

        # For numbered locations, add digit↔word variants
        # E.g., "bravo 2" ↔ "bravo two"
        has_digit = any(digit in compact for digit in DISPLAY_NUMBER_WORDS)

        if has_digit:
            for digit, word in DISPLAY_NUMBER_WORDS.items():
                if digit in compact:
                    variant_word = compact.replace(digit, word)
                    aliases[variant_word] = canonical
                    aliases[f"sector {variant_word}"] = canonical
                    aliases[variant_word.replace(" ", "-")] = canonical
                    aliases[variant_word.replace(" ", "_")] = canonical

    return aliases


def _find_location_mentions(text: str) -> list[str]:
    """Find non-overlapping location mentions in the order they appear."""
    lowered = text.lower()
    matches: list[tuple[int, int, str]] = []

    for alias, canonical in sorted(LOCATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if not alias:
            continue

        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        for match in re.finditer(pattern, lowered):
            start, end = match.span()
            overlaps = any(not (end <= existing_start or start >= existing_end) for existing_start, existing_end, _ in matches)
            if overlaps:
                continue
            matches.append((start, end, canonical))

    ordered_mentions: list[str] = []
    for _, _, canonical in sorted(matches, key=lambda item: item[0]):
        if not ordered_mentions or ordered_mentions[-1] != canonical:
            ordered_mentions.append(canonical)
    return ordered_mentions


def _find_location_in_text(text: str) -> str | None:
    """Find the first resolved location mention in the utterance."""
    mentions = _find_location_mentions(text)
    return mentions[0] if mentions else None


def _extract_callsign(text: str) -> tuple[str, str]:
    stripped = text.strip()
    for callsign in ALLOWED_CALLSIGNS:
        pattern = rf"^\s*{re.escape(callsign.lower())}\b[\s,:\-]*"
        if re.match(pattern, stripped.lower()):
            remaining = re.sub(pattern, "", stripped, count=1, flags=re.IGNORECASE)
            return callsign, remaining.strip()
    return _default_callsign(), stripped


def _extract_terminal_proword(text: str) -> tuple[str | None, str]:
    stripped = text.strip()
    lowered = stripped.lower()
    for proword in ("over", "out"):
        if re.search(rf"\b{proword}\b[\s.!?]*$", lowered):
            remaining = re.sub(rf"\b{proword}\b[\s.!?]*$", "", stripped, flags=re.IGNORECASE).strip(" ,.-")
            return proword.upper(), remaining.strip()
    return None, stripped


def build_safe_fallback() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "callsign": _default_callsign(),
        "intent": "swarm_command",
        "goal": "NO_OP",
        "target_location": None,
        "avoid_location": None,
        "target_location_detail": None,
        "avoid_location_detail": None,
        "patrol_end_location": None,
        "patrol_end_location_detail": None,
        "confidence": 0.0,
        "confirmation_required": False,
        "execution_state": "NONE",
        "terminal_proword": None,
    }


def normalize_command(payload: dict[str, Any]) -> dict[str, Any]:
    target_location = _canonicalize_location(payload.get("target_location"))
    avoid_location = _canonicalize_location(payload.get("avoid_location"))
    patrol_end_location = _canonicalize_location(
        payload.get("patrol_end_location") or payload.get("target_location_end")
    )
    normalized = {
        "schema_version": str(payload.get("schema_version") or SCHEMA_VERSION),
        "callsign": _canonicalize_callsign(payload.get("callsign")),
        "intent": "swarm_command",
        "goal": str(payload.get("goal") or "NO_OP").upper(),
        "target_location": target_location,
        "avoid_location": avoid_location,
        "target_location_detail": payload.get("target_location_detail") or _build_location_detail(target_location),
        "avoid_location_detail": payload.get("avoid_location_detail") or _build_location_detail(avoid_location),
        "patrol_end_location": patrol_end_location,
        "patrol_end_location_detail": payload.get("patrol_end_location_detail") or _build_location_detail(patrol_end_location),
        "confidence": payload.get("confidence", 0.0),
        "confirmation_required": bool(payload.get("confirmation_required", False)),
        "execution_state": str(payload.get("execution_state") or "NONE").upper(),
        "terminal_proword": None,
    }

    try:
        normalized["confidence"] = max(0.0, min(1.0, float(normalized["confidence"])))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.0

    terminal_proword = payload.get("terminal_proword")
    if isinstance(terminal_proword, str):
        normalized_proword = terminal_proword.upper().strip()
        if normalized_proword in TERMINAL_PROWORDS:
            normalized["terminal_proword"] = normalized_proword

    if normalized["execution_state"] not in EXECUTION_STATES:
        normalized["execution_state"] = "NONE"

    return normalized


def validate_command(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_command(payload)

    if normalized["goal"] not in ALLOWED_GOALS:
        return build_safe_fallback()

    if _goal_requires_target(normalized["goal"]) and not normalized["target_location"]:
        return build_safe_fallback()

    if _goal_requires_avoid(normalized["goal"]) and not normalized["avoid_location"]:
        return build_safe_fallback()

    if normalized["goal"] in {"ABORT", "HOLD_POSITION", "STANDBY", "EXECUTE", "DISREGARD", "REVIEW_REPORTS", "NO_OP"}:
        normalized["target_location"] = None
        normalized["avoid_location"] = None
        normalized["target_location_detail"] = None
        normalized["avoid_location_detail"] = None
        normalized["patrol_end_location"] = None
        normalized["patrol_end_location_detail"] = None

    if normalized["patrol_end_location"] and normalized["goal"] != "SCAN_AREA":
        normalized["patrol_end_location"] = None
        normalized["patrol_end_location_detail"] = None

    if normalized["patrol_end_location"] and not normalized["target_location"]:
        return build_safe_fallback()

    if normalized["goal"] == "ATTACK_AREA":
        normalized["confirmation_required"] = True
        normalized["execution_state"] = "PENDING_EXECUTE"
    elif normalized["goal"] == "EXECUTE":
        normalized["confirmation_required"] = False
        normalized["execution_state"] = "EXECUTE_REQUESTED"
    elif normalized["goal"] == "DISREGARD":
        normalized["confirmation_required"] = False
        normalized["execution_state"] = "CANCELED"
    elif normalized["goal"] == "NO_OP":
        normalized["confirmation_required"] = False
        normalized["execution_state"] = "NONE"
    else:
        normalized["confirmation_required"] = bool(normalized.get("confirmation_required"))
        if normalized["execution_state"] not in EXECUTION_STATES:
            normalized["execution_state"] = "NONE"

    return normalized


def parse_with_rules(text: str) -> dict[str, Any] | None:
    callsign, without_callsign = _extract_callsign(text)
    terminal_proword, body = _extract_terminal_proword(without_callsign)
    lowered = body.lower().strip()
    if not lowered:
        return None

    location_mentions = _find_location_mentions(lowered)
    location = location_mentions[0] if location_mentions else None
    base_payload = {
        "callsign": callsign,
        "terminal_proword": terminal_proword,
    }

    if any(
        term in lowered
        for term in [
            "abort",
            "cancel mission",
            "stop mission",
            "stand down",
            "end mission",
            "end attack",
            "end attack mission",
            "terminate attack",
            "terminate attack mission",
            "cancel attack mission",
        ]
    ):
        return validate_command(
            {
                **base_payload,
                "goal": "ABORT",
                "confidence": 0.99,
            }
        )

    if any(
        term in lowered
        for term in [
            "review reports",
            "review report",
            "process reports",
            "process report",
            "mission report",
            "mission reports",
            "status report",
            "report status",
        ]
    ):
        return validate_command(
            {
                **base_payload,
                "goal": "REVIEW_REPORTS",
                "confidence": 0.97,
            }
        )

    if any(term in lowered for term in ["execute", "wilco execute"]):
        return validate_command(
            {
                **base_payload,
                "goal": "EXECUTE",
                "confidence": 0.99,
            }
        )

    if any(term in lowered for term in ["disregard", "disregard last", "cancel last", "cancel command"]):
        return validate_command(
            {
                **base_payload,
                "goal": "DISREGARD",
                "confidence": 0.98,
            }
        )

    if any(term in lowered for term in ["standby", "stand by"]):
        return validate_command(
            {
                **base_payload,
                "goal": "STANDBY",
                "confidence": 0.97,
            }
        )

    if any(term in lowered for term in ["loiter", "anchor", "orbit"]):
        if not location:
            return None
        return validate_command(
            {
                **base_payload,
                "goal": "LOITER",
                "target_location": location,
                "confidence": 0.93,
            }
        )

    if any(term in lowered for term in ["mark", "mark target", "mark area"]):
        if not location:
            return None
        return validate_command(
            {
                **base_payload,
                "goal": "MARK",
                "target_location": location,
                "confidence": 0.9,
            }
        )

    if any(term in lowered for term in ["hold position", "stay put", "hold", "wait there"]):
        return validate_command(
            {
                **base_payload,
                "goal": "HOLD_POSITION",
                "confidence": 0.97,
            }
        )

    if "patrol" in lowered:
        if not location:
            return None
        payload = {
            **base_payload,
            "goal": "SCAN_AREA",
            "target_location": location_mentions[0],
            "confidence": 0.95,
        }
        if len(location_mentions) > 1:
            payload["patrol_end_location"] = location_mentions[-1]
        return validate_command(payload)

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
                **base_payload,
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
                **base_payload,
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
                **base_payload,
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
                **base_payload,
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
                "You convert short radio-style operator speech into command JSON for a drone swarm. "
                "Return only JSON that fits the provided schema. "
                f"Allowed callsigns: {', '.join(ALLOWED_CALLSIGNS)}. "
                f"Allowed goals: {', '.join(ALLOWED_GOALS)}. "
                f"Allowed locations: {', '.join(ALLOWED_LOCATIONS)}. "
                "Prefer commands in the form '[CALLSIGN] [ACTION] [LOCATION] OVER'. "
                "If the request is unclear or unsafe, return goal NO_OP with null locations. "
                "ATTACK_AREA must set confirmation_required true and execution_state PENDING_EXECUTE. "
                "Recon patrol routes should use goal SCAN_AREA with target_location as the start "
                "and patrol_end_location as the end. "
                "Reviewing reports should use goal REVIEW_REPORTS with no target."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Schema:\n{schema_text}\n\n"
                f"Operator text: {text}\n"
                "Return only one JSON object. "
                "Examples: 'JARVIS, move to Sector Bravo 3, over.' "
                "'JARVIS, recon patrol Bravo 1 to Bravo 3, over.' "
                "'JARVIS, review reports, over.' "
                "'JARVIS, all units, abort, out.' "
                "'JARVIS, execute, over.'"
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
    patrol_end = command.get("patrol_end_location")
    callsign = command.get("callsign") or _default_callsign()
    execution_state = command.get("execution_state")

    def humanize(location: str | None) -> str | None:
        if not location:
            return None
        return location.replace("_", " ").title()

    if goal == "MOVE_TO" and target:
        return f"{callsign}, moving to {humanize(target)}, over."
    if goal == "ATTACK_AREA" and target and execution_state == "PENDING_EXECUTE":
        return f"{callsign}, attack on {humanize(target)} pending execute, over."
    if goal == "ATTACK_AREA" and target:
        return f"{callsign}, attacking {humanize(target)}, over."
    if goal == "AVOID_AREA" and avoid:
        return f"{callsign}, avoiding {humanize(avoid)}, over."
    if goal == "SCAN_AREA" and target and patrol_end:
        return f"{callsign}, recon patrol from {humanize(target)} to {humanize(patrol_end)}, over."
    if goal == "SCAN_AREA" and target:
        return f"{callsign}, scanning {humanize(target)}, over."
    if goal == "REVIEW_REPORTS":
        return f"{callsign}, reviewing mission reports, over."
    if goal == "LOITER" and target:
        return f"{callsign}, loitering at {humanize(target)}, over."
    if goal == "MARK" and target:
        return f"{callsign}, marking {humanize(target)}, over."
    if goal == "HOLD_POSITION":
        return f"{callsign}, holding position, over."
    if goal == "STANDBY":
        return f"{callsign}, standby, over."
    if goal == "EXECUTE":
        return f"{callsign}, execute received, over."
    if goal == "DISREGARD":
        return f"{callsign}, pending command disregarded, over."
    if goal == "ABORT":
        return f"{callsign}, abort acknowledged, out."
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


ALLOWED_CALLSIGNS = _parse_csv_env("JARVIS_ALLOWED_CALLSIGNS", DEFAULT_CALLSIGNS)
ALLOWED_GOALS = _parse_csv_env("JARVIS_ALLOWED_GOALS", DEFAULT_GOALS)
ALLOWED_LOCATIONS = _parse_csv_env("JARVIS_ALLOWED_LOCATIONS", DEFAULT_LOCATIONS)
LOCATION_ALIASES = _location_aliases()
COMMAND_SCHEMA = _build_schema()
