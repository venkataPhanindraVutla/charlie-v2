from __future__ import annotations

from typing import Any


class Decider:
    """Tactical chooser. Laya Router when installed; else first allowed action."""

    def __init__(self, router: Any | None = None, *, load: bool = False) -> None:
        self.router = _try_router() if load and router is None else router

    def choose(self, state: str, objective: str, candidates: list[str]) -> str:
        if not candidates:
            raise ValueError("no candidates")
        if len(candidates) == 1 or self.router is None:
            return candidates[0]
        questions = {
            "next": {
                "type": "choice",
                "instructions": f"Which capability should run next for: {objective}",
                "options": list(candidates),
            }
        }
        result = self.router.predict(state, questions)
        choice = result.get("answers", {}).get("next", {}).get("choice")
        if choice in candidates:
            return str(choice)
        return candidates[0]


def _try_router() -> Any | None:
    try:
        from laya import Router

        return Router(max_loaded=1)
    except Exception:
        return None
