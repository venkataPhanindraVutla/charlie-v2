from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable

from charlie.interfaces.voice.input import RealtimeSTTInput
from charlie.interfaces.voice.output import VoiceOutput
from charlie.interfaces.voice.wakeword import END_PHRASE, WAKE_WORD, WakeGate

WAKE_ACK = "Hey, I'm listening!"
GOODBYE = "Sayonara Phani Sama"


def start_voice_ear(
    loop: asyncio.AbstractEventLoop,
    voice: VoiceOutput,
    on_command: Callable[[str], Awaitable[None]],
) -> threading.Thread | None:
    """Always-on mic in a daemon thread. Harness only sees text after the gate."""

    def run() -> None:
        try:
            mic = RealtimeSTTInput()
        except Exception as exc:
            print(f"RealtimeSTT unavailable: {exc}")
            return
        gate = WakeGate()
        print(f"Say '{WAKE_WORD}' to activate. Say '{END_PHRASE}' to stop.")
        while True:
            try:
                uttered = mic.text()
            except Exception as exc:
                print(f"STT Error: {exc}")
                continue
            kind, payload = gate.consider(uttered)
            if kind == "ignore":
                continue
            if kind == "wake_ack":
                _wait(loop, voice.speak(WAKE_ACK))
                continue
            if kind == "goodbye":
                _wait(loop, voice.speak(GOODBYE))
                continue
            _wait(loop, on_command(payload))

    thread = threading.Thread(target=run, daemon=True, name="charlie-ear")
    thread.start()
    return thread


def _wait(loop: asyncio.AbstractEventLoop, coro: Awaitable[None]) -> None:
    asyncio.run_coroutine_threadsafe(coro, loop).result()
