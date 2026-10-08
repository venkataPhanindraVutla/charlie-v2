from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


ClientType = Literal["user.turn", "ui.ready", "ui.hidden"]
Source = Literal["text", "voice"]
AgentState = Literal["idle", "listening", "thinking", "acting", "done", "error"]


class ClientMessage(BaseModel):
    type: ClientType
    source: Source | None = None
    text: str | None = None


class UserTurn(ClientMessage):
    type: Literal["user.turn"] = "user.turn"
    source: Source
    text: str = Field(min_length=1)


class ServerMessage(BaseModel):
    type: str
    state: AgentState | None = None
    text: str | None = None
    tool: str | None = None
    ok: bool | None = None
    summary: str | None = None


def parse_client(raw: str) -> ClientMessage:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json") from exc
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError("message must be a JSON object with a type")
    try:
        if data["type"] == "user.turn":
            return UserTurn.model_validate(data)
        return ClientMessage.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def encode_server(msg: ServerMessage | dict[str, Any]) -> str:
    if isinstance(msg, ServerMessage):
        payload = msg.model_dump(exclude_none=True)
    else:
        payload = ServerMessage.model_validate(msg).model_dump(exclude_none=True)
    return json.dumps(payload, ensure_ascii=False)
