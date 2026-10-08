from __future__ import annotations

import re

DOMAIN_CAPABILITIES: dict[str, list[str]] = {
    "communication": [
        "apps.open",
        "apps.jump",
        "communication.send_message",
        "communication.find_contact",
    ],
    "apps": ["apps.open", "apps.list"],
    "files": ["files.open", "files.open_folder"],
    "code": ["process.run", "python.run"],
    "web": ["web.search", "web.fetch"],
    "system": ["apps.list", "process.run"],
}

CHAT_APPS = ("slack", "whatsapp", "discord", "messages", "telegram")
CHAT_CAPABILITIES = {
    "communication.send_message",
    "communication.find_contact",
}
JUMPS = {"apps.jump", "os.app.jump", "communication.send_message", "communication.find_contact"}

COMMS_RE = re.compile(
    r"whats?\s*app|\bslack\b|\bdiscord\b|\btelegram\b|\b(dm|dms)\b|"
    r"\b(send|message|text|ping)\b.{0,40}\b(to|on|in)\b|"
    r"\b(open|jump|find).{0,40}\b(chat|conversation)\b|"
    r"\b(send again|resend|send it)\b",
    re.I,
)

SEND_AGAIN_RE = re.compile(r"\b(send again|resend|send it)\b", re.I)
ASK_SENT_RE = re.compile(r"\bdid you send\b|\bwas it sent\b|\bdid it send\b", re.I)
WANTS_SEND_RE = re.compile(r"\bsend\b", re.I)

WEB_RE = re.compile(
    r"https?://|\bsearch (the )?web\b|\blook up\b|\bgoogle\b|\bduckduckgo\b|"
    r"\bstock\b|\bticker\b|\b(share )?price\b|\bweather\b|\bforecast\b|\bnews\b|"
    r"\bheadline|\bwho (is|won|are)\b|"
    r"\bwhat('s| is) (the )?(current|latest)\b|"
    r"\b(current|latest)\b.{0,40}\b(price|stock|score|weather|version|news)\b",
    re.I,
)

LIVE_LOOKUP = {"web.search", "web.fetch"}


def is_comms_turn(text: str, last_domain: str | None = None) -> bool:
    if COMMS_RE.search(text or ""):
        return True
    return last_domain == "communication" and bool(SEND_AGAIN_RE.search(text or ""))


def infer_domain(text: str, last_domain: str | None = None) -> str:
    lowered = (text or "").lower()
    if ASK_SENT_RE.search(lowered):
        return "status"
    if is_comms_turn(text, last_domain):
        return "communication"
    if any(word in lowered for word in ("file", "folder", "directory", "open ~/")):
        return "files"
    if WEB_RE.search(lowered):
        return "web"
    if any(word in lowered for word in ("terminal", "shell", "python", "git ", "command")):
        return "code"
    if re.search(r"\b(open|launch|start)\b", lowered):
        return "apps"
    return "talk"


def constrain(domain: str, actions: list[str]) -> list[str]:
    if not actions or domain == "talk":
        return []
    if len(actions) == 1:
        return list(actions)
    allowed = set(DOMAIN_CAPABILITIES.get(domain, []))
    filtered = [action for action in actions if action in allowed]
    return filtered or list(actions)


def step_permitted(
    text: str,
    capability: str,
    args: dict | None = None,
    comms: bool | None = None,
) -> bool:
    args = args or {}
    app = str(args.get("app") or args.get("name") or "").lower()
    if comms is None:
        comms = is_comms_turn(text)
    if capability in CHAT_CAPABILITIES and not comms:
        return False
    if capability in JUMPS and app in CHAT_APPS and not comms:
        return False
    if capability in {"apps.open", "os.app.open"} and app in CHAT_APPS and not comms:
        return False
    return True


def schemas_for(text: str, schemas: list[dict], comms: bool | None = None) -> list[dict]:
    if comms is None:
        comms = is_comms_turn(text)
    if comms:
        return schemas
    blocked = CHAT_CAPABILITIES | {"apps.jump"}
    return [spec for spec in schemas if spec.get("name") not in blocked]
