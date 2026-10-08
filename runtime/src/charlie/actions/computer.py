from __future__ import annotations

import time
from pathlib import Path


def _gui():
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError("pyautogui is not installed in the Charlie runtime.") from exc
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui


def _keys(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    else:
        text = str(raw).replace("command", "command").strip()
        text = text.replace("+", ",").replace(" ", ",")
        parts = [p.strip() for p in text.split(",") if p.strip()]
    alias = {"cmd": "command", "ctrl": "ctrl", "control": "ctrl", "opt": "option", "return": "enter"}
    return [alias.get(p.lower(), p.lower()) for p in parts]


def hotkey(keys: object) -> str:
    parsed = _keys(keys)
    if not parsed:
        raise RuntimeError("Missing keys.")
    gui = _gui()
    gui.hotkey(*parsed)
    return f"Pressed {'+'.join(parsed)}."


def type_text(text: str, interval: float = 0.02) -> str:
    if not text:
        raise RuntimeError("Missing text.")
    gui = _gui()
    gui.write(str(text)[:2000], interval=min(max(interval, 0.0), 0.2))
    return f"Typed {len(text)} characters."


def press(key: str) -> str:
    if not key:
        raise RuntimeError("Missing key.")
    gui = _gui()
    gui.press(str(key))
    return f"Pressed {key}."


def click(x: object = None, y: object = None, button: str = "left", clicks: object = 1) -> str:
    gui = _gui()
    n = int(clicks or 1)
    if x is None or y is None:
        gui.click(button=button, clicks=n)
        return f"Clicked {button} at current position."
    gui.click(int(x), int(y), button=button, clicks=n)
    return f"Clicked {button} at {int(x)},{int(y)}."


def move(x: object, y: object) -> str:
    if x is None or y is None:
        raise RuntimeError("Missing x or y.")
    gui = _gui()
    gui.moveTo(int(x), int(y))
    return f"Moved pointer to {int(x)},{int(y)}."


def position() -> str:
    gui = _gui()
    point = gui.position()
    return f"{int(point.x)},{int(point.y)}"


def screenshot(path: str | None = None) -> str:
    gui = _gui()
    dest = Path(path) if path else Path.home() / "Library" / "Application Support" / "Charlie" / "last.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    gui.screenshot(str(dest))
    return str(dest)


def sleep(seconds: object) -> str:
    delay = min(max(float(seconds or 0), 0.0), 15.0)
    time.sleep(delay)
    return f"Waited {delay:.2f}s."
