from __future__ import annotations

import os
import re
import subprocess
import sys

_speaker: subprocess.Popen | None = None
_voice: str | None = None

PREFERRED = (
    "Flo (English (US))",
    "Samantha",
    "Sandy (English (US))",
    "Shelley (English (US))",
    "Karen",
    "Moira",
    "Tessa",
    "Tara",
)

NOVELTY = re.compile(
    r"bells|boing|bubbles|cellos|bad news|good news|whisper|zarvox|trinoids|"
    r"wobble|bahh|albert|fred|jester|organ|superstar|kathy|princess|junior|"
    r"grandma|grandpa|eddy|reed|rocko|ralph",
    re.I,
)


def _mac_voices() -> list[str]:
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    names: list[str] = []
    for line in result.stdout.splitlines():
        match = re.match(r"^(.+?)\s+([a-z]{2}[_-][A-Z]{2})\s+#", line)
        if not match:
            continue
        name, lang = match.group(1).strip(), match.group(2)
        if lang.startswith("en") and not NOVELTY.search(name):
            names.append(name)
    return names


def _pick_voice() -> str:
    global _voice
    if _voice:
        return _voice
    available = _mac_voices()
    for name in PREFERRED:
        if name in available:
            _voice = name
            return _voice
    _voice = available[0] if available else "Samantha"
    return _voice


def speak(text: str) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    spoken = (text or "").strip()
    if not spoken:
        return
    global _speaker
    if _speaker is not None and _speaker.poll() is None:
        _speaker.kill()
    if sys.platform == "darwin":
        _speaker = subprocess.Popen(
            ["say", "-v", _pick_voice(), "-r", "168", spoken[:500]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if sys.platform == "win32":
        escaped = spoken[:500].replace("'", "''")
        _speaker = subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female); "
                "$s.Rate = 0; "
                f"$s.Speak('{escaped}')",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
