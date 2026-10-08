# Charlie Harness + MCP

Locked: 2026-10-08

Charlie is a **harness**. The local LLM plans at **task** level. Laya decides at **tactical** level (`choice` / `score` / `noul`). MCP servers expose **semantic capabilities**. Individual tools do not own the loop.

```
USER → HARNESS (plan / state / Laya / execute / verify / recover)
                 ↓ MCP
        OS · Apps · Browser · Code · Web · Music
```

## Loops

- **Strategic (rare):** LLM emits domain + ordered steps with capability names and success conditions. Called once per task, or on explicit replan.
- **Tactical (fast):** observe → Laya chooses among the **step's allowed actions** → MCP executes → verify → next step. No LLM.

## Non-goals for this cut

- LLM inside an MCP server
- Full browser/CDP MCP (stub registry only)
- Downloading Laya weights in tests (heuristic decider fallback)
