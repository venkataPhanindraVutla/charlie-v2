from __future__ import annotations

from dataclasses import dataclass

from charlie.harness.broker import CallResult
from charlie.harness.task import TaskStep
from charlie.harness.world import WorldState


@dataclass
class Verdict:
    success: bool
    recoverable: bool = False
    needs_replan: bool = False
    needs_user: bool = False
    reason: str = ""


class Verifier:
    def verify(self, step: TaskStep, result: CallResult, world: WorldState) -> Verdict:
        if not result.ok:
            recoverable = step.attempts < step.max_attempts
            return Verdict(success=False, recoverable=recoverable, reason=result.observation)
        required = step.success or {}
        app = required.get("app_running") or required.get("application_running")
        if app and not world.is_running(str(app)):
            return Verdict(
                success=False,
                recoverable=step.attempts < step.max_attempts,
                reason=f"{app} is not running.",
            )
        return Verdict(success=True, reason=result.observation)
