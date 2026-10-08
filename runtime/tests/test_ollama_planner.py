import json

import httpx

from charlie.cognition.models import OllamaPlanner
from charlie.cognition.planner import ModelUnavailable


def test_plan_parses_ollama_json():
    def handler(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        assert sent.get("think") is False
        assert sent.get("options", {}).get("num_predict") == 384
        body = {
            "message": {
                "content": json.dumps(
                    {
                        "say": "Opening Terminal.",
                        "actions": [{"tool": "os.app.open", "args": {"name": "Terminal"}}],
                    }
                )
            }
        }
        return httpx.Response(200, json=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    planner = OllamaPlanner(client=client)
    plan = planner.plan("open Terminal")
    assert plan.say == "Opening Terminal."
    assert plan.actions[0].tool == "os.app.open"
    assert plan.actions[0].args["name"] == "Terminal"


def test_unreachable_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    planner = OllamaPlanner(client=client)
    try:
        planner.plan("hello")
        assert False, "expected ModelUnavailable"
    except ModelUnavailable:
        pass
