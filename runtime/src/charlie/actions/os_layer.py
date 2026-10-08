from __future__ import annotations

import sys
from typing import Protocol


class OsAdapter(Protocol):
    def open_app(self, name: str) -> str: ...
    def list_apps(self) -> list[str]: ...
    def open_file(self, path: str) -> str: ...
    def open_folder(self, path: str) -> str: ...
    def run_command(self, command: str) -> tuple[str, str, int]: ...
    def quick_switch(self, app: str, query: str, hotkey: str = "k") -> str: ...


def current_adapter() -> OsAdapter:
    if sys.platform == "darwin":
        from charlie.actions.macos import MacOsAdapter

        return MacOsAdapter()
    if sys.platform == "win32":
        from charlie.actions.windows import WindowsAdapter

        return WindowsAdapter()
    from charlie.actions.macos import MacOsAdapter

    return MacOsAdapter()
