from __future__ import annotations

from charlie.harness.task import Task, TaskStatus
from charlie.harness.verifier import Verdict


class Recovery:
    def handle(self, task: Task, verdict: Verdict) -> str:
        step = task.current
        if step is None:
            task.fail(verdict.reason)
            return "fail"
        if verdict.recoverable and step.attempts < step.max_attempts:
            return "retry"
        if verdict.needs_user:
            task.status = TaskStatus.waiting_user
            return "ask"
        if verdict.needs_replan:
            return "replan"
        task.fail(verdict.reason)
        return "fail"
