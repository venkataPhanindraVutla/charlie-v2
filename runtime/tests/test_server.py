from fastapi.testclient import TestClient

from charlie.actions.registry import ToolResult
from charlie.cognition.planner import FakePlanner
from charlie.runtime.engine import Engine
from charlie.server import create_app


class CaptureVoice:
    def __init__(self) -> None:
        self.heard: list[str] = []

    async def speak(self, text: str) -> None:
        self.heard.append(text)


class FakeRegistry:
    def execute(self, action):
        return ToolResult(ok=True, observation="Opened Terminal.", tool=action.tool)


def test_health_and_turn():
    engine = Engine(
        planner=FakePlanner(actions=[{"tool": "os.app.open", "args": {"name": "Terminal"}}]),
        registry=FakeRegistry(),
    )
    app = create_app(engine)
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "status"
        ws.send_text('{"type":"user.turn","source":"text","text":"open Terminal"}')
        types = []
        for _ in range(8):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "assistant.done":
                break
        assert "assistant.done" in types


def test_transcribe_endpoint_returns_text():
    engine = Engine(
        planner=FakePlanner(actions=[]),
        registry=FakeRegistry(),
    )
    app = create_app(engine, transcribe=lambda _data: "open terminal")
    client = TestClient(app)
    result = client.post("/voice/transcribe", content=b"RIFF....")
    assert result.status_code == 200
    assert result.json() == {"text": "open terminal"}


def test_turn_speaks_through_voice_interface():
    engine = Engine(
        planner=FakePlanner(actions=[], say="Opened Terminal."),
        registry=FakeRegistry(),
    )
    voice = CaptureVoice()
    app = create_app(engine, voice=voice)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_text('{"type":"user.turn","source":"text","text":"open Terminal"}')
        for _ in range(8):
            if ws.receive_json()["type"] == "assistant.done":
                break
    assert voice.heard == ["Opened Terminal."]


def test_client_disconnect_during_hello_is_quiet():
    engine = Engine(
        planner=FakePlanner(actions=[]),
        registry=FakeRegistry(),
    )
    app = create_app(engine)
    client = TestClient(app)
    with client.websocket_connect("/ws"):
        pass
