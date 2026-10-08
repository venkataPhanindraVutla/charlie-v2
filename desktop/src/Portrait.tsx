import type { AgentState } from "./ws";

export function Portrait({ state }: { state: AgentState }) {
  const mouth =
    state === "listening" ? "M70 128 Q88 142 106 128" : state === "thinking" ? "M74 132 H102" : "M70 128 Q88 138 106 128";
  const eyes = state === "thinking" ? 4 : 7;

  return (
    <div className={`portrait ${state}`} aria-hidden="true">
      <svg viewBox="0 0 160 200">
        <ellipse cx="80" cy="168" rx="46" ry="14" fill="#1a1630" opacity="0.35" />
        <path d="M40 86 C40 40 120 40 120 86 L118 150 C110 176 50 176 42 150 Z" fill="#f3d7c4" />
        <path d="M36 90 C28 20 132 16 124 92 C110 70 50 70 36 90 Z" fill="#2a1f40" />
        <path d="M48 78 C60 108 70 118 80 150 L52 138 Z" fill="#3b2d5c" opacity="0.55" />
        <circle cx="64" cy="108" r={eyes} fill="#1a1630" />
        <circle cx="98" cy="108" r={eyes} fill="#1a1630" />
        <path className="brow" d="M52 96 Q64 90 74 96" stroke="#1a1630" strokeWidth="2.4" fill="none" />
        <path d="M90 96 Q100 90 110 96" stroke="#1a1630" strokeWidth="2.4" fill="none" />
        <path d={mouth} stroke="#1a1630" strokeWidth="2.6" fill="none" />
        {state === "listening" ? <circle cx="80" cy="44" r="5" fill="#e8a0bf" /> : null}
      </svg>
    </div>
  );
}
