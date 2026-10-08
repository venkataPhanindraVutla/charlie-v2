from charlie.actions.registry import ToolResult
from charlie.cognition.planner import Action, FakePlanner, Plan
from charlie.memory.store import Store
from charlie.runtime.engine import Engine


class FakeRegistry:
    def __init__(self) -> None:
        self.calls = []

    def schemas(self):
        return [{"name": "os.app.jump", "description": "jump", "parameters": {"app": "string", "query": "string"}}]

    def execute(self, action):
        self.calls.append(action)
        app = action.args.get("app") or action.args.get("name") or "app"
        label = action.args.get("query") or action.args.get("name") or ""
        return ToolResult(ok=True, observation=f"Opened {label} in {app}.", tool=action.tool)


class TwoStepPlanner:
    def __init__(self) -> None:
        self.n = 0
        self.last_observations = []

    def plan(self, text, history=None, current_task=None, observations=None, tools=None):
        self.n += 1
        self.last_observations = list(observations or [])
        if self.n == 1:
            return Plan(
                actions=[Action(tool="os.terminal.run", args={"command": "echo hi"})],
                say="",
                done=False,
            )
        return Plan(actions=[], say="Finished after seeing the output.", done=True)


def test_progress_goes_to_planner():
    planner = FakePlanner(actions=[], say="Still working on that Slack jump.")
    engine = Engine(planner=planner, registry=FakeRegistry())
    events = engine.run_turn("what's the progress")
    assert planner.last_text == "what's the progress"
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "slack" in done["text"].lower()


def test_engine_runs_planner_tools_verbatim():
    planner = FakePlanner(
        actions=[{"tool": "os.app.jump", "args": {"app": "WhatsApp", "query": "Arun", "hotkey": "f"}}],
        say="Opened Arun in WhatsApp.",
    )
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn("over whatsapp not slack")
    assert len(registry.calls) == 1
    assert registry.calls[0].args["app"] == "WhatsApp"
    assert registry.calls[0].args["query"] == "Arun"
    assert registry.calls[0].args["hotkey"] == "f"
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "whatsapp" in done["text"].lower()


def test_engine_does_not_invent_tools():
    planner = FakePlanner(actions=[], say="Okay.")
    registry = FakeRegistry()
    Engine(planner=planner, registry=registry).run_turn("open arun chat in slack")
    assert registry.calls == []


def test_planner_receives_history(tmp_path):
    planner = FakePlanner(actions=[], say="Okay.")
    memory = Store(tmp_path / "c.db")
    engine = Engine(planner=planner, registry=FakeRegistry(), memory=memory)
    engine.run_turn("open slack")
    engine.run_turn("now chrome")
    assert planner.last_history
    assert any(t["text"] == "open slack" for t in planner.last_history)


def test_agent_loop_feeds_observations():
    planner = TwoStepPlanner()
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn("do the thing")
    assert planner.n == 2
    assert planner.last_observations
    assert planner.last_observations[0]["tool"] == "os.terminal.run"
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "Finished" in done["text"]
