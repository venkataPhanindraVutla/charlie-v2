from __future__ import annotations

import re
from typing import Any

from charlie.cognition.laya import Decider
from charlie.cognition.personality import render_reply
from charlie.cognition.planner import ModelUnavailable, Plan, Planner
from charlie.harness.broker import ToolBroker
from charlie.harness.policy import (
    COMMS_RE,
    LIVE_LOOKUP,
    WANTS_SEND_RE,
    constrain,
    infer_domain,
    schemas_for,
    step_permitted,
)
from charlie.harness.recovery import Recovery
from charlie.harness.task import Task, TaskStatus, TaskStep
from charlie.harness.verifier import Verifier
from charlie.harness.world import WorldState
from charlie.memory.store import Store
from charlie.mcp.capabilities import CapabilityHost

PROGRESS = ("progress", "status", "update", "are you done", "what happened")
LEAKED = {"name", "path", "command", "query", "app", "tool", "args"}
PROMISE_RE = re.compile(
    r"\b(i('ll| will)|let me)\s+(check|look|search|find|help)\b|"
    r"i'll check",
    re.I,
)
CLAIM_SENT_RE = re.compile(
    r"\b(i('ve| have)? sent|sent this|sent it|sent the)\b",
    re.I,
)


class Harness:
    def __init__(
        self,
        planner: Planner,
        broker: ToolBroker,
        memory: Store | None = None,
        decider: Decider | None = None,
        world: WorldState | None = None,
    ) -> None:
        self.planner = planner
        self.broker = broker
        self.memory = memory
        self.decider = decider or Decider()
        self.world = world or WorldState()
        self.verifier = Verifier()
        self.recovery = Recovery()
        self.current: Task | None = None
        self.last_summary: str = ""
        self.last_domain: str = ""

    def run_turn(self, text: str, source: str = "text") -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = [{"type": "status", "state": "thinking"}]
        if self.memory:
            self.memory.log_event("turn", f"{source}: {text}")
            self.memory.add_turn("user", text)

        domain = infer_domain(text, self.last_domain)
        if domain == "status":
            reply = self.last_summary or "I haven't sent anything yet."
            return self._finish(events, reply)
        if self._is_progress(text) and self.current and self.current.status == TaskStatus.running:
            reply = f"Still on: {self.current.goal}. {self.last_summary}".strip()
            return self._finish(events, reply)

        history = self.memory.recent_turns(12) if self.memory else []
        comms = domain == "communication"
        tools = []
        if hasattr(self.broker.host, "schemas"):
            tools = schemas_for(text, self.broker.host.schemas(), comms=comms)
        try:
            plan = self.planner.plan(
                text,
                history=history,
                current_task=text.strip(),
                observations=[],
                tools=tools,
            )
        except ModelUnavailable:
            return self._finish(events, "I can't reach the local model. Is Ollama running?", error=True)

        task = _task_from_plan(text.strip(), plan)
        task.domain = domain
        if domain == "talk":
            task.steps = [
                step
                for step in task.steps
                if step.capability in LIVE_LOOKUP
                and step_permitted(text, step.capability, step.args, comms=comms)
            ]
        else:
            task.steps = [
                step
                for step in task.steps
                if step_permitted(text, step.capability, step.args, comms=comms)
            ]
        _fold_comms(task, text, history)
        if domain != "talk":
            self.last_domain = domain
        self.current = task
        task.status = TaskStatus.running
        if not task.steps:
            reply = plan.say or "I'm here."
            if domain == "talk" and COMMS_RE.search(reply):
                reply = "I'm here."
            self.last_summary = reply
            return self._finish(events, reply)

        events.append({"type": "status", "state": "acting"})
        while task.current and task.status == TaskStatus.running:
            step = task.current
            step.attempts += 1
            candidates = constrain(task.domain, step.allowed_actions)
            capability = self.decider.choose(self.world.snapshot(), step.objective, candidates)
            result = self.broker.call(capability, step.args, allowed=step.allowed_actions)
            self.world.observe(capability, result.ok, result.observation, step.args)
            task.observations.append(
                {"tool": result.capability, "ok": result.ok, "observation": result.observation}
            )
            events.append(
                {
                    "type": "event",
                    "tool": result.capability,
                    "ok": result.ok,
                    "summary": result.observation,
                }
            )
            if self.memory:
                self.memory.log_event("tool", f"{result.capability} ok={result.ok}")
            verdict = self.verifier.verify(step, result, self.world)
            if verdict.success:
                task.advance()
                continue
            action = self.recovery.handle(task, verdict)
            if action == "retry":
                continue
            break

        reply = self._report(text, history, plan.say, task)
        self.last_summary = reply
        return self._finish(events, reply, error=task.status == TaskStatus.failed)

    def _report(self, text: str, history: list, say: str, task: Task) -> str:
        if task.status != TaskStatus.failed and task.observations:
            try:
                report = self.planner.plan(
                    text,
                    history=history,
                    current_task=text.strip(),
                    observations=task.observations,
                    tools=[],
                )
                spoken = (report.say or "").strip()
                if spoken and not PROMISE_RE.search(spoken) and not _false_sent(spoken, task):
                    return render_reply(spoken)
            except ModelUnavailable:
                pass
        return _reply(say, task)

    def _is_progress(self, text: str) -> bool:
        lowered = text.strip().lower()
        return any(token in lowered for token in PROGRESS)

    def _finish(self, events: list[dict[str, Any]], reply: str, error: bool = False) -> list[dict[str, Any]]:
        text = render_reply(reply)
        events.append({"type": "status", "state": "error" if error else "done"})
        events.append({"type": "assistant.done", "text": text})
        events.append({"type": "speak", "text": text})
        if self.memory:
            self.memory.log_event("reply", text)
            self.memory.add_turn("assistant", text)
        return events


def _task_from_plan(goal: str, plan: Plan) -> Task:
    domain = getattr(plan, "domain", None) or infer_domain(goal)
    steps: list[TaskStep] = list(getattr(plan, "steps", None) or [])
    if not steps:
        for action in plan.actions or []:
            steps.append(
                TaskStep(
                    objective=action.tool,
                    capability=action.tool,
                    args=dict(action.args or {}),
                    allowed_actions=[action.tool],
                )
            )
    return Task(goal=goal, domain=domain, steps=steps, say=plan.say or "")


def _reply(say: str, task: Task) -> str:
    if task.status == TaskStatus.failed:
        fail = next((o.get("text") for o in reversed(task.observations) if o.get("kind") == "fail"), "")
        last = task.observations[-1]["observation"] if task.observations else "Failed."
        return fail or last
    text = (say or "").strip().strip("'\"")
    if text.lower() in LEAKED:
        text = ""
    if _false_sent(text, task):
        text = ""
    facts = [
        str(item.get("observation") or "")
        for item in task.observations
        if item.get("ok") and item.get("tool") in LIVE_LOOKUP
    ]
    if facts and not _sent(task):
        blob = facts[-1].strip()
        if blob:
            return blob[:280]
    if text:
        return text
    if task.observations:
        return str(task.observations[-1].get("observation") or "Done.")
    return "Done."


def _sent(task: Task) -> bool:
    return any(
        item.get("ok") and item.get("tool") == "communication.send_message"
        for item in task.observations
    )


def _false_sent(say: str, task: Task) -> bool:
    return bool(CLAIM_SENT_RE.search(say or "")) and not _sent(task)


def _message_from_history(history: list, text: str = "") -> str:
    for turn in reversed(history or []):
        if turn.get("role") != "assistant":
            continue
        body = (turn.get("text") or "").strip()
        if not body:
            continue
        if CLAIM_SENT_RE.search(body) or PROMISE_RE.search(body):
            continue
        if body.lower() in {"i'm here.", "i'm here", "done."}:
            continue
        return body[:1500]
    return (text or "").strip()[:1500]


def _fold_comms(task: Task, text: str, history: list) -> None:
    if not WANTS_SEND_RE.search(text or ""):
        return
    jumps = {"apps.jump", "communication.find_contact", "os.app.jump"}
    sends = [step for step in task.steps if step.capability == "communication.send_message"]
    jump_steps = [step for step in task.steps if step.capability in jumps]
    if sends:
        for step in sends:
            if not str(step.args.get("message") or "").strip():
                step.args["message"] = _message_from_history(history, text)
            if not step.args.get("recipient"):
                step.args["recipient"] = step.args.get("query")
            if not step.args.get("query"):
                step.args["query"] = step.args.get("recipient")
        task.steps = [step for step in task.steps if step.capability not in jumps]
        return
    if not jump_steps:
        return
    jump = jump_steps[0]
    recipient = str(jump.args.get("query") or jump.args.get("recipient") or "")
    app = str(jump.args.get("app") or jump.args.get("name") or "WhatsApp")
    task.steps = [
        TaskStep(
            objective="send message",
            capability="communication.send_message",
            args={
                "app": app,
                "recipient": recipient,
                "query": recipient,
                "message": _message_from_history(history, text),
                "hotkey": jump.args.get("hotkey"),
            },
        )
    ]
