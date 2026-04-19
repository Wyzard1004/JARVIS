from __future__ import annotations

import audioop
import io
import os
import signal
import time
import wave
from collections import deque
from pathlib import Path
from typing import Iterable

import requests
from dotenv import load_dotenv

try:
    import numpy as np
    import openwakeword
    import pyaudio
    from openwakeword.model import Model
except ImportError as exc:  # pragma: no cover - dependency check for Jetson runtime
    raise SystemExit(
        "Missing headless listener dependencies. Install base_station/requirements.txt "
        "and Jetson audio packages (for example: portaudio19-dev, alsa-utils, ffmpeg)."
    ) from exc


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_STATION_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


class JetsonWakeListener:
    """Reliable hackathon listener: wake word -> record utterance -> local API."""

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
        self.audio_device_name = os.getenv("JARVIS_AUDIO_DEVICE_NAME", "").strip().lower()
        self.audio_device_index = self._parse_int_env("JARVIS_AUDIO_DEVICE_INDEX")
        self.audio_device_rate = self._parse_int_env("JARVIS_AUDIO_DEVICE_RATE")

        self.wakeword_threshold = float(os.getenv("JARVIS_WAKEWORD_THRESHOLD", 0.55))
        self.wakeword_labels = self._parse_csv_env("JARVIS_WAKEWORD_LABELS", ["hey jarvis", "hey_jarvis"])
        self.vad_threshold = float(os.getenv("JARVIS_WAKEWORD_VAD_THRESHOLD", 0.45))
        self.enable_noise_suppression = _env_flag("JARVIS_WAKEWORD_SPEEX", False)
        self.auto_download_models = _env_flag("JARVIS_WAKEWORD_AUTO_DOWNLOAD", True)

        self.silence_rms = float(os.getenv("JARVIS_LISTENER_SILENCE_RMS", 550))
        self.silence_seconds = float(os.getenv("JARVIS_LISTENER_SILENCE_SECONDS", 1.2))
        self.pre_roll_seconds = float(os.getenv("JARVIS_LISTENER_PRE_ROLL_SECONDS", 0.35))
        self.command_start_timeout = float(os.getenv("JARVIS_LISTENER_COMMAND_START_TIMEOUT", 3.0))
        self.min_command_seconds = float(os.getenv("JARVIS_LISTENER_MIN_COMMAND_SECONDS", 0.9))
        self.max_command_seconds = float(os.getenv("JARVIS_LISTENER_MAX_COMMAND_SECONDS", 8.0))
        self.cooldown_seconds = float(os.getenv("JARVIS_LISTENER_COOLDOWN_SECONDS", 2.0))

        self._stop_requested = False
        self._session = requests.Session()
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._selected_device_index, self._selected_device_name = self._resolve_input_device()
        self._device_sample_rate = self._resolve_device_sample_rate()

        if self.auto_download_models:
            openwakeword.utils.download_models()
        self._wake_model = Model(
            vad_threshold=self.vad_threshold,
            enable_speex_noise_suppression=self.enable_noise_suppression,
        )

        self._chunk_seconds = self.chunk_samples / self.sample_rate
        self._pre_roll_chunks = max(1, int(round(self.pre_roll_seconds / self._chunk_seconds)))
        self._device_chunk_samples = max(1, int(round(self._device_sample_rate * self._chunk_seconds)))
        self._resample_state = None

    @staticmethod
    def _parse_csv_env(name: str, default: list[str]) -> list[str]:
        raw = os.getenv(name, "")
        values = [_normalize_label(item) for item in raw.split(",") if item.strip()]
        return values or [_normalize_label(item) for item in default]

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
        self._open_stream()
        print("[LISTENER] Jetson wake listener online")
        print(f"[LISTENER] Wake labels: {', '.join(self.wakeword_labels)}")
        print(f"[LISTENER] Posting commands to {self.api_url}")
        if self.operator_node:
            print(f"[LISTENER] Operator node override: {self.operator_node}")
        else:
            print("[LISTENER] Operator node follows active simulation selection")
        if self._selected_device_name:
            print(
                "[LISTENER] Using audio input: "
                f"index={self._selected_device_index} "
                f"name={self._selected_device_name} "
                f"device_rate={self._device_sample_rate} "
                f"wake_rate={self.sample_rate}"
            )
        else:
            print(
                "[LISTENER] Using default system audio input "
                f"device_rate={self._device_sample_rate} wake_rate={self.sample_rate}"
            )

        pre_roll: deque[bytes] = deque(maxlen=self._pre_roll_chunks)

        try:
            while not self._stop_requested:
                chunk = self._read_chunk()
                pre_roll.append(chunk)
                frame = self._resample_for_wakeword(chunk)

                score = self._wake_score(frame)
                if score < self.wakeword_threshold:
                    continue

                print(f"[LISTENER] Wake word detected (score={score:.2f})")
                command_wav = self._capture_command(pre_roll, first_chunk=chunk)
                if not command_wav:
                    print("[LISTENER] No command captured after wake word")
                    self._cooldown()
                    continue

                self._submit_command(command_wav)
                self._cooldown()
        finally:
            self.close()

    def close(self) -> None:
        if self._stream is not None:
            if self._stream.is_active():
                self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        self._audio.terminate()

    def _open_stream(self) -> None:
        open_kwargs = {
            "format": pyaudio.paInt16,
            "channels": self.channels,
            "rate": self._device_sample_rate,
            "input": True,
            "frames_per_buffer": self._device_chunk_samples,
        }
        if self._selected_device_index is not None:
            open_kwargs["input_device_index"] = self._selected_device_index

        self._stream = self._audio.open(
            **open_kwargs,
        )

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

    def _read_chunk(self) -> bytes:
        assert self._stream is not None
        return self._stream.read(self._device_chunk_samples, exception_on_overflow=False)

    def _wake_score(self, frame: np.ndarray) -> float:
        predictions = self._wake_model.predict(frame)
        best_score = 0.0
        for raw_label, score in predictions.items():
            normalized = _normalize_label(raw_label)
            if normalized in self.wakeword_labels:
                best_score = max(best_score, float(score))
        return best_score

    def _capture_command(self, pre_roll: Iterable[bytes], first_chunk: bytes) -> bytes | None:
        recorded_chunks = list(pre_roll)
        if not recorded_chunks or recorded_chunks[-1] != first_chunk:
            recorded_chunks.append(first_chunk)

        command_started = False
        silence_run = 0.0
        started_at = time.monotonic()
        speech_deadline = started_at + self.command_start_timeout

        while not self._stop_requested:
            elapsed = time.monotonic() - started_at
            if elapsed >= self.max_command_seconds:
                break

            chunk = self._read_chunk()
            recorded_chunks.append(chunk)
            frame = self._resample_for_wakeword(chunk)
            rms = self._rms(frame)

            if rms >= self.silence_rms:
                command_started = True
                silence_run = 0.0
            elif command_started:
                silence_run += self._chunk_seconds

            if not command_started and time.monotonic() >= speech_deadline:
                return None

            if command_started and elapsed >= self.min_command_seconds and silence_run >= self.silence_seconds:
                break

        if not command_started:
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

    def _submit_command(self, wav_bytes: bytes) -> None:
        try:
            form_data = {"input_source": "jetson-wakeword"}
            if self.operator_node:
                form_data["origin"] = self.operator_node
                form_data["operator_node"] = self.operator_node
            duration_seconds = 0.0
            if self.channels > 0 and self._device_sample_rate > 0:
                duration_seconds = len(wav_bytes) / (2 * self.channels * self._device_sample_rate)
            print(
                "[LISTENER] Uploading command audio "
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
            print(f"[LISTENER] Failed to reach local API: {exc}")
            return

        transcript = payload.get("transcribed_text") or ""
        parsed = payload.get("parsed_command") or {}
        goal = parsed.get("goal", "UNKNOWN")
        target = parsed.get("target_location") or parsed.get("avoid_location")
        status = payload.get("status", "unknown")
        execution_state = parsed.get("execution_state", "NONE")
        origin = payload.get("origin") or self.operator_node or "unknown"
        trace_id = payload.get("trace_id") or "unknown"
        command_id = payload.get("command_id") or "unknown"

        print(f"[LISTENER] Transcript: {transcript}")
        print(f"[LISTENER] Trace: {trace_id} command_id={command_id}")
        print(f"[LISTENER] Origin: {origin}")
        print(f"[LISTENER] Status: {status} execution_state={execution_state}")
        print(f"[LISTENER] Parsed goal: {goal} target={target}")

    def _cooldown(self) -> None:
        if self.cooldown_seconds <= 0:
            return
        time.sleep(self.cooldown_seconds)

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        if frame.size == 0:
            return 0.0
        samples = frame.astype(np.float32)
        return float(np.sqrt(np.mean(np.square(samples))))

    def _resample_for_wakeword(self, chunk: bytes) -> np.ndarray:
        if self._device_sample_rate == self.sample_rate:
            return np.frombuffer(chunk, dtype=np.int16)

        converted, self._resample_state = audioop.ratecv(
            chunk,
            2,
            self.channels,
            self._device_sample_rate,
            self.sample_rate,
            self._resample_state,
        )
        return np.frombuffer(converted, dtype=np.int16)

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


def main() -> None:
    listener = JetsonWakeListener()
    signal.signal(signal.SIGINT, listener.stop)
    signal.signal(signal.SIGTERM, listener.stop)
    listener.run_forever()


if __name__ == "__main__":
    main()
