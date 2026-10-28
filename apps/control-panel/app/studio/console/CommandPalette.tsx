"use client";
import { useEffect, useRef, useState } from "react";

const PIPE = process.env.NEXT_PUBLIC_PIPELINE_URL || "http://127.0.0.1:8800";

type Cmd = {
  id: string;
  label: string;
  category: string;
  keywords?: string;
  action: () => void | Promise<void>;
};

const CHEAT_SHEET = [
  { key: "Ctrl + K", desc: "Open command palette" },
  { key: "?", desc: "Toggle hotkey cheat sheet" },
  { key: "↑ / ↓", desc: "Navigate commands" },
  { key: "Enter", desc: "Execute selected command" },
  { key: "Esc", desc: "Close palette / cheat sheet" },
  { key: "1–8 (pipeline)", desc: "Jump to stage N in Pipeline" },
  { key: "J / L", desc: "Previous / next take (Review Room)" },
  { key: "A / R", desc: "Approve / Reject take (Review Room)" },
  { key: "Space", desc: "Play / pause waveform (Timeline)" },
];

export default function CommandPalette({
  onSwitchDomain,
  onBoxStart,
  onBoxStop,
  boxState,
}: {
  onSwitchDomain: (d: string) => void;
  onBoxStart: () => void;
  onBoxStop: () => void;
  boxState?: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [cheatSheet, setCheatSheet] = useState(false);
  const [feedback, setFeedback] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Cmd[] = [
    { id: "pipeline", label: "Go to Pipeline", category: "Navigate", keywords: "stages 8", action: () => { onSwitchDomain("pipeline"); close(); } },
    { id: "review", label: "Go to Review Room", category: "Navigate", keywords: "takes approve", action: () => { onSwitchDomain("review"); close(); } },
    { id: "studio", label: "Go to Studio Chat", category: "Navigate", keywords: "llm box", action: () => { onSwitchDomain("studio"); close(); } },
    { id: "generation", label: "Go to Asset Generation", category: "Navigate", keywords: "render shot", action: () => { onSwitchDomain("generation"); close(); } },
    { id: "assembly", label: "Go to Timeline & Assembly", category: "Navigate", keywords: "cut timeline", action: () => { onSwitchDomain("assembly"); close(); } },
    { id: "analytics", label: "Go to Analytics / Queue", category: "Navigate", keywords: "cost control plane", action: () => { onSwitchDomain("analytics"); close(); } },
    {
      id: "box-start",
      label: "Start GPU Box",
      category: "Box",
      keywords: "ec2 comfyui start",
      action: async () => {
        close();
        onBoxStart();
        toast("Box start requested…");
      },
    },
    {
      id: "box-stop",
      label: "Stop GPU Box",
      category: "Box",
      keywords: "ec2 comfyui stop billing",
      action: async () => {
        close();
        onBoxStop();
        toast("Box stop requested — billing ends once stopped.");
      },
    },
    {
      id: "cheat-sheet",
      label: "Show keyboard cheat sheet",
      category: "Help",
      keywords: "hotkeys shortcuts",
      action: () => { setCheatSheet(true); setOpen(false); },
    },
  ];

  function close() { setOpen(false); setQuery(""); setCursor(0); }
  function toast(msg: string) { setFeedback(msg); setTimeout(() => setFeedback(""), 3000); }

  const filtered = query.trim()
    ? commands.filter((c) =>
        `${c.label} ${c.category} ${c.keywords ?? ""}`.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  // Ctrl+K / ? hotkeys
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "k" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        setOpen((v) => { if (!v) { setQuery(""); setCursor(0); } return !v; });
      }
      if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = (document.activeElement as HTMLElement)?.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea") return;
        setCheatSheet((v) => !v);
      }
      if (e.key === "Escape") { close(); setCheatSheet(false); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Focus input when palette opens
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 20); }, [open]);

  function onInputKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
    else if (e.key === "Enter" && filtered[cursor]) { filtered[cursor].action(); }
    else if (e.key === "Escape") { close(); }
  }

  return (
    <>
      {/* Floating feedback toast */}
      {feedback && (
        <div className="fixed bottom-4 right-4 z-50 bg-panel border border-edge rounded-lg px-4 py-2 text-[14px] text-fg shadow-lg">
          {feedback}
        </div>
      )}

      {/* Cheat sheet overlay */}
      {cheatSheet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setCheatSheet(false)}>
          <div className="bg-panel border border-edge rounded-xl p-5 w-[420px] max-w-full shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <div className="text-[16px] font-semibold">Keyboard shortcuts</div>
              <button onClick={() => setCheatSheet(false)} className="text-dim hover:text-fg text-[18px] leading-none">×</button>
            </div>
            <table className="w-full text-[13px] border-collapse">
              <tbody>
                {CHEAT_SHEET.map((r) => (
                  <tr key={r.key} className="border-b border-edge/40 last:border-0">
                    <td className="py-1.5 pr-4 font-mono text-accent whitespace-nowrap">{r.key}</td>
                    <td className="py-1.5 text-dim">{r.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 text-[11px] text-dim text-center">Press Esc or click outside to close</div>
          </div>
        </div>
      )}

      {/* Command palette modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/50" onClick={close}>
          <div
            className="bg-panel border border-edge rounded-xl w-[520px] max-w-full shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Input */}
            <div className="flex items-center gap-2 px-3 border-b border-edge">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-dim shrink-0">
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => { setQuery(e.target.value); setCursor(0); }}
                onKeyDown={onInputKey}
                placeholder="Type a command…"
                className="flex-1 bg-transparent text-fg text-[15px] py-3 outline-none placeholder:text-dim"
              />
              <kbd className="text-[10px] text-dim border border-edge rounded px-1.5 py-0.5 font-mono">Esc</kbd>
            </div>

            {/* Results */}
            <div className="max-h-72 overflow-y-auto py-1">
              {filtered.length === 0 ? (
                <div className="px-4 py-3 text-[14px] text-dim">No commands match.</div>
              ) : (
                (() => {
                  let lastCat = "";
                  return filtered.map((cmd, i) => {
                    const showCat = cmd.category !== lastCat;
                    lastCat = cmd.category;
                    return (
                      <div key={cmd.id}>
                        {showCat && (
                          <div className="px-4 pt-2 pb-1 text-[11px] text-dim uppercase tracking-wide">{cmd.category}</div>
                        )}
                        <button
                          onClick={() => cmd.action()}
                          onMouseEnter={() => setCursor(i)}
                          className={"w-full text-left px-4 py-2 text-[14px] flex items-center gap-2 " +
                            (cursor === i ? "bg-raised text-fg" : "text-dim hover:bg-raised/50")}
                        >
                          {cmd.label}
                          {cmd.id === "box-start" && boxState === "running" && (
                            <span className="ml-auto text-[11px] text-dim">box is running</span>
                          )}
                          {cmd.id === "box-stop" && boxState === "stopped" && (
                            <span className="ml-auto text-[11px] text-dim">already stopped</span>
                          )}
                        </button>
                      </div>
                    );
                  });
                })()
              )}
            </div>

            <div className="border-t border-edge px-4 py-1.5 flex items-center gap-3 text-[11px] text-dim">
              <span><kbd className="border border-edge rounded px-1 py-0.5 font-mono">↑↓</kbd> navigate</span>
              <span><kbd className="border border-edge rounded px-1 py-0.5 font-mono">Enter</kbd> run</span>
              <span><kbd className="border border-edge rounded px-1 py-0.5 font-mono">?</kbd> hotkeys</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
