# Charlie Local Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a greenfield Charlie v2 that runs as an Electron companion chat plus a Python sidecar, plans with local Ollama `qwen3:4b`, executes primitive OS tools, and talks back in chat (voice hold-to-talk wired).

**Architecture:** Electron owns the window, tray, and mic. Python owns the task loop, models, tools, and SQLite. They talk over WebSocket on `127.0.0.1:7420`. No imports from `charlie/`.

**Tech Stack:** Python 3.11+, FastAPI/WebSockets, Ollama HTTP, SQLite, pytest, Electron, Vite, React, TypeScript.

**Spec:** `docs/superpowers/specs/2026-10-08-charlie-local-core-design.md`

## Global Constraints

- Localhost only: bind `127.0.0.1`, never `0.0.0.0`.
- No cloud LLM SDKs (no `openai`, no Gemini).
- Do not import anything from `../charlie/`.
- macOS and Windows OS adapters behind one protocol; no Win-key-only tools.
- Autonomy is execute + log, not confirm dialogs.
- One 4B model warm: `qwen3:4b`. Do not load `qwen3-vl:4b` at the same time in Core.

## Review Focus

- A second Electron window must not start a second sidecar on the same port; bind failure is reported, not hung.
- `os.terminal.run` must never send command output to Ollama if it looks like secrets (env files); truncate and flag.
- Portrait status must track the protocol `status` field, not a fake timer.
- Empty voice capture must not create a user turn.
- Closing the window must hide to tray and leave the sidecar running until Quit.

---

### Task 1: Python package, protocol, failing tests

**Files:**
- Create: `runtime/pyproject.toml`
- Create: `runtime/src/charlie/__init__.py`
- Create: `runtime/src/charlie/protocol.py`
- Create: `runtime/tests/test_protocol.py`

**Interfaces:**
- Consumes: nothing
- Produces: `parse_client(raw: str) -> ClientMessage`, `encode_server(msg: ServerMessage) -> str`

- [ ] **Step 1: Write the failing test**

```python
from charlie.protocol import parse_client, encode_server, ClientMessage

def test_parse_user_turn():
    msg = parse_client('{"type":"user.turn","source":"text","text":"open Terminal"}')
    assert msg.type == "user.turn"
    assert msg.source == "text"
    assert msg.text == "open Terminal"

def test_reject_non_localhost_shape():
    # protocol messages must be JSON objects with a type
    import pytest
    with pytest.raises(ValueError):
        parse_client("not-json")

def test_encode_status():
    raw = encode_server({"type": "status", "state": "thinking"})
    assert '"thinking"' in raw
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd runtime && python -m pytest tests/test_protocol.py -v`  
Expected: FAIL with import error or missing module

- [ ] **Step 3: Implement protocol**

Pydantic models for client and server messages listed in the spec. `parse_client` validates `type` ∈ {user.turn, ui.ready, ui.hidden}. `encode_server` dumps JSON with `type`.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `cd runtime && python -m pytest tests/test_protocol.py -v`  
Expected: PASS

---

### Task 2: Engine loop with a fake planner

**Files:**
- Create: `runtime/src/charlie/runtime/engine.py`
- Create: `runtime/src/charlie/runtime/task.py`
- Create: `runtime/src/charlie/cognition/planner.py`
- Create: `runtime/tests/test_engine.py`

**Interfaces:**
- Consumes: `ClientMessage`
- Produces: `Engine.run_turn(text: str, source: str) -> list[ServerMessage]` including status thinking/acting/done and assistant.done

- [ ] **Step 1: Write the failing test**

```python
def test_open_app_turn_emits_status_and_reply(monkeypatch):
    from charlie.runtime.engine import Engine
    engine = Engine(planner=FakePlanner(actions=[{"tool": "os.app.open", "args": {"name": "Terminal"}}]),
                    registry=FakeRegistry(ok=True))
    events = engine.run_turn("open Terminal", "text")
    states = [e.get("state") for e in events if e["type"] == "status"]
    assert "thinking" in states
    assert "acting" in states
    assert "done" in states
    assert any(e["type"] == "assistant.done" for e in events)
```

- [ ] **Step 2: Run to verify fail**

- [ ] **Step 3: Implement Engine.run_turn** — no Ollama yet. Fake planner returns structured actions. Registry is injectable.

- [ ] **Step 4: Tests pass**

---

### Task 3: OS adapter + tool registry

**Files:**
- Create: `runtime/src/charlie/actions/registry.py`
- Create: `runtime/src/charlie/actions/os_layer.py`
- Create: `runtime/src/charlie/actions/macos.py`
- Create: `runtime/src/charlie/actions/windows.py`
- Create: `runtime/tests/test_registry.py`

**Interfaces:**
- Consumes: `{tool, args}`
- Produces: `{ok: bool, observation: str}`

- [ ] **Step 1: Test registry dispatches `os.app.open` to the platform adapter** (adapter is mocked; do not actually launch apps in CI)

- [ ] **Step 2: Fail, then implement** `Registry.execute`, `OsAdapter.open_app(name)`, platform modules selected by `sys.platform`

- [ ] **Step 3: Tests pass**

---

### Task 4: Ollama planner

**Files:**
- Create: `runtime/src/charlie/cognition/models.py`
- Create: `runtime/src/charlie/cognition/ollama_planner.py`
- Create: `runtime/tests/test_ollama_planner.py`

**Interfaces:**
- Consumes: turn text + tool schemas
- Produces: `Plan(actions: list[Action], say: str)` via Ollama `/api/chat` with `format` JSON schema

- [ ] **Step 1: Test against `httpx.MockTransport`** — fake Ollama JSON, assert Plan parses. No live Ollama required.

- [ ] **Step 2: Implement `OllamaProvider.plan`** using `http://127.0.0.1:11434`, model `qwen3:4b`, `keep_alive` 10m, structured format.

- [ ] **Step 3: If Ollama unreachable, raise `ModelUnavailable`** which Engine converts to an in-character error reply.

---

### Task 5: SQLite memory + event log

**Files:**
- Create: `runtime/src/charlie/memory/store.py`
- Create: `runtime/tests/test_memory.py`

**Interfaces:**
- `Store.log_event(...)`
- `Store.maybe_write_memory(text, score) -> bool`
- `Store.recent_turns(n) -> list`

- [ ] **Step 1: Test that score below 0.6 does not insert into `memories`**
- [ ] **Step 2: Implement SQLite in a temp dir for tests, user-data-dir in production**

---

### Task 6: WebSocket server on 127.0.0.1:7420

**Files:**
- Create: `runtime/src/charlie/server.py`
- Create: `runtime/src/charlie/main.py`
- Create: `runtime/tests/test_server.py`

**Interfaces:**
- `serve(host="127.0.0.1", port=7420)`
- One turn over WS produces status + assistant.done

- [ ] **Step 1: Test with Starlette/FastAPI TestClient websocket**
- [ ] **Step 2: Implement FastAPI websocket endpoint `/ws`**
- [ ] **Step 3: Binding `0.0.0.0` must be impossible (host constant)**

---

### Task 7: Electron companion shell

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/electron/main.ts`
- Create: `desktop/src/App.tsx` (and CSS)
- Create: `desktop/src/ws.ts`

**Interfaces:**
- Main process spawns `python -m charlie` sidecar, connects renderer via preload
- Renderer: portrait + transcript + composer
- Hide to tray on close

- [ ] **Step 1: App renders empty transcript and composer**
- [ ] **Step 2: Sending text calls `user.turn` and appends `assistant.done`**
- [ ] **Step 3: Status field drives portrait class (`idle|listening|thinking|acting|done|error`)**
- [ ] **Step 4: Visual language ink / indigo / warm paper, no extra chrome**

---

### Task 8: Hold-to-talk → text turn

**Files:**
- Create: `desktop/src/voice.ts`
- Modify: `desktop/src/App.tsx`

**Interfaces:**
- Pointer-down on mic starts capture; pointer-up sends audio to local STT or, if STT missing, shows “voice not ready” without a fake turn.

- [ ] **Step 1: Empty blob does not emit `user.turn`**
- [ ] **Step 2: Successful transcript emits `user.turn` with `source: "voice"`**

---

### Task 9: Personality + speak

**Files:**
- Create: `runtime/src/charlie/cognition/personality.py`
- Modify: engine to emit `speak` with the same short reply shown in chat

- [ ] **Step 1: Replies are short, feminine, calm; no tool names leaked**
- [ ] **Step 2: `speak` event accompanies `assistant.done`**
