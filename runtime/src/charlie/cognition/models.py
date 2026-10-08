from __future__ import annotations

import json
from typing import Any

import httpx

from charlie.cognition.planner import Action, ModelUnavailable, Plan, Planner
from charlie.cognition.personality import SYSTEM_PROMPT
from charlie.harness.task import TaskStep

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "say": {"type": "string"},
        "domain": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "objective": {"type": "string"},
                    "capability": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["capability"],
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                },
            },
        },
    },
    "required": ["say"],
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
        cap_lines = []
        for spec in tools or []:
            params = ", ".join((spec.get("parameters") or {}).keys()) or "(none)"
            cap_lines.append(f"- {spec['name']} {{{params}}}")
        caps = "\n".join(cap_lines) or "(none)"
        obs_block = json.dumps(observations or [], ensure_ascii=False)
        if len(obs_block) > 3500:
            obs_block = obs_block[:3500] + "…"
        reporting = bool(observations)
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "format": PLAN_SCHEMA,
            "options": {"temperature": 0.1, "num_predict": 384},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Plan ONLY this line. Do not repeat WhatsApp/Slack from history unless this line asks for it.\n"
                        "If observations are present, return steps=[] and write say from those facts.\n"
                        "If no OS action is needed and this is not a live-fact lookup, return steps=[].\n"
                        f"Capabilities:\n{'(none — answer only)' if reporting else caps}\n"
                        f"Current task: {current_task or text}\n"
                        f"Recent turns:\n{history_block}\n"
                        f"Observations:\n{obs_block if reporting else '(none)'}\n"
                        f"Now: {text}"
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
        steps = []
        for item in data.get("steps") or []:
            if not isinstance(item, dict) or not item.get("capability"):
                continue
            steps.append(
                TaskStep(
                    objective=str(item.get("objective") or item["capability"]),
                    capability=str(item["capability"]),
                    args=item.get("args") or {},
                )
            )
        actions = [
            Action(tool=item["tool"], args=item.get("args") or {})
            for item in data.get("actions") or []
            if isinstance(item, dict) and item.get("tool")
        ]
        return Plan(
            actions=actions,
            say=data.get("say") or "Done.",
            done=not steps and not actions,
            domain=str(data.get("domain") or "apps"),
            steps=steps,
        )
