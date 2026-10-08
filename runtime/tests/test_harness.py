from charlie.actions.registry import ToolResult
from charlie.cognition.laya import Decider
from charlie.cognition.planner import FakePlanner
from charlie.harness.broker import ToolBroker
from charlie.runtime.engine import Engine


class FakeRegistry:
    def __init__(self, fail_first: int = 0) -> None:
        self.calls = []
        self.fail_first = fail_first

    def execute(self, action):
        self.calls.append(action)
        if len(self.calls) <= self.fail_first:
            return ToolResult(ok=False, observation="busy", tool=action.tool)
        return ToolResult(ok=True, observation=f"ok:{action.tool}", tool=action.tool)


def test_broker_rejects_out_of_contract():
    host = type("H", (), {"execute": lambda self, c, a: ToolResult(ok=True, observation="nope", tool=c)})()
    broker = ToolBroker(host)
    result = broker.call("web.search", {"query": "x"}, allowed=["apps.open"])
    assert result.ok is False
    assert "not allowed" in result.observation
    assert broker.calls == []


def test_decider_without_laya_picks_first():
    assert Decider(router=None).choose("state", "open", ["apps.open", "web.search"]) == "apps.open"


def test_failed_step_retries_once():
    planner = FakePlanner(actions=[{"tool": "apps.open", "args": {"name": "Slack"}}], say="Opened Slack.")
    registry = FakeRegistry(fail_first=1)
    events = Engine(planner=planner, registry=registry).run_turn("open slack")
    assert len(registry.calls) == 2
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "Opened Slack" in done["text"] or "ok:apps.open" in done["text"]


def test_unrelated_turn_does_not_hit_whatsapp():
    planner = FakePlanner(
        actions=[
            {
                "tool": "communication.send_message",
                "args": {"app": "WhatsApp", "recipient": "Arun", "message": "hi"},
            }
        ],
        say="Sent on WhatsApp.",
    )
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn("hello")
    assert registry.calls == []
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "whatsapp" not in done["text"].lower()


def test_whatsapp_turn_still_jumps():
    planner = FakePlanner(
        actions=[{"tool": "apps.jump", "args": {"app": "WhatsApp", "query": "Arun"}}],
        say="Opened Arun in WhatsApp.",
    )
    registry = FakeRegistry()
    Engine(planner=planner, registry=registry).run_turn("open arun on whatsapp")
    assert registry.calls
    assert registry.calls[0].args.get("app") == "WhatsApp" or registry.calls[0].args.get("query") == "Arun"


def test_whatsapp_send_promotes_jump_and_sends():
    planner = FakePlanner(
        actions=[{"tool": "apps.jump", "args": {"app": "WhatsApp", "query": "Deekshitha"}}],
        say="I've sent this to deekshitha on WhatsApp.",
    )
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn(
        "can you open whatsapp and send the nvidia stock price to deekshitha"
    )
    assert registry.calls
    assert registry.calls[0].tool == "communication.send_message"
    assert registry.calls[0].args.get("query") == "Deekshitha" or registry.calls[0].args.get(
        "recipient"
    ) == "Deekshitha"
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "sent" in done["text"].lower()


def test_send_again_stays_on_whatsapp():
    planner = FakePlanner(
        actions=[
            {
                "tool": "communication.send_message",
                "args": {"app": "WhatsApp", "recipient": "Deekshitha", "message": "NVIDIA is $532"},
            }
        ],
        say="Sent.",
    )
    engine = Engine(planner=planner, registry=FakeRegistry())
    engine.harness.last_domain = "communication"
    engine.run_turn("can you send again")
    assert engine.harness.last_domain == "communication"


def test_did_you_send_does_not_retype():
    planner = FakePlanner(
        actions=[
            {
                "tool": "communication.send_message",
                "args": {"app": "WhatsApp", "recipient": "Deekshitha", "message": "hi"},
            }
        ],
        say="Sent.",
    )
    registry = FakeRegistry()
    engine = Engine(planner=planner, registry=registry)
    engine.harness.last_summary = "Sent to Deekshitha in WhatsApp."
    events = engine.run_turn("did you send?")
    assert registry.calls == []
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "deekshitha" in done["text"].lower()


def test_stock_question_runs_web_search():
    from charlie.harness.policy import infer_domain

    assert infer_domain("hey what is the current nvidia stock price") == "web"
    planner = FakePlanner(
        actions=[{"tool": "web.search", "args": {"query": "NVIDIA stock price"}}],
        say="I'll check the current NVIDIA stock price for you.",
    )
    registry = FakeRegistry()
    events = Engine(planner=planner, registry=registry).run_turn(
        "hey what is the current nvidia stock price"
    )
    assert registry.calls
    assert registry.calls[0].tool == "web.search"
    done = next(e for e in events if e["type"] == "assistant.done")
    assert "i'll check" not in done["text"].lower()


def test_dedupes_list_calls():
    class Host:
        def __init__(self):
            self.n = 0

        def execute(self, capability, args):
            self.n += 1
            return ToolResult(ok=True, observation="Slack, Chrome", tool=capability)

    host = Host()
    broker = ToolBroker(host, ttl_s=30)
    first = broker.call("apps.list", {})
    second = broker.call("apps.list", {})
    assert first.observation == second.observation
    assert host.n == 1
