from __future__ import annotations

import asyncio
from collections.abc import Callable

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from charlie.protocol import encode_server, parse_client
from charlie.runtime.engine import Engine
from charlie.voice.stt import transcribe_wav_bytes
from charlie.voice.tts import speak

HOST = "127.0.0.1"
PORT = 7420


def create_app(
    engine: Engine,
    transcribe: Callable[[bytes], str] | None = None,
) -> FastAPI:
    app = FastAPI(title="Charlie runtime")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    stt = transcribe or transcribe_wav_bytes

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
            await ws.send_text(encode_server({"type": "status", "state": "idle"}))
            while True:
                raw = await ws.receive_text()
                message = parse_client(raw)
                if message.type != "user.turn" or not message.text:
                    continue
                events = await asyncio.to_thread(
                    engine.run_turn, message.text, message.source or "text"
                )
                for event in events:
                    await ws.send_text(encode_server(event))
                    if event.get("type") == "speak" and event.get("text"):
                        await asyncio.to_thread(speak, str(event["text"]))
        except WebSocketDisconnect:
            return
        except ValueError as exc:
            try:
                await ws.send_text(
                    encode_server({"type": "status", "state": "error", "text": str(exc)})
                )
            except WebSocketDisconnect:
                return

    return app
