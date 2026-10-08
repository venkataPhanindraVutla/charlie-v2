from __future__ import annotations

from typing import Any

from charlie.actions.registry import Registry
from charlie.cognition.laya import Decider
from charlie.cognition.planner import Planner
from charlie.harness.broker import ToolBroker
from charlie.harness.runtime import Harness
from charlie.memory.store import Store
from charlie.mcp.capabilities import CapabilityHost


class Engine:
    """Interface façade. The harness owns the loop."""

    def __init__(
        self,
        planner: Planner,
        registry: Registry | None = None,
        memory: Store | None = None,
        host: CapabilityHost | None = None,
        decider: Decider | None = None,
    ) -> None:
        self.planner = planner
        self.registry = registry
        self.memory = memory
        if host is None:
            if registry is not None and hasattr(registry, "execute") and not isinstance(registry, Registry):
                host = _RegistryHost(registry)
            else:
                host = CapabilityHost(registry=registry if isinstance(registry, Registry) else registry)
        self.harness = Harness(
            planner=planner,
            broker=ToolBroker(host),
            memory=memory,
            decider=decider or Decider(router=None),
        )
        self.current_task: str | None = None
        self.last_summary: str = ""

    def run_turn(self, text: str, source: str = "text") -> list[dict[str, Any]]:
        events = self.harness.run_turn(text, source)
        self.last_summary = self.harness.last_summary
        self.current_task = self.harness.current.goal if self.harness.current else text.strip()
        return events


class _RegistryHost:
    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def schemas(self) -> list[dict[str, Any]]:
        if hasattr(self.registry, "schemas"):
            return self.registry.schemas()
        return []

    def execute(self, capability: str, args: dict[str, Any]) -> Any:
        from charlie.cognition.planner import Action

        return self.registry.execute(Action(tool=capability, args=args))
