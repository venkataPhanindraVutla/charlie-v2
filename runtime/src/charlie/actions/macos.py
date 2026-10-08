from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _open_accessibility_settings() -> None:
    for url in (
        "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    ):
        subprocess.run(["open", url], capture_output=True)


class MacOsAdapter:
    def open_app(self, name: str) -> str:
        result = subprocess.run(
            ["open", "-a", name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not open {name}")
        return f"Opened {name}."

    def list_apps(self) -> list[str]:
        apps = Path("/Applications")
        if not apps.exists():
            return []
        return sorted(p.stem for p in apps.glob("*.app"))

    def open_file(self, path: str) -> str:
        result = subprocess.run(["open", path], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not open {path}")
        return f"Opened {path}."

    def open_folder(self, path: str) -> str:
        return self.open_file(path)

    def run_command(self, command: str) -> tuple[str, str, int]:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode

    def quick_switch(self, app: str, query: str, hotkey: str = "k") -> str:
        query = re.sub(r"[^A-Za-z0-9 ._-]", "", query).strip()[:80]
        if not query:
            raise RuntimeError("No name to search.")
        self.open_app(app)
        key = (hotkey or "k")[:1]
        script = f"""
tell application "{app}" to activate
delay 1.4
tell application "System Events"
  keystroke "{key}" using command down
  delay 0.5
  keystroke "{query}"
  delay 0.7
  key code 125
  delay 0.15
  keystroke return
end tell
"""
        result = subprocess.run(["osascript"], input=script, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            lowered = err.lower()
            if "not allowed" in lowered or "assistive" in lowered or "accessibility" in lowered:
                _open_accessibility_settings()
                raise RuntimeError(
                    "Accessibility has no Terminal row until you add it. Click +, press Cmd-Shift-G, "
                    "paste /Applications/Cursor.app, and toggle it on. Terminal.app lives in "
                    "/Applications/Utilities/ if you want that too."
                )
            raise RuntimeError(err or f"Could not jump to {query} in {app}.")
        return f"Opened {query} in {app}."
