from __future__ import annotations

import base64
import io
import json
import os
import queue
import signal
import threading
import time
import wave
from collections import deque
from glob import glob
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pyaudio
import requests
import serial
from dotenv import load_dotenv


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_STATION_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class _RelayBridgeHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], listener: "JetsonSerialPTTListener"):
        super().__init__(server_address, _RelayBridgeRequestHandler)
        self.listener = listener


class _RelayBridgeRequestHandler(BaseHTTPRequestHandler):
    server: _RelayBridgeHttpServer

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path != "/status":
            self._write_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return

        self._write_json(HTTPStatus.OK, self.server.listener.get_bridge_status())

    def do_POST(self) -> None:
        if self.path != "/relay":
            self._write_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        try:
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
            response = self.server.listener.queue_relay_packet(payload)
            status_code = HTTPStatus.OK if response.get("accepted") else HTTPStatus.SERVICE_UNAVAILABLE
            self._write_json(status_code, response)
        except json.JSONDecodeError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"detail": f"Invalid JSON: {exc}"})
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"detail": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive request guard
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": str(exc)})


class JetsonSerialPTTListener:
    """Button-driven listener: ESP32 serial PTT + gateway relay bridge."""

    START_EVENTS = {"PTT_DOWN", "BUTTON_DOWN", "START", "START_LISTEN"}
    STOP_EVENTS = {"PTT_UP", "BUTTON_UP", "STOP", "STOP_LISTEN"}
    CANCEL_EVENTS = {"CANCEL", "ABORT"}
    RELAY_PACKET_FIELDS = {
        "packet_kind",
        "packet_id",
        "origin_node",
        "callsign",
        "goal",
        "execution_state",
        "target_location",
        "priority",
        "issued_at_ms",
        "expires_at_ms",
        "max_hops",
        "ack_required",
        "event",
    }

    def __init__(self) -> None:
        self.sample_rate = int(os.getenv("JARVIS_LISTENER_SAMPLE_RATE", 16000))
        self.channels = int(os.getenv("JARVIS_LISTENER_CHANNELS", 1))
        self.chunk_samples = int(os.getenv("JARVIS_LISTENER_CHUNK_SAMPLES", 1280))
        self.api_timeout = int(os.getenv("JARVIS_LISTENER_API_TIMEOUT", 90))
        self.api_url = os.getenv(
            "JARVIS_LISTENER_API_URL",
            "http://127.0.0.1:8000/api/transcribe-command",
        ).strip()
        self.operator_node = os.getenv("JARVIS_OPERATOR_NODE", "").strip()

        self.serial_port = os.getenv("JARVIS_SERIAL_PORT", "").strip()
        self.serial_baud = int(os.getenv("JARVIS_SERIAL_BAUD", 115200))
        self.serial_timeout = float(os.getenv("JARVIS_SERIAL_TIMEOUT", 0.05))
        self.serial_startup_grace_seconds = float(os.getenv("JARVIS_SERIAL_STARTUP_GRACE_SECONDS", 2.5))

        self.audio_device_name = os.getenv("JARVIS_AUDIO_DEVICE_NAME", "").strip().lower()
        self.audio_device_index = self._parse_int_env("JARVIS_AUDIO_DEVICE_INDEX")
        self.audio_device_rate = self._parse_int_env("JARVIS_AUDIO_DEVICE_RATE")

        self.min_command_seconds = float(os.getenv("JARVIS_LISTENER_MIN_COMMAND_SECONDS", 0.35))
        self.max_command_seconds = float(os.getenv("JARVIS_LISTENER_MAX_COMMAND_SECONDS", 8.0))
        self.cooldown_seconds = float(os.getenv("JARVIS_LISTENER_COOLDOWN_SECONDS", 0.25))

        self.bridge_host = os.getenv("JARVIS_RELAY_BRIDGE_HOST", "127.0.0.1").strip() or "127.0.0.1"
        self.bridge_port = int(os.getenv("JARVIS_RELAY_BRIDGE_PORT", "8765"))
        self.default_relay_ttl_ms = int(os.getenv("JARVIS_RELAY_TTL_MS", "15000"))
        self.status_history_size = int(os.getenv("JARVIS_RELAY_STATUS_HISTORY_SIZE", "32"))
        self.relay_enabled = _env_flag("JARVIS_RELAY_ENABLED", True)

        self._stop_requested = False
        self._session = requests.Session()
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._serial = None
        self._listening = False
        self._selected_device_index, self._selected_device_name = self._resolve_input_device()
        self._device_sample_rate = self._resolve_device_sample_rate()
        self._chunk_seconds = self.chunk_samples / self.sample_rate
        self._device_chunk_samples = max(1, int(round(self._device_sample_rate * self._chunk_seconds)))

        self._serial_write_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._ptt_events: "queue.Queue[str]" = queue.Queue()
        self._serial_thread: threading.Thread | None = None
        self._bridge_thread: threading.Thread | None = None
        self._bridge_server: _RelayBridgeHttpServer | None = None
        self._recent_acks: deque[dict[str, Any]] = deque(maxlen=self.status_history_size)
        self._field_status: dict[str, dict[str, Any]] = {}
        self._last_packet_sent: dict[str, Any] | None = None
        self._last_relay_error: dict[str, Any] | None = None
        self._last_serial_line: str | None = None
        self._last_serial_rx_at: float | None = None
        self._serial_noise_until = 0.0
        self._suppressed_serial_noise = 0

    @staticmethod
    def _parse_int_env(name: str) -> int | None:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def stop(self, *_args: Any) -> None:
        self._stop_requested = True

    def run_forever(self) -> None:
        self._open_serial()
        self._start_bridge_server()
        self._start_serial_reader()

        print("[PTT] Serial button listener online")
        print(f"[PTT] Posting commands to {self.api_url}")
        if self.operator_node:
            print(f"[PTT] Operator node override: {self.operator_node}")
        else:
            print("[PTT] Operator node follows active simulation selection")
        print(
            "[PTT] Waiting for ESP32 on "
            f"{self._serial.port} @ {self.serial_baud} baud"
        )
        print(f"[PTT] Relay bridge listening on http://{self.bridge_host}:{self.bridge_port}")

        if self._selected_device_name:
            print(
                "[PTT] Using audio input: "
                f"index={self._selected_device_index} "
                f"name={self._selected_device_name} "
                f"device_rate={self._device_sample_rate}"
            )
        else:
            print(
                "[PTT] Using default system audio input "
                f"device_rate={self._device_sample_rate}"
            )

        self._write_serial("READY")

        try:
            while not self._stop_requested:
                event = self._next_ptt_event()
                if event is None or event not in self.START_EVENTS:
                    continue

                print(f"[PTT] Start event received: {event}")
                self._write_serial("LISTENING")
                wav_bytes = self._record_until_release()

                if wav_bytes is None:
                    self._write_serial("READY")
                    print("[PTT] Recording cancelled or too short")
                    self._cooldown()
                    continue

                self._write_serial("PROCESSING")
                self._submit_command(wav_bytes)
                self._cooldown()
        finally:
            self.close()

    def close(self) -> None:
        self._stop_requested = True

        if self._bridge_server is not None:
            self._bridge_server.shutdown()
            self._bridge_server.server_close()
            self._bridge_server = None

        if self._bridge_thread is not None and self._bridge_thread.is_alive():
            self._bridge_thread.join(timeout=1.0)
            self._bridge_thread = None

        if self._serial_thread is not None and self._serial_thread.is_alive():
            self._serial_thread.join(timeout=1.0)
            self._serial_thread = None

        if self._stream is not None:
            if self._stream.is_active():
                self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            self._serial = None
        self._audio.terminate()

    def _open_serial(self) -> None:
        port = self._resolve_serial_port()
        self._serial = serial.Serial()
        self._serial.port = port
        self._serial.baudrate = self.serial_baud
        self._serial.timeout = self.serial_timeout
        self._serial.dsrdtr = False
        self._serial.rtscts = False
        self._serial.dtr = False
        self._serial.rts = False
        self._serial.open()
        time.sleep(1.0)
        try:
            self._serial.setDTR(False)
            self._serial.setRTS(False)
        except serial.SerialException:
            pass
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()
        self._serial_noise_until = time.time() + max(0.0, self.serial_startup_grace_seconds)
        self._suppressed_serial_noise = 0

    def _resolve_serial_port(self) -> str:
        if self.serial_port:
            return self.serial_port

        candidates = sorted(glob("/dev/ttyUSB*") + glob("/dev/ttyACM*"))
        if not candidates:
            raise SystemExit(
                "No serial ESP32 found. Set JARVIS_SERIAL_PORT to a concrete device like "
                "/dev/ttyUSB0 or /dev/ttyACM0."
            )
        return candidates[0]

    def _start_serial_reader(self) -> None:
        self._serial_thread = threading.Thread(
            target=self._serial_reader_loop,
            name="jarvis-serial-reader",
            daemon=True,
        )
        self._serial_thread.start()

    def _serial_reader_loop(self) -> None:
        while not self._stop_requested and self._serial is not None and self._serial.is_open:
            try:
                raw = self._serial.readline()
            except serial.SerialException as exc:
                if not self._stop_requested:
                    print(f"[PTT] Serial read failed: {exc}")
                break

            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                self._handle_serial_line(line)

    def _handle_serial_line(self, line: str) -> None:
        timestamp = time.time()
        with self._status_lock:
            self._last_serial_line = line
            self._last_serial_rx_at = timestamp

        upper = line.upper()

        if upper == "GATEWAY_BOOT":
            self._serial_noise_until = timestamp + max(0.0, self.serial_startup_grace_seconds)
            self._suppressed_serial_noise = 0
            print("[PTT] Gateway boot detected; waiting for serial to settle")
            self._write_serial("READY")
            return

        if upper.startswith("ACK "):
            self._record_ack(line, timestamp)
            return

        if upper.startswith("STATUS "):
            self._record_status(line, timestamp)
            return

        if upper.startswith("RELAY_ERR "):
            error_code = line.split(" ", 1)[1].strip()
            with self._status_lock:
                self._last_relay_error = {"code": error_code, "timestamp": timestamp}
            print(f"[PTT] Relay error: {error_code}")
            return

        normalized = self._normalize_serial_event(line)
        if normalized in self.STOP_EVENTS and not self._listening:
            print(f"[PTT] Ignoring stop event while idle: {normalized}")
            return

        if normalized in self.START_EVENTS | self.STOP_EVENTS | self.CANCEL_EVENTS:
            print(f"[PTT] ESP32 event: {normalized}")
            self._ptt_events.put(normalized)
            return

        if timestamp < self._serial_noise_until:
            self._suppressed_serial_noise += 1
            if self._suppressed_serial_noise == 1:
                print("[PTT] Ignoring serial startup noise while gateway settles")
            return

        print(f"[PTT] ESP32 message: {line}")

    def _record_ack(self, line: str, timestamp: float) -> None:
        tokens = line.split()
        if len(tokens) < 4:
            print(f"[PTT] Malformed ACK line: {line}")
            return

        ack = {
            "packet_id": tokens[1],
            "node_id": tokens[2],
            "hop": tokens[3],
            "timestamp": timestamp,
        }
        with self._status_lock:
            self._recent_acks.append(ack)
            node_status = self._field_status.setdefault(tokens[2], {})
            node_status["last_ack_packet_id"] = tokens[1]
            node_status["last_ack_hop"] = tokens[3]
            node_status["last_ack_at"] = timestamp
        print(f"[PTT] Gateway ACK: packet={tokens[1]} node={tokens[2]} hop={tokens[3]}")

    def _record_status(self, line: str, timestamp: float) -> None:
        tokens = line.split(maxsplit=2)
        if len(tokens) < 3:
            print(f"[PTT] Malformed STATUS line: {line}")
            return

        node_id = tokens[1]
        state = tokens[2]
        with self._status_lock:
            node_status = self._field_status.setdefault(node_id, {})
            node_status["state"] = state
            node_status["updated_at"] = timestamp
        print(f"[PTT] Gateway STATUS: node={node_id} state={state}")

    def _start_bridge_server(self) -> None:
        self._bridge_server = _RelayBridgeHttpServer((self.bridge_host, self.bridge_port), self)
        self._bridge_thread = threading.Thread(
            target=self._bridge_server.serve_forever,
            name="jarvis-relay-bridge",
            daemon=True,
        )
        self._bridge_thread.start()

    def _next_ptt_event(self, timeout: float = 0.1) -> str | None:
        try:
            return self._ptt_events.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_bridge_status(self) -> dict[str, Any]:
        with self._status_lock:
            return {
                "relay_enabled": self.relay_enabled,
                "serial": {
                    "port": getattr(self._serial, "port", None),
                    "open": bool(self._serial is not None and self._serial.is_open),
                    "baud": self.serial_baud,
                    "last_line": self._last_serial_line,
                    "last_rx_at": self._last_serial_rx_at,
                },
                "listener": {
                    "api_url": self.api_url,
                    "listening": self._listening,
                    "stop_requested": self._stop_requested,
                },
                "bridge": {
                    "host": self.bridge_host,
                    "port": self.bridge_port,
                },
                "last_packet_sent": self._last_packet_sent,
                "last_relay_error": self._last_relay_error,
                "recent_acks": list(self._recent_acks),
                "field_status": dict(self._field_status),
            }

    def queue_relay_packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.relay_enabled:
            return {"accepted": False, "detail": "Relay bridge disabled by environment"}

        if not isinstance(payload, dict):
            raise ValueError("Relay payload must be a JSON object")

        relay_payload = self._normalize_relay_payload(payload)
        encoded = base64.b64encode(
            json.dumps(relay_payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")

        if not self._write_serial(f"RELAY {encoded}"):
            return {"accepted": False, "detail": "Serial gateway unavailable"}

        with self._status_lock:
            self._last_packet_sent = {
                **relay_payload,
                "sent_at": time.time(),
            }
            self._last_relay_error = None

        return {
            "accepted": True,
            "packet_id": relay_payload["packet_id"],
            "packet_kind": relay_payload["packet_kind"],
        }

    def _normalize_relay_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = {key: payload.get(key) for key in self.RELAY_PACKET_FIELDS if key in payload}
        if not normalized.get("packet_kind"):
            raise ValueError("packet_kind is required")
        if not normalized.get("packet_id"):
            raise ValueError("packet_id is required")

        issued_at_ms = self._coerce_int(normalized.get("issued_at_ms"), default=int(time.time() * 1000))
        expires_at_ms = self._coerce_int(
            normalized.get("expires_at_ms"),
            default=issued_at_ms + max(1000, self.default_relay_ttl_ms),
        )
        if expires_at_ms <= issued_at_ms:
            expires_at_ms = issued_at_ms + max(1000, self.default_relay_ttl_ms)

        return {
            "event": str(normalized.get("event") or ""),
            "packet_kind": str(normalized["packet_kind"]),
            "packet_id": self._coerce_int(normalized["packet_id"]),
            "origin_node": str(normalized.get("origin_node") or "soldier-1"),
            "callsign": str(normalized.get("callsign") or "JARVIS"),
            "goal": str(normalized.get("goal") or "UNKNOWN"),
            "execution_state": str(normalized.get("execution_state") or "NONE"),
            "target_location": (
                None if normalized.get("target_location") in (None, "", "None") else str(normalized.get("target_location"))
            ),
            "priority": str(normalized.get("priority") or "medium"),
            "issued_at_ms": issued_at_ms,
            "expires_at_ms": expires_at_ms,
            "max_hops": max(0, self._coerce_int(normalized.get("max_hops"), default=2)),
            "ack_required": bool(normalized.get("ack_required", True)),
        }

    @staticmethod
    def _coerce_int(value: Any, default: int | None = None) -> int:
        if value is None:
            if default is None:
                raise ValueError("Integer value required")
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value).strip()
        if not text:
            if default is None:
                raise ValueError("Integer value required")
            return default
        return int(text)

    def _open_stream(self) -> None:
        if self._stream is not None:
            return

        open_kwargs = {
            "format": pyaudio.paInt16,
            "channels": self.channels,
            "rate": self._device_sample_rate,
            "input": True,
            "frames_per_buffer": self._device_chunk_samples,
        }
        if self._selected_device_index is not None:
            open_kwargs["input_device_index"] = self._selected_device_index

        self._stream = self._audio.open(**open_kwargs)

    def _resolve_input_device(self) -> tuple[int | None, str | None]:
        device_count = self._audio.get_device_count()

        if self.audio_device_index is not None:
            try:
                info = self._audio.get_device_info_by_index(self.audio_device_index)
            except Exception:
                return None, None
            return self.audio_device_index, str(info.get("name") or "")

        if not self.audio_device_name:
            return None, None

        for index in range(device_count):
            try:
                info = self._audio.get_device_info_by_index(index)
            except Exception:
                continue
            if int(info.get("maxInputChannels", 0)) <= 0:
                continue
            name = str(info.get("name") or "")
            if self.audio_device_name in name.lower():
                return index, name

        return None, None

    def _resolve_device_sample_rate(self) -> int:
        if self.audio_device_rate is not None:
            return self.audio_device_rate

        if self._selected_device_index is not None:
            try:
                info = self._audio.get_device_info_by_index(self._selected_device_index)
                rate = int(round(float(info.get("defaultSampleRate", self.sample_rate))))
                return rate or self.sample_rate
            except Exception:
                return self.sample_rate

        try:
            info = self._audio.get_default_input_device_info()
            rate = int(round(float(info.get("defaultSampleRate", self.sample_rate))))
            return rate or self.sample_rate
        except Exception:
            return self.sample_rate

    def _read_chunk(self) -> bytes:
        assert self._stream is not None
        return self._stream.read(self._device_chunk_samples, exception_on_overflow=False)

    def _record_until_release(self) -> bytes | None:
        self._open_stream()
        self._listening = True
        recorded_chunks: list[bytes] = []
        started_at = time.monotonic()
        cancelled = False

        try:
            while not self._stop_requested:
                recorded_chunks.append(self._read_chunk())
                elapsed = time.monotonic() - started_at

                event = self._next_ptt_event(timeout=0.0)
                if event in self.CANCEL_EVENTS:
                    cancelled = True
                    break
                if event in self.STOP_EVENTS:
                    break
                if elapsed >= self.max_command_seconds:
                    print(f"[PTT] Max duration reached ({self.max_command_seconds:.1f}s)")
                    break
        finally:
            self._listening = False
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

        duration = time.monotonic() - started_at
        if cancelled or duration < self.min_command_seconds or not recorded_chunks:
            return None

        return self._encode_wav(recorded_chunks)

    def _encode_wav(self, chunks: list[bytes]) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self._audio.get_sample_size(pyaudio.paInt16))
            wav_file.setframerate(self._device_sample_rate)
            wav_file.writeframes(b"".join(chunks))
        return buffer.getvalue()

    @classmethod
    def _normalize_serial_event(cls, event: str) -> str:
        normalized = event.strip().upper()

        if normalized.endswith("PTT_DOWN") or normalized.endswith("TT_DOWN"):
            return "PTT_DOWN"
        if normalized.endswith("PTT_UP") or normalized.endswith("TT_UP"):
            return "PTT_UP"
        if normalized.endswith("BUTTON_DOWN"):
            return "BUTTON_DOWN"
        if normalized.endswith("BUTTON_UP"):
            return "BUTTON_UP"
        if normalized.endswith("START_LISTEN"):
            return "START_LISTEN"
        if normalized.endswith("STOP_LISTEN"):
            return "STOP_LISTEN"
        if normalized.endswith("START"):
            return "START"
        if normalized.endswith("STOP"):
            return "STOP"
        if normalized.endswith("CANCEL"):
            return "CANCEL"
        if normalized.endswith("ABORT"):
            return "ABORT"

        return normalized

    def _write_serial(self, message: str) -> bool:
        if self._serial is None or not self._serial.is_open:
            return False
        try:
            with self._serial_write_lock:
                self._serial.write(f"{message}\n".encode("utf-8"))
            return True
        except serial.SerialException as exc:
            with self._status_lock:
                self._last_relay_error = {"code": str(exc), "timestamp": time.time()}
            return False

    def _submit_command(self, wav_bytes: bytes) -> None:
        try:
            form_data = {"input_source": "jetson-esp32-ptt"}
            if self.operator_node:
                form_data["origin"] = self.operator_node
                form_data["operator_node"] = self.operator_node
            duration_seconds = 0.0
            if self.channels > 0 and self.sample_rate > 0:
                duration_seconds = len(wav_bytes) / (2 * self.channels * self.sample_rate)
            print(
                "[PTT] Uploading command audio "
                f"bytes={len(wav_bytes)} duration={duration_seconds:.2f}s "
                f"to {self.api_url}"
            )
            response = self._session.post(
                self.api_url,
                files={"audio": ("command.wav", wav_bytes, "audio/wav")},
                data=form_data,
                timeout=self.api_timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            print(f"[PTT] Failed to reach local API: {exc}")
            self._write_serial("ERROR")
            return

        transcript = payload.get("transcribed_text") or ""
        parsed = payload.get("parsed_command") or {}
        goal = parsed.get("goal", "UNKNOWN")
        target = parsed.get("target_location") or parsed.get("avoid_location") or "NONE"
        status = payload.get("status", "unknown")
        message = (payload.get("message") or "").strip()
        execution_state = parsed.get("execution_state", "NONE")
        trace_id = payload.get("trace_id") or "unknown"
        command_id = payload.get("command_id") or "unknown"
        operator_context = payload.get("operator_context") or {}
        origin = (
            payload.get("origin")
            or operator_context.get("active_operator")
            or self.operator_node
            or "unknown"
        )

        print(f"[PTT] Transcript: {transcript}")
        print(f"[PTT] Trace: {trace_id} command_id={command_id}")
        print(f"[PTT] Origin: {origin}")
        print(f"[PTT] Status: {status} execution_state={execution_state}")
        if message:
            print(f"[PTT] Message: {message}")
        print(f"[PTT] Parsed goal: {goal} target={target}")
        self._write_serial(f"RESULT {goal} {target}")

    def _cooldown(self) -> None:
        if self.cooldown_seconds > 0:
            time.sleep(self.cooldown_seconds)


def main() -> None:
    listener = JetsonSerialPTTListener()
    signal.signal(signal.SIGINT, listener.stop)
    signal.signal(signal.SIGTERM, listener.stop)
    listener.run_forever()


if __name__ == "__main__":
    main()
