from __future__ import annotations

import json
from typing import Any

import httpx

from charlie.cognition.planner import Action, ModelUnavailable, Plan, Planner
from charlie.cognition.personality import SYSTEM_PROMPT

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "say": {"type": "string"},
        "done": {"type": "boolean"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["tool"],
            },
        },
    },
    "required": ["say", "actions"],
}


class OllamaPlanner(Planner):
    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "qwen3:4b",
        client: httpx.Client | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self._client = client

    def plan(
        self,
        text: str,
        history: list[dict[str, str]] | None = None,
        current_task: str | None = None,
        observations: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> Plan:
        history_lines = []
        for turn in (history or [])[-8:]:
            role = turn.get("role", "user")
            history_lines.append(f"{role}: {turn.get('text', '')}")
        history_block = "\n".join(history_lines) or "(none)"
        tool_lines = []
        for spec in tools or []:
            params = ", ".join((spec.get("parameters") or {}).keys()) or "(none)"
            tool_lines.append(f"- {spec['name']} {{{params}}} — {spec.get('description', '')}")
        tools_block = "\n".join(tool_lines) or "(none)"
        obs_lines = []
        for i, obs in enumerate(observations or [], start=1):
            snippet = str(obs.get("observation") or "")[:800]
            obs_lines.append(f"{i}. {obs.get('tool')} ok={obs.get('ok')}\n{snippet}")
        obs_block = "\n".join(obs_lines) or "(none yet)"
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "format": PLAN_SCHEMA,
            "options": {"temperature": 0.2, "num_predict": 512},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Choose tools yourself. Emit a JSON plan.\n"
                        f"Tools:\n{tools_block}\n"
                        f"Current task: {current_task or text}\n"
                        f"Recent turns:\n{history_block}\n"
                        f"Tool results so far:\n{obs_block}\n"
                        f"Now: {text}\n"
                        "If results already finish the task, set done=true and actions=[]. "
                        "Otherwise set done=false and emit the next actions."
                    ),
                },
            ],
        }
        client = self._client or httpx.Client(timeout=httpx.Timeout(120.0, connect=2.0))
        owns = self._client is None
        try:
            response = client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelUnavailable(str(exc)) from exc
        finally:
            if owns:
                client.close()

        body = response.json()
        content = body.get("message", {}).get("content") or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ModelUnavailable("planner returned non-JSON") from exc
        actions = [
            Action(tool=item["tool"], args=item.get("args") or {})
            for item in data.get("actions") or []
            if isinstance(item, dict) and item.get("tool")
        ]
        done = True if "done" not in data else bool(data.get("done"))
        return Plan(actions=actions, say=data.get("say") or "Done.", done=done)
