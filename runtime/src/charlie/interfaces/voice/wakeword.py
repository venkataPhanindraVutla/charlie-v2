from __future__ import annotations

WAKE_WORD = "wake up"
END_PHRASE = "bye"

Kind = str  # ignore | wake_ack | command | goodbye


class WakeGate:
    """Idle until 'wake up'; 'bye' deactivates. Same phrases as original Charlie."""

    def __init__(self, wake: str = WAKE_WORD, end: str = END_PHRASE) -> None:
        self.wake = wake.lower()
        self.end = end.lower()
        self.active = False

    def consider(self, text: str) -> tuple[Kind, str]:
        raw = (text or "").strip()
        if not raw:
            return ("ignore", "")
        lower = raw.lower()
        if self.end in lower:
            if self.active:
                self.active = False
                return ("goodbye", "")
            return ("ignore", "")
        if not self.active:
            if self.wake not in lower:
                return ("ignore", "")
            self.active = True
            command = lower.split(self.wake, 1)[1].strip()
            if command:
                return ("command", command)
            return ("wake_ack", "")
        return ("command", raw)
