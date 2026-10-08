export type AgentState = "idle" | "listening" | "thinking" | "acting" | "done" | "error";

type Handlers = {
  onStatus: (state: AgentState) => void;
  onAssistant: (text: string, done: boolean) => void;
  onSpeak?: (text: string) => void;
  onError: (message: string) => void;
};

const STATES: AgentState[] = ["idle", "listening", "thinking", "acting", "done", "error"];

function isState(value: string): value is AgentState {
  return (STATES as string[]).includes(value);
}

export function connectRuntime(handlers: Handlers) {
  const url =
    (window as unknown as { charlie?: { runtimeUrl: string } }).charlie?.runtimeUrl ??
    "ws://127.0.0.1:7420/ws";
  let socket: WebSocket | null = null;
  let closed = false;
  let buffer = "";
  let retry: ReturnType<typeof setTimeout> | undefined;
  let everOpened = false;

  const open = () => {
    if (closed) return;
    socket = new WebSocket(url);
    socket.onopen = () => {
      everOpened = true;
    };
    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(String(event.data));
        if (msg.type === "status" && isState(msg.state)) handlers.onStatus(msg.state);
        if (msg.type === "assistant.delta") {
          buffer += msg.text ?? "";
          handlers.onAssistant(buffer, false);
        }
        if (msg.type === "assistant.done") {
          handlers.onAssistant(msg.text ?? buffer, true);
          buffer = "";
        }
        if (msg.type === "speak" && msg.text) handlers.onSpeak?.(msg.text);
      } catch {
        handlers.onError("I couldn't read a runtime message.");
      }
    };
    socket.onerror = () => {
      if (!closed && everOpened) handlers.onError("The local runtime isn't answering.");
    };
    socket.onclose = () => {
      if (closed) return;
      retry = setTimeout(open, 800);
    };
  };

  open();

  return {
    sendTurn(text: string, source: "text" | "voice") {
      if (!text.trim()) return;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        handlers.onError("I'm still connecting to the local runtime.");
        return;
      }
      socket.send(JSON.stringify({ type: "user.turn", source, text }));
    },
    close() {
      closed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    },
  };
}
