from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


class WindowsAdapter:
    def open_app(self, name: str) -> str:
        # Prefer launching by name through cmd start; avoid the v1 Win-key GUI hack.
        result = subprocess.run(
            ["cmd", "/c", "start", "", name],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not open {name}")
        return f"Opened {name}."

    def list_apps(self) -> list[str]:
        roots = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ]
        names: list[str] = []
        for root in roots:
            if root.exists():
                names.extend(p.name for p in root.iterdir() if p.is_dir())
        return sorted(set(names))

    def open_file(self, path: str) -> str:
        os.startfile(path)  # type: ignore[attr-defined]
        return f"Opened {path}."

    def open_folder(self, path: str) -> str:
        return self.open_file(path)

    def run_command(self, command: str) -> tuple[str, str, int]:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode

    def quick_switch(self, app: str, query: str, hotkey: str = "k") -> str:
        query = re.sub(r"[^A-Za-z0-9 ._-]", "", query).strip()[:80]
        if not query:
            raise RuntimeError("No name to search.")
        self.open_app(app)
        escaped = query.replace("'", "''")
        send = "^" + (hotkey or "k")[:1]
        script = (
            "Start-Sleep -Seconds 1;"
            "Add-Type -AssemblyName System.Windows.Forms;"
            f"[System.Windows.Forms.SendKeys]::SendWait('{send}');"
            "Start-Sleep -Milliseconds 500;"
            f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}');"
            "Start-Sleep -Milliseconds 600;"
            "[System.Windows.Forms.SendKeys]::SendWait('{DOWN}');"
            "Start-Sleep -Milliseconds 150;"
            "[System.Windows.Forms.SendKeys]::SendWait('{ENTER}');"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not jump to {query} in {app}.")
        return f"Opened {query} in {app}."
