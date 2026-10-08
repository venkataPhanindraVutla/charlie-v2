from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    pending = "pending"
    planning = "planning"
    running = "running"
    waiting_user = "waiting_user"
    done = "done"
    failed = "failed"


@dataclass
class TaskStep:
    objective: str
    capability: str
    args: dict[str, Any] = field(default_factory=dict)
    allowed_actions: list[str] = field(default_factory=list)
    success: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 2
    id: str = field(default_factory=lambda: uuid4().hex[:8])

    def __post_init__(self) -> None:
        if not self.allowed_actions:
            self.allowed_actions = [self.capability]


@dataclass
class Task:
    goal: str
    domain: str = "apps"
    status: TaskStatus = TaskStatus.pending
    steps: list[TaskStep] = field(default_factory=list)
    current_index: int = 0
    observations: list[dict[str, Any]] = field(default_factory=list)
    say: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:10])

    @property
    def current(self) -> TaskStep | None:
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self) -> None:
        self.current_index += 1
        if self.current_index >= len(self.steps):
            self.status = TaskStatus.done

    def fail(self, reason: str = "") -> None:
        self.status = TaskStatus.failed
        if reason:
            self.observations.append({"kind": "fail", "text": reason})
