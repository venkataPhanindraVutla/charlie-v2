# Charlie v2

Local OS agent. Electron companion chat + Python sidecar. Ollama `qwen3:4b` on localhost. Nothing leaves the machine.

## Run

Terminal 1 — runtime:

```bash
cd runtime
python3 -m pip install -e ".[dev]"
python3 -m charlie
```

Terminal 2 — desktop:

```bash
cd desktop
npm install
npm run dev
```

Type in the window, or hold 話. Voice transcription is not wired in Local Core yet; typed turns already hit the runtime.

If Ollama is not running, Charlie still opens and will tell you she cannot think. Install Ollama and `ollama pull qwen3:4b` for planning.

## Layout

- `runtime/` — task loop, tools, SQLite, WebSocket on `127.0.0.1:7420`
- `desktop/` — Electron tray + companion UI
- `docs/superpowers/` — locked spec and plan
