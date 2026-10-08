from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ModelUnavailable(Exception):
    """Local Ollama (or other provider) is not reachable."""


@dataclass
class Action:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    actions: list[Action]
    say: str = ""
    done: bool = True
    domain: str = "apps"
    steps: list[Any] = field(default_factory=list)


class Planner:
    def plan(
        self,
        text: str,
        history: list[dict[str, str]] | None = None,
        current_task: str | None = None,
        observations: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> Plan:
        raise NotImplementedError


class FakePlanner(Planner):
    def __init__(self, actions: list[dict[str, Any]] | None = None, say: str = "Opening it.", done: bool = True) -> None:
        self._actions = [Action(tool=a["tool"], args=a.get("args", {})) for a in (actions or [])]
        self._say = say
        self._done = done
        self.last_text = ""
        self.last_history: list[dict[str, str]] = []
        self.last_task: str | None = None
        self.last_observations: list[dict[str, Any]] = []
        self.last_tools: list[dict[str, Any]] = []

    def plan(
        self,
        text: str,
        history: list[dict[str, str]] | None = None,
        current_task: str | None = None,
        observations: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> Plan:
        self.last_text = text
        self.last_history = list(history or [])
        self.last_task = current_task
        self.last_observations = list(observations or [])
        self.last_tools = list(tools or [])
        return Plan(actions=list(self._actions), say=self._say, done=self._done)
