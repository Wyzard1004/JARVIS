from __future__ import annotations

import io
import os
import signal
import time
import wave
from glob import glob
from pathlib import Path

import pyaudio
import requests
import serial
from dotenv import load_dotenv


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_STATION_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class JetsonSerialPTTListener:
    """Button-driven listener: ESP32 serial PTT -> record Jetson mic -> local API."""

    START_EVENTS = {"PTT_DOWN", "BUTTON_DOWN", "START", "START_LISTEN"}
    STOP_EVENTS = {"PTT_UP", "BUTTON_UP", "STOP", "STOP_LISTEN"}
    CANCEL_EVENTS = {"CANCEL", "ABORT"}

    def __init__(self) -> None:
        self.sample_rate = int(os.getenv("JARVIS_LISTENER_SAMPLE_RATE", 16000))
        self.channels = int(os.getenv("JARVIS_LISTENER_CHANNELS", 1))
        self.chunk_samples = int(os.getenv("JARVIS_LISTENER_CHUNK_SAMPLES", 1280))
        self.api_timeout = int(os.getenv("JARVIS_LISTENER_API_TIMEOUT", 90))
        self.api_url = os.getenv(
            "JARVIS_LISTENER_API_URL",
            "http://127.0.0.1:8000/api/transcribe-command",
        ).strip()

        self.serial_port = os.getenv("JARVIS_SERIAL_PORT", "").strip()
        self.serial_baud = int(os.getenv("JARVIS_SERIAL_BAUD", 115200))
        self.serial_timeout = float(os.getenv("JARVIS_SERIAL_TIMEOUT", 0.05))

        self.audio_device_name = os.getenv("JARVIS_AUDIO_DEVICE_NAME", "").strip().lower()
        self.audio_device_index = self._parse_int_env("JARVIS_AUDIO_DEVICE_INDEX")
        self.audio_device_rate = self._parse_int_env("JARVIS_AUDIO_DEVICE_RATE")

        self.min_command_seconds = float(os.getenv("JARVIS_LISTENER_MIN_COMMAND_SECONDS", 0.35))
        self.max_command_seconds = float(os.getenv("JARVIS_LISTENER_MAX_COMMAND_SECONDS", 8.0))
        self.cooldown_seconds = float(os.getenv("JARVIS_LISTENER_COOLDOWN_SECONDS", 0.25))

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

    @staticmethod
    def _parse_int_env(name: str) -> int | None:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def stop(self, *_args) -> None:
        self._stop_requested = True

    def run_forever(self) -> None:
        self._open_serial()
        print("[PTT] Serial button listener online")
        print(f"[PTT] Posting commands to {self.api_url}")
        print(
            "[PTT] Waiting for ESP32 on "
            f"{self._serial.port} @ {self.serial_baud} baud"
        )

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
                event = self._read_serial_event(block=True)
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

                event = self._read_serial_event(block=False)
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

    def _read_serial_event(self, block: bool) -> str | None:
        assert self._serial is not None

        try:
            if not block and self._serial.in_waiting <= 0:
                return None
            raw = self._serial.readline()
        except serial.SerialException as exc:
            print(f"[PTT] Serial read failed: {exc}")
            return None

        if not raw:
            return None

        event = raw.decode("utf-8", errors="ignore").strip().upper()
        if not event:
            return None

        event = self._normalize_serial_event(event)

        if event in self.STOP_EVENTS and not self._listening:
            print(f"[PTT] Ignoring stop event while idle: {event}")
            return None

        print(f"[PTT] ESP32 event: {event}")
        return event

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

    def _write_serial(self, message: str) -> None:
        if self._serial is None or not self._serial.is_open:
            return
        try:
            self._serial.write(f"{message}\n".encode("utf-8"))
        except serial.SerialException:
            pass

    def _submit_command(self, wav_bytes: bytes) -> None:
        try:
            response = self._session.post(
                self.api_url,
                files={"audio": ("command.wav", wav_bytes, "audio/wav")},
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
        execution_state = parsed.get("execution_state", "NONE")

        print(f"[PTT] Transcript: {transcript}")
        print(f"[PTT] Status: {status} execution_state={execution_state}")
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
