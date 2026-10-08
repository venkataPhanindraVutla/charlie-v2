from charlie.actions.registry import ToolResult
from charlie.cognition.planner import FakePlanner
from charlie.harness.task import Task, TaskStatus
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


class CountingPlanner(FakePlanner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.n = 0

    def plan(self, text, history=None, current_task=None, observations=None, tools=None):
        self.n += 1
        return super().plan(text, history, current_task, observations, tools)


def test_progress_does_not_replan():
    planner = CountingPlanner(actions=[], say="Opened Slack.")
    engine = Engine(planner=planner, registry=FakeRegistry())
    engine.harness.current = Task(goal="open arun chat in slack", status=TaskStatus.running)
    engine.harness.last_summary = "Slack is open."
    events = engine.run_turn("what's the progress")
    assert planner.n == 0
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


def test_harness_plans_once_then_executes():
    planner = CountingPlanner(
        actions=[{"tool": "os.terminal.run", "args": {"command": "echo hi"}}],
        say="Finished after seeing the output.",
    )
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn("run echo in the terminal")
    assert planner.n == 2
    assert planner.last_observations
    assert len(registry.calls) == 1
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "Finished" in done["text"]
