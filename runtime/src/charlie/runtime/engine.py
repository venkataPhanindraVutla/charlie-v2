from __future__ import annotations

from typing import Any

from charlie.actions.registry import Registry, ToolResult
from charlie.cognition.personality import render_reply
from charlie.cognition.planner import ModelUnavailable, Planner
from charlie.memory.store import Store

MAX_STEPS = 8
LEAKED_SAY = {"name", "path", "command", "query", "app", "tool", "args"}


class Engine:
    def __init__(
        self,
        planner: Planner,
        registry: Registry | None = None,
        memory: Store | None = None,
    ) -> None:
        self.planner = planner
        self.registry = registry or Registry()
        self.memory = memory
        self.current_task: str | None = None
        self.last_summary: str = ""

    def run_turn(self, text: str, source: str = "text") -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = [{"type": "status", "state": "thinking"}]
        if self.memory:
            self.memory.log_event("turn", f"{source}: {text}")
            self.memory.add_turn("user", text)

        history = self.memory.recent_turns(12) if self.memory else []
        self.current_task = text.strip()
        observations: list[dict[str, Any]] = []
        results: list[ToolResult] = []
        say = "Done."
        tools = self.registry.schemas() if hasattr(self.registry, "schemas") else []

        try:
            for _ in range(MAX_STEPS):
                plan = self.planner.plan(
                    text,
                    history=history,
                    current_task=self.current_task,
                    observations=observations,
                    tools=tools,
                )
                say = plan.say or say
                if not plan.actions:
                    break
                events.append({"type": "status", "state": "acting"})
                for action in plan.actions:
                    result = self.registry.execute(action)
                    results.append(result)
                    observation = {
                        "tool": result.tool,
                        "ok": result.ok,
                        "observation": result.observation,
                    }
                    observations.append(observation)
                    events.append(
                        {
                            "type": "event",
                            "tool": result.tool,
                            "ok": result.ok,
                            "summary": result.observation,
                        }
                    )
                    if self.memory:
                        self.memory.log_event("tool", f"{result.tool} ok={result.ok}")
                if plan.done:
                    break
        except ModelUnavailable:
            return self._finish(events, "I can't reach the local model. Is Ollama running?", error=True)

        reply = self._reply_after(say, results)
        self.last_summary = reply
        return self._finish(events, reply)

    def _finish(self, events: list[dict[str, Any]], reply: str, error: bool = False) -> list[dict[str, Any]]:
        text = render_reply(reply)
        events.append({"type": "status", "state": "error" if error else "done"})
        events.append({"type": "assistant.done", "text": text})
        events.append({"type": "speak", "text": text})
        if self.memory:
            self.memory.log_event("reply", text)
            self.memory.add_turn("assistant", text)
        return events

    def _reply_after(self, say: str, results: list[ToolResult]) -> str:
        fails = [r.observation for r in results if not r.ok]
        if fails and not any(r.ok for r in results):
            return fails[0]
        text = (say or "").strip().strip("'\"")
        if text.lower() in LEAKED_SAY:
            text = ""
        if text:
            return text
        if results:
            return results[-1].observation
        return "Done."
