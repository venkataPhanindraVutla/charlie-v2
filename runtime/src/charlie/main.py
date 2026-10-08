from __future__ import annotations

import argparse
import os
import threading
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import uvicorn

from charlie.actions.registry import Registry
from charlie.cognition.laya import Decider
from charlie.cognition.models import OllamaPlanner
from charlie.memory.store import Store
from charlie.runtime.engine import Engine
from charlie.server import HOST, PORT, create_app


def user_data_dir() -> Path:
    home = Path.home()
    mac = home / "Library" / "Application Support" / "Charlie"
    if Path("/Applications").exists() or (home / "Library").exists():
        return mac
    return Path.home() / "AppData" / "Roaming" / "Charlie"


def build_engine() -> Engine:
    db = user_data_dir() / "charlie.db"
    return Engine(
        planner=OllamaPlanner(),
        registry=Registry(),
        memory=Store(db),
        decider=Decider(load=False),
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="charlie")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(
        "--no-listen",
        action="store_true",
        help="Skip RealtimeSTT wake-word ear (Electron hold-to-talk still works)",
    )
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Charlie binds to 127.0.0.1 only")
    app = create_app(build_engine(), listen=not args.no_listen)

    def _warm_ear() -> None:
        try:
            from charlie.voice.stt import model

            model()
        except Exception as exc:
            print(f"local whisper warmup: {exc}")

    threading.Thread(target=_warm_ear, daemon=True).start()
    uvicorn.run(app, host=HOST, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
