from charlie.cognition.planner import ModelUnavailable, Planner
from charlie.runtime.engine import Engine


class DownPlanner(Planner):
    def plan(self, text: str, history=None, current_task=None, **kwargs):
        raise ModelUnavailable("down")


def test_model_down_stays_up():
    engine = Engine(planner=DownPlanner(), registry=None)
    events = engine.run_turn("open Terminal")
    assert any(e.get("state") == "error" for e in events)
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "Ollama" in done["text"]
