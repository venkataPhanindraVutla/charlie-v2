from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from charlie.actions import computer, web
from charlie.actions.os_layer import OsAdapter, current_adapter
from charlie.actions.python_run import run_python
from charlie.cognition.planner import Action


@dataclass
class ToolResult:
    ok: bool
    observation: str
    tool: str


def _letter(hotkey: object) -> str:
    raw = str(hotkey or "k").lower()
    for prefix in ("command+", "cmd+", "ctrl+", "control+", "meta+"):
        raw = raw.replace(prefix, "")
    raw = raw.replace("+", "")
    for ch in reversed(raw):
        if ch.isalnum():
            return ch
    return "k"


class Registry:
    def __init__(self, adapter: OsAdapter | None = None) -> None:
        self.adapter = adapter or current_adapter()
        self._handlers: dict[str, Callable[[dict[str, Any]], str]] = {
            "os.app.open": self._open_app,
            "os.app.list": self._list_apps,
            "os.file.open": self._open_file,
            "os.folder.open": self._open_folder,
            "os.terminal.run": self._run_command,
            "os.app.jump": self._jump,
            "os.chat.send": self._chat_send,
            "computer.hotkey": lambda a: computer.hotkey(a.get("keys") or a.get("key")),
            "computer.type": lambda a: computer.type_text(str(a.get("text") or ""), float(a.get("interval") or 0.02)),
            "computer.press": lambda a: computer.press(str(a.get("key") or "")),
            "computer.click": lambda a: computer.click(a.get("x"), a.get("y"), str(a.get("button") or "left"), a.get("clicks") or 1),
            "computer.move": lambda a: computer.move(a.get("x"), a.get("y")),
            "computer.position": lambda a: computer.position(),
            "computer.screenshot": lambda a: computer.screenshot(a.get("path")),
            "computer.sleep": lambda a: computer.sleep(a.get("seconds", a.get("n", 0))),
            "python.run": lambda a: run_python(str(a.get("code") or a.get("script") or "")),
            "web.search": lambda a: web.search(str(a.get("query") or ""), int(a.get("limit") or 5)),
            "web.fetch": lambda a: web.fetch(str(a.get("url") or "")),
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {"name": "os.app.open", "description": "Open an installed application by name", "parameters": {"name": "string"}},
            {"name": "os.app.list", "description": "List installed applications", "parameters": {}},
            {"name": "os.file.open", "description": "Open a file with the default app", "parameters": {"path": "string"}},
            {"name": "os.folder.open", "description": "Open a folder in the file manager", "parameters": {"path": "string"}},
            {"name": "os.terminal.run", "description": "Run a local shell command and capture stdout/stderr", "parameters": {"command": "string"}},
            {
                "name": "os.app.jump",
                "description": "Open an app, focus it, press its search hotkey, type a query, hit enter. Pass hotkey: k for Slack/Discord, f for WhatsApp and most search boxes.",
                "parameters": {"app": "string", "query": "string", "hotkey": "string"},
            },
            {"name": "computer.hotkey", "description": "Press a modifier combo via pyautogui, e.g. keys command+f or [command,f]", "parameters": {"keys": "string"}},
            {"name": "computer.type", "description": "Type text into the focused UI", "parameters": {"text": "string"}},
            {"name": "computer.press", "description": "Press one key (enter, down, tab, escape, ...)", "parameters": {"key": "string"}},
            {"name": "computer.click", "description": "Click. Optional x,y; otherwise current pointer.", "parameters": {"x": "number", "y": "number", "button": "string", "clicks": "number"}},
            {"name": "computer.move", "description": "Move the pointer", "parameters": {"x": "number", "y": "number"}},
            {"name": "computer.position", "description": "Return current pointer x,y", "parameters": {}},
            {"name": "computer.screenshot", "description": "Save a screenshot and return its path", "parameters": {"path": "string"}},
            {"name": "computer.sleep", "description": "Wait up to 15 seconds", "parameters": {"seconds": "number"}},
            {"name": "python.run", "description": "Execute a Python script. pyautogui is in scope if installed. Print what you need to see.", "parameters": {"code": "string"}},
            {"name": "web.search", "description": "Search the public web. Use when the machine cannot answer.", "parameters": {"query": "string"}},
            {"name": "web.fetch", "description": "GET a URL and return extracted text", "parameters": {"url": "string"}},
        ]

    def execute(self, action: Action | dict[str, Any]) -> ToolResult:
        if isinstance(action, dict):
            action = Action(tool=action["tool"], args=action.get("args") or {})
        tool = action.tool
        handler = self._handlers.get(tool)
        if handler is None:
            return ToolResult(ok=False, observation=f"Unknown tool: {tool}", tool=tool)
        try:
            observation = handler(action.args or {})
            return ToolResult(ok=True, observation=str(observation), tool=tool)
        except Exception as exc:
            return ToolResult(ok=False, observation=str(exc), tool=tool)

    def _open_app(self, args: dict[str, Any]) -> str:
        name = args.get("name")
        if not name:
            raise RuntimeError("Missing app name.")
        return self.adapter.open_app(str(name))

    def _list_apps(self, args: dict[str, Any]) -> str:
        names = self.adapter.list_apps()
        return ", ".join(names[:40]) or "No apps found."

    def _open_file(self, args: dict[str, Any]) -> str:
        path = args.get("path")
        if not path:
            raise RuntimeError("Missing file path.")
        return self.adapter.open_file(str(path))

    def _open_folder(self, args: dict[str, Any]) -> str:
        path = args.get("path")
        if not path:
            raise RuntimeError("Missing folder path.")
        return self.adapter.open_folder(str(path))

    def _run_command(self, args: dict[str, Any]) -> str:
        command = args.get("command")
        if not command:
            raise RuntimeError("Missing command.")
        stdout, stderr, code = self.adapter.run_command(str(command))
        return _truncate_command_output(stdout, stderr, code)

    def _jump(self, args: dict[str, Any]) -> str:
        app = args.get("app")
        query = args.get("query")
        if not app or not query:
            raise RuntimeError("Missing app or search name.")
        return self.adapter.quick_switch(str(app), str(query), hotkey=_letter(args.get("hotkey")))

    def _chat_send(self, args: dict[str, Any]) -> str:
        app = args.get("app") or args.get("name")
        query = args.get("query") or args.get("recipient")
        message = args.get("message") or args.get("text")
        if not app or not query:
            raise RuntimeError("Missing app or recipient.")
        if not str(message or "").strip():
            raise RuntimeError("Missing message.")
        return self.adapter.compose_message(
            str(app), str(query), str(message), hotkey=_letter(args.get("hotkey") or "f")
        )


def _truncate_command_output(stdout: str, stderr: str, code: int) -> str:
    combined = f"exit {code}\n{stdout}\n{stderr}".strip()
    lowered = combined.lower()
    if any(flag in lowered for flag in ("api_key", "secret=", "password=", "begin private key")):
        return f"exit {code}\n[output withheld: possible secret]"
    if len(combined) > 4000:
        return combined[:4000] + "\n[truncated]"
    return combined
