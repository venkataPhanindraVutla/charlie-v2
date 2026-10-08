from __future__ import annotations

from typing import Any

from charlie.actions.registry import Registry, ToolResult
from charlie.cognition.planner import Action

SEMANTIC_TO_TOOL = {
    "apps.open": "os.app.open",
    "apps.list": "os.app.list",
    "apps.jump": "os.app.jump",
    "files.open": "os.file.open",
    "files.open_folder": "os.folder.open",
    "process.run": "os.terminal.run",
    "python.run": "python.run",
    "web.search": "web.search",
    "web.fetch": "web.fetch",
    "os.app.open": "os.app.open",
    "os.app.list": "os.app.list",
    "os.app.jump": "os.app.jump",
    "os.file.open": "os.file.open",
    "os.folder.open": "os.folder.open",
    "os.terminal.run": "os.terminal.run",
}

APP_HOTKEYS = {
    "slack": "k",
    "discord": "k",
    "whatsapp": "f",
    "messages": "f",
    "finder": "f",
}


class CapabilityHost:
    """In-process MCP: semantic names, deterministic execution, no LLM."""

    def __init__(self, registry: Registry | None = None) -> None:
        self.registry = registry or Registry()

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {"name": "apps.open", "description": "Open an installed application", "parameters": {"name": "string"}},
            {"name": "apps.list", "description": "List installed applications", "parameters": {}},
            {
                "name": "apps.jump",
                "description": "Open an app and search inside it for a person, channel, or file",
                "parameters": {"app": "string", "query": "string"},
            },
            {
                "name": "communication.send_message",
                "description": "Open a chat app, find a recipient, optionally type a message",
                "parameters": {"app": "string", "recipient": "string", "message": "string"},
            },
            {"name": "communication.find_contact", "description": "Jump to a contact in a chat app", "parameters": {"app": "string", "query": "string"}},
            {"name": "files.open", "description": "Open a file", "parameters": {"path": "string"}},
            {"name": "files.open_folder", "description": "Open a folder", "parameters": {"path": "string"}},
            {"name": "process.run", "description": "Run a shell command", "parameters": {"command": "string"}},
            {"name": "python.run", "description": "Run a Python script", "parameters": {"code": "string"}},
            {"name": "web.search", "description": "Search the public web", "parameters": {"query": "string"}},
            {"name": "web.fetch", "description": "Fetch a URL", "parameters": {"url": "string"}},
        ]

    def execute(self, capability: str, args: dict[str, Any]) -> ToolResult:
        if capability == "communication.send_message":
            return self._send_message(args)
        if capability == "communication.find_contact":
            return self._jump(
                {
                    "app": args.get("app"),
                    "query": args.get("query") or args.get("recipient"),
                }
            )
        if capability == "apps.jump":
            return self._jump(args)
        tool = SEMANTIC_TO_TOOL.get(capability, capability)
        mapped = dict(args)
        if tool == "os.app.open" and "name" not in mapped and mapped.get("app"):
            mapped["name"] = mapped["app"]
        if hasattr(self.registry, "execute"):
            return self.registry.execute(Action(tool=tool, args=mapped))
        raise RuntimeError(f"unknown capability {capability}")

    def _jump(self, args: dict[str, Any]) -> ToolResult:
        app = str(args.get("app") or args.get("name") or "")
        query = str(args.get("query") or args.get("recipient") or "")
        hotkey = args.get("hotkey") or APP_HOTKEYS.get(app.lower(), "f")
        return self.registry.execute(
            Action(tool="os.app.jump", args={"app": app, "query": query, "hotkey": hotkey})
        )

    def _send_message(self, args: dict[str, Any]) -> ToolResult:
        app = str(args.get("app") or args.get("name") or "")
        query = str(args.get("recipient") or args.get("query") or "")
        message = str(args.get("message") or args.get("text") or "").strip()
        hotkey = args.get("hotkey") or APP_HOTKEYS.get(app.lower(), "f")
        return self.registry.execute(
            Action(
                tool="os.chat.send",
                args={"app": app, "query": query, "message": message, "hotkey": hotkey},
            )
        )
