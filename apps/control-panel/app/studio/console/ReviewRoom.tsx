"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export type C2PAStatus = "valid" | "missing" | "broken";

export type ReviewTake = {
  takeId: string;
  shotId?: string;
  songId?: string;
  sceneNumber?: number;
  label: string;
  url: string;
  model?: string | null;
  c2paStatus?: C2PAStatus;
};

const C2PA_CHIP: Record<C2PAStatus, { label: string; color: string }> = {
  valid:   { label: "C2PA ✓", color: "#57c97a" },
  missing: { label: "C2PA ?", color: "#e0a13a" },
  broken:  { label: "C2PA ✗", color: "#ef6f6c" },
};

type NotePin = { id: string; takeId: string; time: number; text: string };
type Decision = { state: "approved" | "rejected"; reason?: string };

const pad = (n: number) => String(Math.floor(n)).padStart(2, "0");
function toTc(secs: number) {
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60), f = Math.floor((secs % 1) * 30);
  return `${pad(h)}:${pad(m)}:${pad(s)};${pad(f)}`;
}

const CHEAT = [["J","slow reverse"],["K","pause"],["L","play"],["Space","play/pause"],
  ["← →","frame ±1f"],["A","approve"],["R","reject…"],["N / P","next / prev take"],
  ["\\","cycle A/B mode"],["?","toggle keys"]];

export default function ReviewRoom({
  takes,
  reviewer = "brad",
  onApprove,
  onReject,
}: {
  takes: ReviewTake[];
  reviewer?: string;
  onApprove?: (take: ReviewTake) => void;
  onReject?: (take: ReviewTake, reason: string) => void;
}) {
  const [idx, setIdx] = useState(0);
  const [bIdx, setBIdx] = useState(1);
  const [abMode, setAbMode] = useState<"single" | "side-by-side" | "wipe">("single");
  const [wipeX, setWipeX] = useState(0.5);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [notes, setNotes] = useState<NotePin[]>([]);
  const [noteInput, setNoteInput] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [timecode, setTimecode] = useState("00:00:00;00");
  const [duration, setDuration] = useState(0);
  const [progress, setProgress] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [cheatSheet, setCheatSheet] = useState(false);
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);
  const [licenceOpen, setLicenceOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const videoBRef = useRef<HTMLVideoElement>(null);
  const wipeDragging = useRef(false);

  const take = takes[idx];
  const bTake = takes[bIdx];

  const scheduleTimecodeUpdate = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if ((v as any).requestVideoFrameCallback) {
      (v as any).requestVideoFrameCallback(({ mediaTime }: { mediaTime: number }) => {
        setTimecode(toTc(mediaTime));
        setProgress(v.duration ? mediaTime / v.duration : 0);
        if (!v.paused) scheduleTimecodeUpdate();
      });
    }
  }, []);

  // Sync B video time and play state to A.
  useEffect(() => {
    const a = videoRef.current, b = videoBRef.current;
    if (!a || !b || abMode === "single") return;
    const syncTime = () => { if (Math.abs(b.currentTime - a.currentTime) > 0.1) b.currentTime = a.currentTime; };
    const syncPlay = () => { b.play().catch(() => {}); };
    const syncPause = () => { b.pause(); };
    a.addEventListener("timeupdate", syncTime);
    a.addEventListener("play", syncPlay);
    a.addEventListener("pause", syncPause);
    return () => { a.removeEventListener("timeupdate", syncTime); a.removeEventListener("play", syncPlay); a.removeEventListener("pause", syncPause); };
  }, [abMode]);

  function pinNote() {
    const t = noteInput.trim();
    if (!t || !take) return;
    setNotes((n) => [...n, { id: crypto.randomUUID(), takeId: take.takeId, time: videoRef.current?.currentTime ?? 0, text: t }]);
    setNoteInput("");
  }

  function nextTake() { if (idx < takes.length - 1) setIdx((i) => i + 1); }
  function prevTake() { if (idx > 0) setIdx((i) => i - 1); }
  function cycleAB() { setAbMode((m) => m === "single" ? "side-by-side" : m === "side-by-side" ? "wipe" : "single"); }

  async function submitDecision(state: "approved" | "rejected", reason?: string) {
    const t = take; if (!t) return;
    setBusy(t.takeId);
    setDecisions((d) => ({ ...d, [t.takeId]: { state, reason } }));
    try {
      if (t.songId && t.shotId) {
        const res = await fetch("/api/studio/review", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ songId: t.songId, shotId: t.shotId, decision: state, reviewer, reason }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        if (!data.chain_ok) setToast({ text: "Warning: ledger chain_ok failed", ok: false });
        else setToast({ text: state === "approved" ? "Approved — ledger updated" : "Rejected — reason recorded", ok: state === "approved" });
      } else {
        setToast({ text: state === "approved" ? "Approved (no ledger: no songId)" : "Rejected (no ledger)", ok: state === "approved" });
      }
      if (state === "approved") onApprove?.(t);
      else onReject?.(t, reason ?? "");
      if (autoAdvance) setTimeout(nextTake, 600);
    } catch (e: any) {
      setToast({ text: `Error: ${e?.message ?? String(e)}`, ok: false });
      setDecisions((d) => { const c = { ...d }; delete c[t.takeId]; return c; });
    } finally { setBusy(null); }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable) return;
      const v = videoRef.current;
      switch (e.key) {
        case "j": if (v) { v.playbackRate = 0.5; v.play(); setPlaying(true); scheduleTimecodeUpdate(); } break;
        case "k": if (v) { v.pause(); setPlaying(false); } break;
        case "l": if (v) { v.playbackRate = 1; v.play(); setPlaying(true); scheduleTimecodeUpdate(); } break;
        case " ": e.preventDefault(); if (v) { v.paused ? v.play().then(() => { setPlaying(true); scheduleTimecodeUpdate(); }) : (v.pause(), setPlaying(false)); } break;
        case "ArrowLeft": e.preventDefault(); if (v) v.currentTime = Math.max(0, v.currentTime - 1 / 30); break;
        case "ArrowRight": e.preventDefault(); if (v) v.currentTime = Math.min(v.duration || 0, v.currentTime + 1 / 30); break;
        case "a": if (take && !decisions[take.takeId]) submitDecision("approved"); break;
        case "r": setRejectOpen(true); break;
        case "n": nextTake(); break;
        case "p": prevTake(); break;
        case "\\": e.preventDefault(); cycleAB(); break;
        case "?": setCheatSheet((s) => !s); break;
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [take, decisions, idx, abMode, autoAdvance, scheduleTimecodeUpdate]);

  function onWipeDragStart(e: React.MouseEvent<HTMLDivElement>) {
    wipeDragging.current = true;
    const container = e.currentTarget.parentElement!;
    function onMove(ev: MouseEvent) {
      if (!wipeDragging.current) return;
      const rect = container.getBoundingClientRect();
      setWipeX(Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width)));
    }
    function onUp() { wipeDragging.current = false; document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  const takeNotes = notes.filter((n) => n.takeId === take?.takeId);
  const decision = take ? decisions[take.takeId] : undefined;

  if (!takes.length) {
    return (
      <div className="bg-panel border border-edge rounded-xl p-8 text-dim text-[15px] flex items-center justify-center" style={{ minHeight: "40vh" }}>
        No takes in the review queue. Generate shots first (Stage 4 · Asset Gen).
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3" style={{ minHeight: "70vh" }}>
      {/* Toolbar */}
      <div className="bg-panel border border-edge rounded-xl px-4 py-2 flex items-center justify-between gap-3">
        <div className="text-[12px] text-dim">REVIEW ROOM · {takes.length} take{takes.length !== 1 ? "s" : ""} · {Object.keys(decisions).length} decided</div>
        <div className="flex items-center gap-2">
          <button onClick={cycleAB} className={"px-2.5 py-1 rounded text-[12px] border " + (abMode !== "single" ? "border-accent/50 text-accent bg-accent/10" : "border-edge text-dim hover:text-fg")}>
            {abMode === "single" ? "A only" : abMode === "side-by-side" ? "A|B" : "wipe"}
          </button>
          <label className="flex items-center gap-1.5 text-[12px] text-dim cursor-pointer">
            <input type="checkbox" checked={autoAdvance} onChange={(e) => setAutoAdvance(e.target.checked)} className="rounded" /> auto-advance
          </label>
          <button onClick={() => setCheatSheet((s) => !s)} className="text-dim text-[12px] border border-edge rounded px-2 py-0.5 hover:text-fg">? keys</button>
        </div>
      </div>

      {cheatSheet && (
        <div className="bg-panel border border-edge rounded-xl px-4 py-3 font-mono grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-[12px]">
          {CHEAT.map(([k, v]) => <div key={k}><span className="text-accent">{k}</span><span className="text-dim"> — {v}</span></div>)}
        </div>
      )}

      {/* Main layout: playlist | viewer | inspector */}
      <div className="grid gap-3 flex-1" style={{ gridTemplateColumns: "190px 1fr 252px", minHeight: "56vh" }}>
        {/* Playlist */}
        <div className="bg-panel border border-edge rounded-xl overflow-auto">
          <div className="text-[11px] text-dim uppercase tracking-wide px-3 py-2 border-b border-edge">Playlist</div>
          <div className="p-2 space-y-1">
            {takes.map((t, i) => {
              const d = decisions[t.takeId];
              return (
                <button key={t.takeId} onClick={() => setIdx(i)}
                  className={"w-full text-left rounded-md px-2.5 py-2 text-[13px] border " + (i === idx ? "bg-raised border-edge" : "border-transparent hover:bg-raised/40")}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono truncate max-w-[100px]">{t.label}</span>
                    <span className="text-[10px] shrink-0" style={{ color: d?.state === "approved" ? "#57c97a" : d?.state === "rejected" ? "#ef6f6c" : "#97a1ad" }}>
                      {d?.state === "approved" ? "✓" : d?.state === "rejected" ? "✗" : "○"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {t.sceneNumber != null && <span className="text-[10px] text-dim">S{t.sceneNumber}</span>}
                    {t.c2paStatus && (
                      <span data-c2pa={t.c2paStatus} className="text-[9px] font-mono px-1 rounded" style={{ color: C2PA_CHIP[t.c2paStatus].color, background: `${C2PA_CHIP[t.c2paStatus].color}22` }}>
                        {C2PA_CHIP[t.c2paStatus].label}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Viewer */}
        <div className="bg-panel border border-edge rounded-xl overflow-hidden flex flex-col min-h-0">
          <div className="relative flex-1 bg-black overflow-hidden" style={{ minHeight: "220px" }}>
            <div className={abMode === "side-by-side" ? "flex h-full" : "h-full"}>
              {take?.url ? (
                <video ref={videoRef} src={take.url}
                  style={{ width: abMode === "side-by-side" ? "50%" : "100%", height: "100%", objectFit: "contain" }}
                  onPlay={() => { setPlaying(true); scheduleTimecodeUpdate(); }}
                  onPause={() => setPlaying(false)}
                  onLoadedMetadata={(e) => { const v = e.currentTarget; setDuration(v.duration); setTimecode(toTc(v.currentTime)); }}
                  onTimeUpdate={(e) => { const v = e.currentTarget; setTimecode(toTc(v.currentTime)); setProgress(v.duration ? v.currentTime / v.duration : 0); }}
                />
              ) : (
                <div className="flex items-center justify-center w-full h-full text-dim text-[13px]">no video</div>
              )}
              {abMode === "side-by-side" && bTake?.url && (
                <video ref={videoBRef} src={bTake.url} style={{ width: "50%", height: "100%", objectFit: "contain" }} />
              )}
            </div>
            {abMode === "wipe" && bTake?.url && (
              <>
                <video ref={videoBRef} src={bTake.url} className="absolute inset-0 w-full h-full"
                  style={{ objectFit: "contain", clipPath: `inset(0 ${Math.round((1 - wipeX) * 100)}% 0 0)` }} />
                <div className="absolute top-0 bottom-0 w-0.5 bg-white/60 cursor-ew-resize z-10"
                  style={{ left: `${wipeX * 100}%` }} onMouseDown={onWipeDragStart} />
                <div className="absolute top-2 left-2 text-[11px] text-white/70 font-mono select-none pointer-events-none">A</div>
                <div className="absolute top-2 text-[11px] text-white/70 font-mono select-none pointer-events-none" style={{ left: `calc(${wipeX * 100}% + 6px)` }}>B</div>
              </>
            )}
            <div className="absolute bottom-2 right-2 text-[11px] font-mono text-white/80 bg-black/60 rounded px-1.5 py-0.5 select-none">{timecode}</div>
            {decision && (
              <div className="absolute top-2 left-2 text-[11px] font-mono rounded px-2 py-0.5 select-none"
                style={{ background: decision.state === "approved" ? "rgba(87,201,122,.85)" : "rgba(239,111,108,.85)", color: "#fff" }}>
                {decision.state === "approved" ? "✓ APPROVED" : "✗ REJECTED"}
              </div>
            )}
          </div>

          {/* Scrub bar + note markers */}
          <div className="relative h-1.5 bg-ink border-t border-edge cursor-pointer"
            onClick={(e) => { const v = videoRef.current; if (!v) return; const r = e.currentTarget.getBoundingClientRect(); v.currentTime = ((e.clientX - r.left) / r.width) * (v.duration || 0); }}>
            <div className="h-full bg-accent/60 pointer-events-none" style={{ width: `${progress * 100}%` }} />
            {takeNotes.map((n) => (
              <div key={n.id} title={n.text} className="absolute top-0 bottom-0 w-0.5 pointer-events-none"
                style={{ left: `${(n.time / (duration || 1)) * 100}%`, background: "#e0a13a" }} />
            ))}
          </div>

          {/* Transport */}
          <div className="bg-raised border-t border-edge px-3 py-2 flex items-center gap-2 text-[16px]">
            <button onClick={prevTake} title="P — prev take" className="text-dim hover:text-fg px-1">⏮</button>
            <button onClick={() => { const v = videoRef.current; if (v) v.currentTime = Math.max(0, v.currentTime - 1 / 30); }} title="← frame back" className="text-dim hover:text-fg px-1 text-[13px]">⏪</button>
            <button onClick={() => { const v = videoRef.current; if (!v) return; v.paused ? v.play().then(() => { setPlaying(true); scheduleTimecodeUpdate(); }) : (v.pause(), setPlaying(false)); }} className="text-fg w-7 text-center">{playing ? "⏸" : "▶"}</button>
            <button onClick={() => { const v = videoRef.current; if (v) v.currentTime = Math.min(v.duration || 0, v.currentTime + 1 / 30); }} title="→ frame forward" className="text-dim hover:text-fg px-1 text-[13px]">⏩</button>
            <button onClick={nextTake} title="N — next take" className="text-dim hover:text-fg px-1">⏭</button>
            <span className="ml-auto text-[11px] font-mono text-dim">{timecode}</span>
          </div>
        </div>

        {/* Inspector */}
        <div className="bg-panel border border-edge rounded-xl overflow-auto flex flex-col">
          <div className="text-[11px] text-dim uppercase tracking-wide px-3 py-2 border-b border-edge">Inspector</div>
          <div className="flex-1 p-3 space-y-4 overflow-auto">
            {/* Metadata */}
            <dl className="text-[12px] font-mono space-y-1">
              <div className="flex justify-between"><dt className="text-dim">take</dt><dd className="truncate max-w-[140px]">{take?.takeId ?? "—"}</dd></div>
              {take?.shotId && <div className="flex justify-between"><dt className="text-dim">shot</dt><dd className="truncate max-w-[140px]">{take.shotId}</dd></div>}
              {take?.songId && <div className="flex justify-between"><dt className="text-dim">song</dt><dd>{take.songId}</dd></div>}
              {take?.sceneNumber != null && <div className="flex justify-between"><dt className="text-dim">scene</dt><dd>{take.sceneNumber}</dd></div>}
            </dl>

            {/* Source & Licence */}
            {take && (
              <div>
                <button
                  onClick={() => setLicenceOpen((v) => !v)}
                  className="flex items-center justify-between w-full text-[11px] text-dim uppercase tracking-wide mb-1 hover:text-fg"
                >
                  <span>Source &amp; Licence</span>
                  <span>{licenceOpen ? "▴" : "▾"}</span>
                </button>
                {licenceOpen && (
                  <div className="bg-ink rounded-md p-2.5 text-[11px] font-mono space-y-1.5">
                    {take.c2paStatus ? (
                      <div className="flex items-center gap-1.5">
                        <span className="text-dim">C2PA</span>
                        <span data-c2pa={take.c2paStatus} style={{ color: C2PA_CHIP[take.c2paStatus].color }}>{C2PA_CHIP[take.c2paStatus].label}</span>
                      </div>
                    ) : (
                      <div className="text-dim">C2PA — unknown</div>
                    )}
                    {take.model ? (
                      <div className="flex gap-1.5"><span className="text-dim">model</span><span className="text-fg truncate">{take.model}</span></div>
                    ) : (
                      <div className="text-dim">model — not recorded</div>
                    )}
                    {take.shotId && <div className="flex gap-1.5"><span className="text-dim">shot</span><span className="text-fg">{take.shotId}</span></div>}
                    {take.songId && <div className="flex gap-1.5"><span className="text-dim">song</span><span className="text-fg">{take.songId}</span></div>}
                    <div className="text-dim pt-1 border-t border-edge/40">AI-generated — Ilyrium internal use. No third-party rights claimed.</div>
                  </div>
                )}
              </div>
            )}

            {/* Decision */}
            <div>
              <div className="text-[11px] text-dim uppercase tracking-wide mb-2">Decision</div>
              {decision ? (
                <div className="rounded-md px-2.5 py-2 border text-[13px]"
                  style={{ borderColor: decision.state === "approved" ? "#57c97a55" : "#ef6f6c55", background: decision.state === "approved" ? "rgba(87,201,122,.08)" : "rgba(239,111,108,.08)" }}>
                  <div style={{ color: decision.state === "approved" ? "#57c97a" : "#ef6f6c" }}>{decision.state === "approved" ? "✓ Approved" : "✗ Rejected"}</div>
                  {decision.reason && <div className="text-dim text-[11px] mt-0.5">{decision.reason}</div>}
                </div>
              ) : (
                <div className="space-y-2">
                  <button disabled={!!busy} onClick={() => submitDecision("approved")}
                    className="w-full text-left rounded-md px-3 py-1.5 text-[13px] border disabled:opacity-50"
                    style={{ color: "#57c97a", borderColor: "#57c97a55", background: "rgba(87,201,122,.10)" }}>
                    {busy === take?.takeId ? "…" : "A — Approve"}
                  </button>
                  <button disabled={!!busy} onClick={() => setRejectOpen(true)}
                    className="w-full text-left rounded-md px-3 py-1.5 text-[13px] border disabled:opacity-50"
                    style={{ color: "#ef6f6c", borderColor: "#ef6f6c55", background: "rgba(239,111,108,.10)" }}>
                    R — Reject…
                  </button>
                </div>
              )}
            </div>

            {/* Frame notes */}
            <div>
              <div className="text-[11px] text-dim uppercase tracking-wide mb-1">Frame notes</div>
              <div className="flex gap-1.5 mb-2">
                <input value={noteInput} onChange={(e) => setNoteInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && pinNote()}
                  placeholder="note at current frame…"
                  className="flex-1 bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1" />
                <button onClick={pinNote} className="border border-edge text-dim rounded-md px-2 py-1 text-[12px] hover:text-fg">+</button>
              </div>
              {takeNotes.length === 0 && <div className="text-dim text-[12px]">No notes yet.</div>}
              {takeNotes.map((n) => (
                <div key={n.id} className="flex gap-2 text-[12px] py-1 border-t border-edge first:border-t-0">
                  <span className="font-mono shrink-0" style={{ color: "#e0a13a" }}>{toTc(n.time)}</span>
                  <span className="text-dim flex-1 break-words">{n.text}</span>
                  <button onClick={() => setNotes((ns) => ns.filter((x) => x.id !== n.id))} className="text-dim hover:text-bad text-[11px] shrink-0">×</button>
                </div>
              ))}
            </div>

            {/* B take selector (A/B modes) */}
            {abMode !== "single" && (
              <div>
                <div className="text-[11px] text-dim uppercase tracking-wide mb-1">B take</div>
                <select value={bIdx} onChange={(e) => setBIdx(Number(e.target.value))}
                  className="w-full bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1.5">
                  {takes.map((t, i) => <option key={t.takeId} value={i}>{t.label}</option>)}
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Reject dialog */}
      {rejectOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setRejectOpen(false)}>
          <div className="bg-panel border border-edge rounded-xl p-5 w-96 max-w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="text-[16px] font-semibold mb-1">Reject take</div>
            <div className="text-[13px] text-dim mb-3">Rejection is appended to the ledger. Takes are never deleted.</div>
            <textarea autoFocus value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Reason for rejection (required)…" rows={3}
              className="w-full bg-ink border border-edge rounded-md text-fg text-[14px] p-2 mb-3" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setRejectOpen(false); setRejectReason(""); }}
                className="border border-edge text-dim rounded-md px-3 py-1.5 text-[14px]">Cancel</button>
              <button disabled={!rejectReason.trim() || !!busy}
                onClick={() => { const r = rejectReason.trim(); setRejectOpen(false); setRejectReason(""); submitDecision("rejected", r); }}
                className="rounded-md px-3 py-1.5 text-[14px] disabled:opacity-50"
                style={{ color: "#ef6f6c", border: "1px solid rgba(239,111,108,.4)", background: "rgba(239,111,108,.10)" }}>
                Confirm reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 rounded-xl px-4 py-3 text-[13px] max-w-sm border shadow-xl"
          style={{ background: toast.ok ? "rgba(87,201,122,.15)" : "rgba(239,111,108,.15)", borderColor: toast.ok ? "#57c97a55" : "#ef6f6c55", color: toast.ok ? "#57c97a" : "#ef6f6c" }}>
          {toast.text}
          <button onClick={() => setToast(null)} className="ml-3 text-dim text-[11px]">×</button>
        </div>
      )}
    </div>
  );
}

// Wrapper for Pipeline.tsx stage 5: fetches shots from the pipeline service.
export function ReviewPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [takes, setTakes] = useState<ReviewTake[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) { setLoading(false); return; }
    fetch(`${pipe}/pipeline/${runId}/shots`)
      .then((r) => r.json())
      .then((d: any) => {
        const ts: ReviewTake[] = [];
        for (const s of (d.shots || [])) {
          for (const t of (s.takes || [])) {
            const url: string = t.public_url || (t.file ? `${pipe}/media/${runId}/${t.file}` : "");
            if (!url) continue;
            const model: string | null = t.model ?? null;
            const c2paStatus: C2PAStatus = t.c2pa_status ?? (model ? "valid" : "missing");
            ts.push({
              takeId: t.take_id,
              shotId: s.shot_id ?? `scene-${s.scene_number}`,
              songId: s.song_id,
              sceneNumber: s.scene_number,
              label: `S${s.scene_number} · ${String(t.take_id).slice(0, 6)} · ${model ?? ""}`,
              url,
              model,
              c2paStatus,
            });
          }
        }
        setTakes(ts);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [runId, pipe]);

  async function handleReject(t: ReviewTake, reason: string) {
    if (!t.sceneNumber) return;
    try {
      await fetch(`${pipe}/pipeline/${runId}/shot/${t.sceneNumber}/action`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ op: "regenerate", reason }),
      });
    } catch { /* best-effort re-gen trigger */ }
  }

  if (loading) return <div className="text-dim text-[14px] mb-3">Loading shots…</div>;
  return <ReviewRoom takes={takes} onReject={handleReject} />;
}
