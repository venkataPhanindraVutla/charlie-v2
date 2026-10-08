from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorldState:
    applications: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_capability: str | None = None
    last_observation: str = ""

    def mark_open(self, name: str) -> None:
        slot = self.applications.setdefault(name, {})
        slot["running"] = True
        slot["installed"] = True

    def is_running(self, name: str) -> bool:
        cached = self.applications.get(name, {}).get("running")
        if cached:
            return True
        return _process_mentions(name)

    def observe(self, capability: str, ok: bool, observation: str, args: dict[str, Any] | None = None) -> None:
        self.last_capability = capability
        self.last_observation = observation
        args = args or {}
        if ok and capability in {"apps.open", "os.app.open"}:
            self.mark_open(str(args.get("name") or ""))
        if ok and capability in {"apps.jump", "os.app.jump", "communication.send_message"}:
            self.mark_open(str(args.get("app") or args.get("name") or ""))

    def snapshot(self) -> str:
        running = [name for name, meta in self.applications.items() if meta.get("running")]
        return (
            f"running={running or '[]'} last={self.last_capability or 'none'} "
            f"note={self.last_observation[:160]}"
        )


def _process_mentions(name: str) -> bool:
    needle = (name or "").strip()
    if not needle:
        return False
    if sys.platform == "darwin":
        result = subprocess.run(["pgrep", "-if", needle], capture_output=True, text=True)
        return result.returncode == 0 and bool(result.stdout.strip())
    if sys.platform == "win32":
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Process -Name '{needle}' -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    result = subprocess.run(["pgrep", "-if", needle], capture_output=True, text=True)
    return result.returncode == 0
