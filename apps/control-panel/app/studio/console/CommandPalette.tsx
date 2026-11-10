"use client";
import { Fragment, useEffect, useRef, useState } from "react";
import { useKeyBindings, useKeyModal, useKeys } from "./keys/KeysProvider";
import { BINDINGS, cheatSheetRows, filterCommands, paletteCommands, type PaletteCommand } from "./keys/registry";

// Commands, the cheat sheet and every key the palette handles come from keys/registry.ts;
// this component only owns the open/closed and cursor state.
export default function CommandPalette({ boxState }: { boxState?: string | null }) {
  const keys = useKeys();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [cheatSheet, setCheatSheet] = useState(false);
  const [feedback, setFeedback] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = paletteCommands(BINDINGS, keys.has);

  function close() { setOpen(false); setQuery(""); setCursor(0); }
  function toast(msg: string) { setFeedback(msg); setTimeout(() => setFeedback(""), 3000); }

  const filtered = filterCommands(commands, query);

  function run(cmd: PaletteCommand) {
    if (cmd.id === "help.cheatsheet") { close(); setCheatSheet(true); return; }
    close();
    keys.invoke(cmd.id);
    if (cmd.id === "box.start") toast("Box start requested…");
    if (cmd.id === "box.stop") toast("Box stop requested — billing ends once stopped.");
  }

  useKeyBindings("global", true, {
    "palette.toggle": () => setOpen((v) => { if (!v) { setQuery(""); setCursor(0); } return !v; }),
    "help.cheatsheet": () => setCheatSheet((v) => !v),
    "overlay.close": () => { close(); setCheatSheet(false); },
  });
  useKeyBindings("palette", open, {
    "palette.down": () => setCursor((c) => Math.min(c + 1, filtered.length - 1)),
    "palette.up": () => setCursor((c) => Math.max(c - 1, 0)),
    "palette.run": () => { if (filtered[cursor]) run(filtered[cursor]); },
  });
  useKeyModal(open || cheatSheet);

  // Focus input when palette opens
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 20); }, [open]);

  return (
    <>
      {/* Floating feedback toast */}
      {feedback && (
        <div className="fixed bottom-4 right-4 z-50 bg-panel border border-edge rounded-lg px-4 py-2 text-[14px] text-fg shadow-lg">
          {feedback}
        </div>
      )}

      {/* Cheat sheet overlay: the only one. Rows are the registry's, so it lists every binding. */}
      {cheatSheet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setCheatSheet(false)}>
          <div data-testid="cheat-sheet" className="bg-panel border border-edge rounded-xl p-5 w-[460px] max-w-full max-h-[80vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <div className="text-[16px] font-semibold">Keyboard shortcuts</div>
              <button onClick={() => setCheatSheet(false)} className="text-dim hover:text-fg text-[18px] leading-none">×</button>
            </div>
            <table className="w-full text-[13px] border-collapse">
              <tbody>
                {(() => {
                  let lastGroup = "";
                  return cheatSheetRows(BINDINGS).map((r) => {
                    const head = r.group !== lastGroup;
                    lastGroup = r.group;
                    return (
                      <Fragment key={r.id}>
                        {head && <tr><th colSpan={2} className="pt-3 pb-1 text-left text-[11px] text-dim uppercase tracking-wide font-normal">{r.group}</th></tr>}
                        <tr data-binding-id={r.id} className="border-b border-edge/40 last:border-0">
                          <td className="py-1.5 pr-4 font-mono text-accent whitespace-nowrap">{r.keys}</td>
                          <td className="py-1.5 text-dim">{r.description}</td>
                        </tr>
                      </Fragment>
                    );
                  });
                })()}
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
                          onClick={() => run(cmd)}
                          onMouseEnter={() => setCursor(i)}
                          className={"w-full text-left px-4 py-2 text-[14px] flex items-center gap-2 " +
                            (cursor === i ? "bg-raised text-fg" : "text-dim hover:bg-raised/50")}
                        >
                          {cmd.label}
                          {cmd.id === "box.start" && boxState === "running" && (
                            <span className="ml-auto text-[11px] text-dim">box is running</span>
                          )}
                          {cmd.id === "box.stop" && boxState === "stopped" && (
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
