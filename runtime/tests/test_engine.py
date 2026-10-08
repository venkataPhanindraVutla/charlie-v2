from charlie.cognition.planner import FakePlanner
from charlie.runtime.engine import Engine


class FakeRegistry:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls = []

    def execute(self, action):
        from charlie.actions.registry import ToolResult

        self.calls.append(action)
        return ToolResult(ok=self.ok, observation="Opened Terminal.", tool=action.tool)


def test_open_app_turn_emits_status_and_reply():
    engine = Engine(
        planner=FakePlanner(actions=[{"tool": "os.app.open", "args": {"name": "Terminal"}}]),
        registry=FakeRegistry(ok=True),
    )
    events = engine.run_turn("open Terminal", "text")
    states = [e.get("state") for e in events if e["type"] == "status"]
    assert "thinking" in states
    assert "acting" in states
    assert "done" in states
    assert any(e["type"] == "assistant.done" for e in events)
    assert any(e["type"] == "speak" for e in events)
