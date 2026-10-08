from __future__ import annotations

import io
import os
import wave
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np

_MODEL: Any = None
_BACKEND: str | None = None


def _load_model() -> Any:
    global _BACKEND
    try:
        import mlx_whisper

        _BACKEND = "mlx"
        return mlx_whisper
    except Exception:
        pass
    from faster_whisper import WhisperModel

    last_error: Exception | None = None
    for compute_type in ("int8", "float32"):
        try:
            model = WhisperModel("tiny.en", device="cpu", compute_type=compute_type)
            _BACKEND = "faster"
            return model
        except Exception as exc:
            last_error = exc
    raise RuntimeError(str(last_error) or "Could not load local whisper.")


def model() -> Any:
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()
    return _MODEL


def wav_to_float32(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(audio), int(rate)


def resample(audio: np.ndarray, src_rate: int, dst_rate: int = 16000) -> np.ndarray:
    if src_rate == dst_rate or audio.size == 0:
        return audio.astype(np.float32)
    n = int(round(audio.size * dst_rate / src_rate))
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    old = np.linspace(0.0, 1.0, audio.size, endpoint=False)
    new = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(new, old, audio).astype(np.float32)


def transcribe_wav_bytes(data: bytes, whisper: Any | None = None) -> str:
    if not data or len(data) < 44:
        return ""
    audio, rate = wav_to_float32(data)
    audio = resample(audio, rate, 16000)
    duration = audio.size / 16000.0
    if duration < 0.28 or float(np.max(np.abs(audio))) < 0.012:
        return ""
    engine = whisper if whisper is not None else model()
    if hasattr(engine, "transcribe") and engine.__class__.__name__ != "module":
        segments, _info = engine.transcribe(audio, language="en", beam_size=1)
        return " ".join(segment.text for segment in segments).strip()
    result = engine.transcribe(audio, path_or_hf_repo="mlx-community/whisper-tiny.en-mlx")
    if isinstance(result, dict):
        return str(result.get("text") or "").strip()
    segments, _info = result
    return " ".join(getattr(segment, "text", str(segment)) for segment in segments).strip()
