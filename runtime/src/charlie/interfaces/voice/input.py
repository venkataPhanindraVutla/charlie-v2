from __future__ import annotations

from typing import Protocol


class VoiceInput(Protocol):
    def text(self) -> str: ...


class RealtimeSTTInput:
    """Original Charlie ear: RealtimeSTT.AudioToTextRecorder."""

    def __init__(self) -> None:
        from RealtimeSTT import AudioToTextRecorder

        self.recorder = AudioToTextRecorder(
            language="en",
            spinner=False,
            ensure_sentence_ends_with_period=True,
        )

    def text(self) -> str:
        uttered = self.recorder.text()
        return (uttered or "").strip()
