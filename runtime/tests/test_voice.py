import asyncio
from pathlib import Path

from charlie.interfaces.voice.output import EdgeTTSVoice
from charlie.interfaces.voice.wakeword import WakeGate


def test_wake_gate_idle_until_wake_word():
    gate = WakeGate()
    assert gate.consider("open terminal") == ("ignore", "")
    assert gate.consider("wake up") == ("wake_ack", "")
    assert gate.active is True
    assert gate.consider("open terminal") == ("command", "open terminal")


def test_wake_with_command_same_breath():
    gate = WakeGate()
    kind, payload = gate.consider("wake up open slack")
    assert kind == "command"
    assert payload == "open slack"


def test_bye_deactivates_only_when_awake():
    gate = WakeGate()
    assert gate.consider("bye") == ("ignore", "")
    gate.consider("wake up")
    assert gate.consider("bye") == ("goodbye", "")
    assert gate.active is False
    assert gate.consider("open terminal") == ("ignore", "")


def test_edge_tts_uses_ana_neural(monkeypatch, tmp_path):
    calls: list[tuple[str, str]] = []

    class FakeComm:
        def __init__(self, text: str, voice: str) -> None:
            calls.append((text, voice))

        async def save(self, path: str) -> None:
            Path(path).write_bytes(b"ID3")

    played: list[str] = []
    monkeypatch.setattr("charlie.interfaces.voice.output.edge_tts.Communicate", FakeComm)
    monkeypatch.setattr("charlie.interfaces.voice.output._play", played.append)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    voice = EdgeTTSVoice()
    asyncio.run(voice.speak("hello"))
    assert calls == [("hello", "en-US-AnaNeural")]
    assert voice.voice == "en-US-AnaNeural"
    assert played and played[0].endswith(".mp3")
