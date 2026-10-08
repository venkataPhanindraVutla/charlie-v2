from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

CACHEABLE = {"apps.list", "os.app.list", "web.search", "web.fetch"}


class CapabilityHost(Protocol):
    def execute(self, capability: str, args: dict[str, Any]) -> Any: ...


@dataclass
class CallResult:
    ok: bool
    observation: str
    capability: str


class ToolBroker:
    def __init__(self, host: CapabilityHost, ttl_s: float = 20.0) -> None:
        self.host = host
        self.ttl_s = ttl_s
        self._cache: dict[str, tuple[float, CallResult]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(
        self,
        capability: str,
        args: dict[str, Any] | None = None,
        allowed: list[str] | None = None,
    ) -> CallResult:
        args = dict(args or {})
        if allowed is not None and capability not in allowed:
            return CallResult(
                ok=False,
                observation=f"{capability} is not allowed for this step.",
                capability=capability,
            )
        key = _cache_key(capability, args)
        if capability in CACHEABLE:
            hit = self._cache.get(key)
            if hit and time.monotonic() - hit[0] < self.ttl_s:
                return hit[1]
        self.calls.append((capability, args))
        raw = self.host.execute(capability, args)
        result = _as_result(capability, raw)
        if capability in CACHEABLE and result.ok:
            self._cache[key] = (time.monotonic(), result)
        return result


def _cache_key(capability: str, args: dict[str, Any]) -> str:
    blob = json.dumps({"c": capability, "a": args}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _as_result(capability: str, raw: Any) -> CallResult:
    if hasattr(raw, "ok") and hasattr(raw, "observation"):
        return CallResult(ok=bool(raw.ok), observation=str(raw.observation), capability=capability)
    if isinstance(raw, dict):
        return CallResult(ok=bool(raw.get("ok", True)), observation=str(raw.get("observation") or raw), capability=capability)
    return CallResult(ok=True, observation=str(raw), capability=capability)
