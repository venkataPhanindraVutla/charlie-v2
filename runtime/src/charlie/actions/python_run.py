from __future__ import annotations

import contextlib
import io
import traceback


def run_python(code: str) -> str:
    if not code or not str(code).strip():
        raise RuntimeError("Missing python code.")
    source = str(code)
    if len(source) > 20000:
        raise RuntimeError("Script too long.")
    namespace: dict = {"__name__": "__charlie__"}
    try:
        import pyautogui

        namespace["pyautogui"] = pyautogui
    except ImportError:
        pass
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(source, "<charlie>", "exec"), namespace, namespace)
    except Exception:
        return (buf.getvalue() + "\n" + traceback.format_exc()).strip()[-4000:]
    out = buf.getvalue().strip()
    return out or "ok"
