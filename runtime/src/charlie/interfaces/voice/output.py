from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from typing import Protocol

import edge_tts

VOICE = "en-US-AnaNeural"
DEBOUNCE_S = 6.0


class VoiceOutput(Protocol):
    async def speak(self, text: str) -> None: ...


class NullVoice:
    async def speak(self, text: str) -> None:
        return


class EdgeTTSVoice:
    """Original Charlie TTS: edge-tts → en-US-AnaNeural → afplay."""

    voice = VOICE

    def __init__(self, voice: str = VOICE) -> None:
        self.voice = voice
        self._lock = asyncio.Lock()
        self._last = ""
        self._last_at = 0.0

    async def speak(self, text: str) -> None:
        spoken = (text or "").strip()
        if not spoken:
            return
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        now = time.monotonic()
        async with self._lock:
            if spoken == self._last and now - self._last_at < DEBOUNCE_S:
                return
            self._last = spoken
            self._last_at = now
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            try:
                await edge_tts.Communicate(spoken, self.voice).save(path)
                await asyncio.to_thread(_play, path)
            except Exception as exc:
                print(f"TTS Error: {exc}")
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass


def _play(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Add-Type -AssemblyName presentationCore; "
                f"$p = New-Object System.Windows.Media.MediaPlayer; "
                f"$p.Open([uri]'{path.replace(chr(39), chr(39)+chr(39))}'); "
                f"$p.Play(); "
                f"while ($p.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 50 }}; "
                f"Start-Sleep -Seconds $p.NaturalDuration.TimeSpan.TotalSeconds",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
