# Charlie v2 — Local Core Design

**Status:** Locked  
**Date:** 2026-10-08  
**Product:** Charlie, a local autonomous OS agent  
**Codebase:** new project `charlie-v2/` (do not import `charlie/`)

## 1. What we are building

Charlie is a local computer agent for **macOS and Windows**. She lives on the machine, uses local models only, and operates the OS: apps, files, terminal, browser, processes, music. The operator talks to her by **chat or voice**. She answers in a calm feminine, Japanese-influenced anime register.

Charlie is the runtime. The LLM is one component inside it. Laya is the fast action chooser. Tools are primitives. Observation and verification close the loop.

## 2. Locked product decisions

| Decision | Lock |
|---|---|
| Existing `charlie/` code | Archive only. Zero imports. Greenfield. |
| Platforms now | macOS + Windows desktop. Nothing else. |
| Mobile / hosted web / VM isolation | Out of scope. Localhost protocol may allow a web client later. |
| Cloud LLMs | Forbidden. Ollama on localhost only. |
| Private data egress | Forbidden. Prompts, files, screenshots, memory, credentials never leave the box. |
| Web search | Later, via an explicit local gateway. Search queries are the only intended internet traffic. |
| UI | Electron. Simple anime companion chat + tray. |
| Control | Chat **or** voice. Same transcript, same runtime. |
| Window close | Hide to tray. Charlie keeps listening. Quit from tray. |
| Autonomy | No confirmation prompts for local actions. Every action is logged. |
| Personality | Separate render layer. Planner stays factual. Voice and copy are feminine, calm, precise, lightly playful. Not loud mascot energy. |
| Memory | SQLite is the store. A few living markdown files are the human-readable projection. Update existing files; never spawn a new file per event. |
| Apps vs browser | Native app first. Chrome profile / Playwright only if the app is not installed. |
| Music | Operator points at a folder. Charlie indexes metadata locally. |

## 3. Goals for Local Core (this spec)

A running Charlie that:

1. Starts as an Electron app which launches a Python sidecar.
2. Shows a simple companion chat (portrait + transcript + composer).
3. Accepts typed turns and hold-to-talk voice turns.
4. Plans with local `qwen3:4b` via Ollama.
5. Executes primitive local tools without asking.
6. Observes the result, speaks/types a short reply, logs the event.
7. Persists useful memory in SQLite.

**Done looks like:** “Open Terminal” from chat or voice opens Terminal (or Windows Terminal), the portrait shows *acting* then *done*, and Charlie says she opened it. If Ollama is down, she says so in character. Nothing is sent to OpenAI/Gemini.

## 4. Out of scope for Local Core

Build later, do not block Core:

- Playwright + CDP browser runtime and Chrome profile manager
- Laya fine-tune / `laya-browser` checkpoint (Core may call Laya if present, else a deterministic chooser)
- Native Slack/accessibility automation beyond “open the app”
- SearXNG web gateway
- Coding-agent edit/run/fix loop
- Process/server intelligence beyond listing
- Full music library semantic search
- Wake-word always-on (Core is hold-to-talk + optional typed wake in chat)

## 5. Architecture

```
Electron (tray + companion window)
  audio I/O, chat UI, mic permission
        │  WebSocket 127.0.0.1:7420
        ▼
Python runtime (sidecar)
  protocol → engine → planner (Ollama) → chooser (Laya or fallback)
        │
        ▼
OS adapter (macOS | Windows)
  open app, files, terminal, later browser
        │
        ▼
SQLite + event log + markdown projection
```

Two processes, one product. Electron is not the agent. Killing the window must not kill the sidecar until the tray quits.

### 5.1 Components

| Unit | Responsibility | Depends on |
|---|---|---|
| `desktop/` | Electron main, tray, companion UI, capture/playback | runtime WS |
| `charlie.server` | Bind localhost, accept one UI client, stream events | engine |
| `charlie.engine` | Task loop: perceive → plan → choose → act → observe → say | planner, chooser, registry, memory |
| `charlie.models` | Ollama chat, tools, structured JSON, keep_alive, VL swap | localhost:11434 |
| `charlie.chooser` | Pick one action from candidates | Laya if loaded, else heuristic |
| `charlie.registry` | Primitive tools with schema, observe, side effects | OS adapter |
| `charlie.os` | macOS vs Windows implementations of the same protocol | stdlib + OS APIs |
| `charlie.memory` | SQLite working/episodic/semantic; markdown writer | local files |
| `charlie.voice` | Optional on runtime; Electron may do STT/TTS and send text | local models |

### 5.2 Local protocol

WebSocket JSON, one connection from Electron.

Client → runtime:

```json
{"type": "user.turn", "source": "text"|"voice", "text": "..."}
{"type": "ui.ready"}
{"type": "ui.hidden"}
```

Runtime → client:

```json
{"type": "status", "state": "idle"|"listening"|"thinking"|"acting"|"done"|"error"}
{"type": "assistant.delta", "text": "..."}
{"type": "assistant.done", "text": "..."}
{"type": "speak", "text": "..."}
{"type": "event", "tool": "...", "ok": true, "summary": "..."}
```

No cloud URLs. Bind `127.0.0.1` only.

### 5.3 Task loop

```
observation = perceive()
state = memory.working.merge(observation)
plan = planner.plan(state)                 # local LLM, structured JSON
candidates = plan.next_actions             # primitives, not “click login”
action = chooser.choose(state, candidates) # Laya or fallback
result = registry.execute(action)          # no confirm
observation = perceive()
eval = evaluator.check(plan, action, result, observation)
if eval.need_ask: speak a question
elif eval.fail and recoverable: replan
else: continue or stop
memory.maybe_write(eval)                   # only if durable and useful
say short reply through personality layer
```

The LLM never calls tools by free-form string against a raw `FUNCTIONS` dict. It produces a plan object. The registry executes.

### 5.4 Tool primitives (Core)

Small set, composed by the planner:

- `os.app.open(name)`
- `os.app.list()`
- `os.file.open(path)`
- `os.folder.open(path)`
- `os.terminal.run(command)`  (cwd allowed; capture stdout/stderr)
- `os.clipboard.get` / `os.clipboard.set`
- `screen.capture()` (saved locally; used later by VL)
- `music.play(query)` (stub: open the pointed folder / first match)

No per-site tools (`open_gmail`, `click_login_button`).

### 5.5 OS adapter

One protocol, two backends:

- macOS: `open -a`, `osascript` where needed, `pbcopy`/`pbpaste`, `/Applications` scan
- Windows: `os.startfile`, `where`, Win+search only as last resort, PowerShell for process list

Hotkeys must be platform-correct (`Cmd` vs `Ctrl`). Never ship the v1 `Win` key / `start ''` / `alt+F4` assumptions as the Mac path.

### 5.6 Models

On this machine: Apple M2, 16 GB. Ollama was not installed at design time.

| Model | Role | Load |
|---|---|---|
| `qwen3:4b` | Plan, code-ish reasoning, JSON | Keep warm |
| `qwen3-vl:4b` | Screenshot / GUI fallback | Swap in; do not keep both 4B models loaded |
| Laya 322M | Choose among candidates | Resident if weights exist |

If Ollama is missing: runtime stays up, Charlie says she cannot think until Ollama is running, tools that do not need a plan (open a named app) may still run from a trivial parse.

Tool calling and structured outputs go through Ollama’s local `/api/chat` (`tools`, `format`, `keep_alive`).

### 5.7 Memory

SQLite file: `~/Library/Application Support/Charlie/charlie.db` on Mac, `%APPDATA%\Charlie\charlie.db` on Windows.

Tables: `events`, `turns`, `memories` (kind, text, score, updated_at).

Markdown projection (update in place):

- `memory/identity.md`
- `memory/preferences.md`
- `memory/applications.md`
- `memory/projects.md`
- `memory/music.md`
- `memory/lessons.md`

Write policy: store only if the memory evaluator says it will help a future task (useful × recurrence × confidence). “Open Chrome” does not write. “Songs live in ~/Music/Anime” does.

### 5.8 Voice

- Electron holds mic permission (needed on macOS TCC).
- Core: hold-to-talk in the composer. Audio is transcribed locally (whisper.cpp or equivalent). Transcript enters `user.turn` with `source: "voice"`.
- TTS: local Kokoro (female, English; Japanese-influenced delivery via copy, not a cartoon voice). Runtime sends `speak`.
- No Microsoft Edge TTS. No OpenAI Realtime. No cloud STT.

### 5.9 Companion UI

One window:

- Portrait, left. Expression follows `status` (idle, listening, thinking, acting, done, error).
- Transcript, right. Typed and spoken turns share the list.
- Composer: text field + hold-to-talk. One surface, not two modes.
- Status line in the title bar.
- Visual language: ink, indigo, warm paper. Calm anime. No neon, no extra chrome.
- Tray icon: show/hide window, quit.

No settings dashboard in Core. Config is a local TOML file.

## 6. Error handling

- Ollama down → `status=error`, spoken/typed “I can’t reach the local model.” Runtime remains up.
- Tool failure → observation includes stderr; engine replans once; then reports.
- WS disconnect → Electron reconnects; sidecar does not exit.
- Sidecar crash → Electron respawns it; user hears a short apology.
- Unknown app name → ask which app (voice/chat), do not guess among three similar names.

## 7. Security (local)

- Listen on `127.0.0.1` only.
- No API keys for cloud AI.
- Event log is local and complete.
- Full local autonomy is not “unlogged subprocess.” It is execute + record.
- Future web client must authenticate to localhost; not built now.

## 8. Testing

- Runtime unit tests: protocol parse, plan JSON schema, OS adapter dispatch, memory write policy, evaluator ask/continue/fail.
- Integration: mock Ollama HTTP, run one `os.app.open` path without a real LLM.
- Desktop: protocol client can send a turn and render `assistant.done` (jsdom or a small node test). Do not require a human to click the window for Core CI.

## 9. Later phases (not this spec’s build)

P2 native app automation and world state · P3 Playwright + Laya browser · P4 coding loop · P5 richer memory · P6 music library · P7 SearXNG gateway · P8 wake-word + richer Kokoro profile.

## 10. Config

`config.toml` (user data dir):

```toml
name = "Charlie"
ollama_host = "http://127.0.0.1:11434"
planner_model = "qwen3:4b"
vision_model = "qwen3-vl:4b"
runtime_port = 7420
music_folder = ""
voice_tts = "kokoro"
voice_id = "af_heart"
autonomy = "full"
```
