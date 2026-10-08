import { FormEvent, PointerEvent, useEffect, useRef, useState } from "react";
import { createHoldToTalk } from "./voice";
import { connectRuntime } from "./ws";
import { Portrait } from "./Portrait";

type Role = "you" | "charlie" | "system";
type AgentState = "idle" | "listening" | "thinking" | "acting" | "done" | "error";

type Line = { id: number; role: Role; text: string };

const STATUS_LINE: Record<AgentState, string> = {
  idle: "here",
  listening: "listening",
  thinking: "thinking",
  acting: "doing it",
  done: "here",
  error: "stuck",
};

export function App() {
  const [lines, setLines] = useState<Line[]>([
    { id: 0, role: "charlie", text: "I'm here. Type, or hold the seal to talk." },
  ]);
  const [state, setState] = useState<AgentState>("idle");
  const [draft, setDraft] = useState("");
  const [held, setHeld] = useState(false);
  const sendRef = useRef<(text: string, source: "text" | "voice") => void>(() => undefined);
  const mic = useRef(createHoldToTalk());
  const bottom = useRef<HTMLDivElement>(null);
  const idRef = useRef(1);

  const push = (role: Role, text: string) => {
    const id = idRef.current++;
    setLines((prev) => [...prev, { id, role, text }]);
  };

  useEffect(() => {
    const session = connectRuntime({
      onStatus: (next) => setState(next),
      onAssistant: (text, done) => {
        if (!done) return;
        push("charlie", text);
        setState("idle");
      },
      onError: (msg) => {
        push("system", msg);
        setState("error");
      },
    });
    sendRef.current = session.sendTurn;
    return () => session.close();
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [lines]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const text = draft.trim();
    if (!text) return;
    push("you", text);
    setDraft("");
    sendRef.current(text, "text");
  };

  const onMicDown = async (event: PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setHeld(true);
    setState("listening");
    try {
      await mic.current.start();
    } catch {
      setHeld(false);
      setState("idle");
      push("system", "I need the microphone. Allow it for Charlie, then hold again.");
    }
  };

  const onMicUp = async () => {
    if (!held) return;
    setHeld(false);
    setState("thinking");
    try {
      const text = await mic.current.stop();
      if (!text) {
        setState("idle");
        push("system", "I didn't catch that.");
        return;
      }
      push("you", text);
      sendRef.current(text, "voice");
    } catch (err) {
      setState("idle");
      push("system", err instanceof Error ? err.message : "I couldn't hear that.");
    }
  };

  return (
    <div className="app">
      <header className="title">
        <h1>Charlie</h1>
        <span className="status">{STATUS_LINE[state]}</span>
      </header>
      <aside className="companion">
        <Portrait state={state} />
        <p className="kicker">Chat or voice. Same thread.</p>
      </aside>
      <section className="transcript" aria-live="polite">
        {lines.map((line) => (
          <div key={line.id} className={`bubble ${line.role}`}>
            {line.text}
          </div>
        ))}
        <div ref={bottom} />
      </section>
      <form className="composer" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Tell me what to do"
          aria-label="Message"
        />
        <button
          type="button"
          className={held ? "mic held" : "mic"}
          onPointerDown={onMicDown}
          onPointerUp={onMicUp}
          onPointerCancel={onMicUp}
          aria-label="Hold to talk"
        >
          話
        </button>
      </form>
    </div>
  );
}
