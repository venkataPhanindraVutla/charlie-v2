from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from charlie.interfaces.voice.output import EdgeTTSVoice, VoiceOutput
from charlie.interfaces.voice.session import start_voice_ear
from charlie.protocol import encode_server, parse_client
from charlie.runtime.engine import Engine
from charlie.voice.stt import transcribe_wav_bytes

HOST = "127.0.0.1"
PORT = 7420


class TurnHub:
    """One turn path for text WS and the voice ear. Speaks once. MCP never sees TTS."""

    def __init__(self, engine: Engine, voice: VoiceOutput) -> None:
        self.engine = engine
        self.voice = voice
        self.clients: set[WebSocket] = set()

    async def run_turn(self, text: str, source: str) -> list[dict[str, Any]]:
        events = await asyncio.to_thread(self.engine.run_turn, text, source)
        spoken = False
        dead: list[WebSocket] = []
        for event in events:
            payload = encode_server(event)
            for ws in list(self.clients):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            if not spoken and event.get("type") == "speak" and event.get("text"):
                spoken = True
                await self.voice.speak(str(event["text"]))
        for ws in dead:
            self.clients.discard(ws)
        return events


def create_app(
    engine: Engine,
    transcribe: Callable[[bytes], str] | None = None,
    voice: VoiceOutput | None = None,
    listen: bool = False,
) -> FastAPI:
    hub = TurnHub(engine, voice or EdgeTTSVoice())
    stt = transcribe or transcribe_wav_bytes

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if listen:
            loop = asyncio.get_running_loop()
            start_voice_ear(loop, hub.voice, lambda t: hub.run_turn(t, "voice"))
        yield

    app = FastAPI(title="Charlie runtime", lifespan=lifespan)
    app.state.hub = hub
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/voice/transcribe")
    async def voice_transcribe(request: Request) -> dict[str, str]:
        data = await request.body()
        text = await asyncio.to_thread(stt, data)
        return {"text": text}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        try:
            await ws.accept()
            hub.clients.add(ws)
            await ws.send_text(encode_server({"type": "status", "state": "idle"}))
            while True:
                raw = await ws.receive_text()
                message = parse_client(raw)
                if message.type != "user.turn" or not message.text:
                    continue
                await hub.run_turn(message.text, message.source or "text")
        except WebSocketDisconnect:
            return
        except ValueError as exc:
            try:
                await ws.send_text(
                    encode_server({"type": "status", "state": "error", "text": str(exc)})
                )
            except WebSocketDisconnect:
                return
        finally:
            hub.clients.discard(ws)

    return app
