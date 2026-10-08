from __future__ import annotations

import asyncio

from charlie.interfaces.voice.output import EdgeTTSVoice

_voice = EdgeTTSVoice()


def speak(text: str) -> None:
    """Sync façade for threads without a running loop. Harness uses VoiceOutput."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_voice.speak(text))
        return
    raise RuntimeError("use await voice.speak() from an async context")
