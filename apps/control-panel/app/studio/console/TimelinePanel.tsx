"use client";

import { useEffect, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type TimelineTake = {
  take_id: string;
  ok?: boolean;
  approval?: string | null; // "approved" | "rejected" | null
  model?: string | null;
  public_url?: string | null;
  file?: string | null;
};

export type TimelineShot = {
  scene_number: number;
  shot_id?: string;
  duration_s?: number;
  keyframe_url?: string | null;
  keyframe_file?: string | null;
  selected_take?: string | null;
  takes: TimelineTake[];
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function mediaSrc(t: TimelineTake, pipe: string, runId: string): string {
  return t.public_url || (t.file ? `${pipe}/media/${runId}/${t.file}` : "");
}

function keyframeSrc(s: TimelineShot, pipe: string, runId: string): string {
  if (s.keyframe_url) return s.keyframe_url;
  if (s.keyframe_file) return `${pipe}/media/${runId}/${s.keyframe_file}`;
  return "";
}

function shotApproval(s: TimelineShot): "approved" | "rejected" | "pending" {
  const sel = s.takes.find((t) => t.take_id === s.selected_take) ?? s.takes[s.takes.length - 1];
  if (!sel) return "pending";
  if (sel.approval === "approved") return "approved";
  if (sel.approval === "rejected") return "rejected";
  return "pending";
}

const APPROVAL_COLORS: Record<string, string> = {
  approved: "#57c97a",
  rejected: "#ef6f6c",
  pending: "#97a1ad",
};
const APPROVAL_LABELS: Record<string, string> = {
  approved: "✓",
  rejected: "✗",
  pending: "▢",
};

// ── Waveform container ────────────────────────────────────────────────────────

function WaveformRuler({ shots, totalDuration, playheadFrac, onSeek }: {
  shots: TimelineShot[];
  totalDuration: number;
  playheadFrac: number;
  onSeek: (frac: number) => void;
}) {
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    onSeek((e.clientX - rect.left) / rect.width);
  };
  let acc = 0;
  return (
    <div className="relative h-8 bg-raised border border-edge rounded cursor-pointer select-none" onClick={handleClick}>
      {/* Tick marks at shot boundaries */}
      {shots.map((s) => {
        const frac = acc / totalDuration;
        acc += s.duration_s ?? 5;
        return (
          <div key={s.scene_number} className="absolute top-0 h-full border-l border-edge/60"
            style={{ left: `${frac * 100}%` }}>
            <span className="text-[9px] text-dim absolute -top-0 left-0.5 font-mono select-none">S{s.scene_number}</span>
          </div>
        );
      })}
      {/* Playhead */}
      <div className="absolute top-0 h-full w-0.5 pointer-events-none" style={{ left: `${playheadFrac * 100}%`, background: "#5b9dff" }} />
    </div>
  );
}

// ── Shot Track ────────────────────────────────────────────────────────────────

function ShotTrack({ shots, totalDuration, playheadFrac, onSeek, pipe, runId }: {
  shots: TimelineShot[];
  totalDuration: number;
  playheadFrac: number;
  onSeek: (frac: number) => void;
  pipe: string;
  runId: string;
}) {
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    onSeek((e.clientX - rect.left) / rect.width);
  };
  const TRACK_H = 72;
  let acc = 0;

  return (
    <div className="relative select-none cursor-pointer" style={{ height: TRACK_H + 22 }} onClick={handleClick}>
      <div className="relative w-full" style={{ height: TRACK_H }}>
        {shots.map((s) => {
          const dur = s.duration_s ?? 5;
          const leftPct = (acc / totalDuration) * 100;
          const widthPct = (dur / totalDuration) * 100;
          acc += dur;
          const state = shotApproval(s);
          const color = APPROVAL_COLORS[state];
          const selTake = s.takes.find((t) => t.take_id === s.selected_take) ?? s.takes[s.takes.length - 1];
          const kf = keyframeSrc(s, pipe, runId);
          const videoSrc = selTake ? mediaSrc(selTake, pipe, runId) : "";

          return (
            <div key={s.scene_number}
              className="absolute top-0 h-full overflow-hidden rounded-sm border"
              style={{ left: `${leftPct}%`, width: `calc(${widthPct}% - 2px)`, borderColor: color, background: "#0e1117" }}>
              {/* Keyframe or approved take video */}
              {(state === "approved" && videoSrc) ? (
                <video src={videoSrc} muted loop autoPlay playsInline
                  className="w-full h-full object-cover opacity-80"
                  style={{ pointerEvents: "none" }} />
              ) : kf ? (
                <img src={kf} alt={`S${s.scene_number}`}
                  className="w-full h-full object-cover"
                  style={{ opacity: state === "pending" ? 0.5 : 0.8 }} />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[10px] font-mono"
                  style={{ color: APPROVAL_COLORS.pending }}>S{s.scene_number}</div>
              )}
              {/* Scene number + approval badge */}
              <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-1 py-0.5"
                style={{ background: "rgba(0,0,0,0.55)" }}>
                <span className="text-[9px] font-mono text-white/70">S{s.scene_number}</span>
                <span className="text-[9px] font-bold" style={{ color }}>{APPROVAL_LABELS[state]}</span>
              </div>
              {/* Duration label */}
              <div className="absolute bottom-0 right-0 px-1 py-0.5 text-[9px] font-mono"
                style={{ background: "rgba(0,0,0,0.55)", color: "#97a1ad" }}>{dur}s</div>
            </div>
          );
        })}
      </div>

      {/* Take alternates row */}
      <div className="absolute bottom-0 left-0 right-0 h-[18px] flex overflow-hidden">
        {shots.map((s) => {
          const dur = s.duration_s ?? 5;
          const leftPct = ((s.takes.length > 0 ? shots.slice(0, shots.indexOf(s)).reduce((a, x) => a + (x.duration_s ?? 5), 0) : 0) / totalDuration) * 100;
          const widthPct = (dur / totalDuration) * 100;
          const alts = s.takes.filter((t) => t.take_id !== s.selected_take);
          if (alts.length === 0) return <div key={s.scene_number} style={{ width: `${widthPct}%` }} />;
          return (
            <div key={s.scene_number} className="flex gap-0.5 items-center overflow-hidden"
              style={{ width: `${widthPct}%`, minWidth: 0 }}>
              {alts.map((t) => (
                <div key={t.take_id}
                  className="shrink-0 h-[14px] rounded-sm border border-edge/60 font-mono flex items-center px-0.5"
                  style={{ background: "#1a1f28", color: t.approval === "approved" ? "#57c97a" : t.approval === "rejected" ? "#ef6f6c" : "#97a1ad", fontSize: 8 }}>
                  {t.take_id.slice(0, 6)}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* Playhead overlay */}
      <div className="absolute top-0 bottom-0 w-0.5 pointer-events-none"
        style={{ left: `${playheadFrac * 100}%`, background: "#5b9dff", boxShadow: "0 0 3px #5b9dff" }} />
    </div>
  );
}

// ── Main TimelinePanel component ──────────────────────────────────────────────

export default function TimelinePanel({ shots, audioUrl, pipe, runId, showAudioControls }: {
  shots: TimelineShot[];
  audioUrl?: string | null;
  pipe?: string;
  runId?: string;
  showAudioControls?: boolean;
}) {
  const waveContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<any>(null);
  const [playheadFrac, setPlayheadFrac] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [wsReady, setWsReady] = useState(false);
  const [wsError, setWsError] = useState(false);

  // Proportional total duration
  const totalDuration = shots.reduce((a, s) => a + (s.duration_s ?? 5), 0) || 64;

  // Timecode display
  const timeSec = Math.round(playheadFrac * totalDuration);
  const timeStr = `${String(Math.floor(timeSec / 60)).padStart(2, "0")}:${String(timeSec % 60).padStart(2, "0")}`;

  // Seek handler (shared between ruler/waveform and shot track clicks)
  function seekTo(frac: number) {
    const f = Math.max(0, Math.min(1, frac));
    setPlayheadFrac(f);
    if (wsRef.current && wsReady) {
      const dur = wsRef.current.getDuration?.() ?? totalDuration;
      wsRef.current.setTime?.(f * dur);
    }
  }

  // Initialize WaveSurfer when audioUrl is available
  useEffect(() => {
    if (!audioUrl || !waveContainerRef.current) return;
    let ws: any;
    let alive = true;

    (async () => {
      try {
        const WS = await import("wavesurfer.js");
        const WaveSurfer = (WS as any).default ?? WS;
        let plugins: any[] = [];
        try {
          const RP = await import("wavesurfer.js/dist/plugins/regions.js");
          const RegionsPlugin = (RP as any).default ?? RP;
          plugins = [RegionsPlugin.create()];
        } catch { /* regions optional */ }

        if (!alive || !waveContainerRef.current) return;
        ws = WaveSurfer.create({
          container: waveContainerRef.current,
          waveColor: "#334155",
          progressColor: "#5b9dff",
          height: 56,
          barWidth: 2,
          barGap: 1,
          normalize: true,
          interact: true,
          plugins,
        });
        wsRef.current = ws;

        ws.on("ready", () => {
          if (!alive) return;
          setWsReady(true);
          // Add shot-boundary regions
          try {
            const rp = ws.getActivePlugins?.()?.find((p: any) => p.addRegion);
            if (rp) {
              let t = 0;
              for (const s of shots) {
                const d = s.duration_s ?? 5;
                const state = shotApproval(s);
                rp.addRegion({
                  start: t, end: t + d,
                  color: state === "approved" ? "rgba(87,201,122,0.08)" : state === "rejected" ? "rgba(239,111,108,0.07)" : "rgba(151,161,173,0.04)",
                  drag: false, resize: false,
                });
                t += d;
              }
            }
          } catch { /* regions drawing is best-effort */ }
        });

        ws.on("timeupdate", (t: number) => {
          if (!alive) return;
          const dur = ws.getDuration?.() ?? totalDuration;
          if (dur > 0) setPlayheadFrac(t / dur);
        });
        ws.on("play", () => { if (alive) setPlaying(true); });
        ws.on("pause", () => { if (alive) setPlaying(false); });
        ws.on("error", () => { if (alive) setWsError(true); });

        ws.load(audioUrl);
      } catch { if (alive) setWsError(true); }
    })();

    return () => {
      alive = false;
      if (wsRef.current) { try { wsRef.current.destroy(); } catch {} wsRef.current = null; }
      setWsReady(false); setPlaying(false);
    };
  }, [audioUrl]);

  const safePipe = pipe ?? "http://127.0.0.1:8800";
  const safeRunId = runId ?? "";

  return (
    <div className="mb-4 space-y-2">
      {/* ── Header bar ── */}
      <div className="flex items-center gap-3">
        <div className="text-[11px] text-dim uppercase tracking-wide font-mono">TIMELINE</div>
        <div className="font-mono text-[13px] tabular-nums" style={{ color: "#5b9dff" }}>{timeStr}</div>
        <div className="text-[11px] text-dim">/ {totalDuration}s · {shots.length} shots</div>
        {audioUrl && !wsError && (
          <button
            onClick={() => wsRef.current?.playPause?.()}
            className="ml-auto border border-edge rounded px-2.5 py-0.5 text-[12px] hover:bg-raised"
            aria-label={playing ? "Pause" : "Play"}>
            {playing ? "⏸ Pause" : "▶ Play"}
          </button>
        )}
        {wsError && <span className="text-[11px] ml-auto" style={{ color: "#ef6f6c" }}>audio unavailable</span>}
      </div>

      {/* ── Waveform (wavesurfer) or ruler ── */}
      <div className="bg-raised border border-edge rounded overflow-hidden">
        {audioUrl && !wsError ? (
          <div ref={waveContainerRef} className="w-full" style={{ minHeight: 56 }} />
        ) : (
          <WaveformRuler shots={shots} totalDuration={totalDuration} playheadFrac={playheadFrac} onSeek={seekTo} />
        )}
      </div>

      {/* ── Shot track ── */}
      <div className="bg-raised border border-edge rounded p-1.5">
        <ShotTrack shots={shots} totalDuration={totalDuration} playheadFrac={playheadFrac}
          onSeek={seekTo} pipe={safePipe} runId={safeRunId} />
      </div>

      {/* ── Legend ── */}
      <div className="flex gap-4 text-[11px] text-dim">
        {Object.entries(APPROVAL_COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm border" style={{ borderColor: c, background: `${c}22` }} />
            {k}
          </span>
        ))}
        <span className="ml-2 italic">click timeline to seek · alt takes shown below main track</span>
      </div>

      {/* ── Audio controls (pipeline-backed mode) ── */}
      {showAudioControls && pipe && runId && (
        <AudioControlsPanel pipe={pipe} runId={runId} />
      )}
    </div>
  );
}

// ── Pipeline-backed wrapper (fetches shots + audio) ───────────────────────────

export function TimelinePipelinePanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [shots, setShots] = useState<TimelineShot[]>([]);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const r = await fetch(`${pipe}/pipeline/${runId}/shots`);
        const d = await r.json();
        if (alive) setShots(d.shots || []);
      } catch {}
      try {
        const r = await fetch(`${pipe}/pipeline/${runId}/cut`);
        const d = await r.json();
        const url = d?.cut?.public_url || (d?.cut?.file ? `${pipe}/media/${runId}/${d.cut.file}` : null);
        if (alive && url) setAudioUrl(url);
      } catch {}
    }
    load();
    return () => { alive = false; };
  }, [pipe, runId]);

  if (shots.length === 0) {
    return <div className="text-dim text-[14px] mb-3">No shots yet — run Script + Storyboard stages first.</div>;
  }
  return (
    <TimelinePanel shots={shots} audioUrl={audioUrl} pipe={pipe} runId={runId} showAudioControls />
  );
}

// ── Multi-track audio types ───────────────────────────────────────────────────

type TrackKind = "ambient" | "narrator" | "character" | "music" | "sfx";

interface AudioElement {
  url: string;
  kind: TrackKind;
  start_s: number;
  volume: number;
  ducking_db: number;
}

interface ShotAudioRow {
  scene_number: number;
  voiceover?: string;
  audio_elements: AudioElement[];
}

interface AddTrackDraft {
  scene_number: number;
  kind: TrackKind;
  url: string;
  volume: number;
  ducking_db: number;
}

const TRACK_COLORS: Record<TrackKind, { bg: string; label: string }> = {
  ambient:   { bg: "rgba(91,157,255,0.18)",  label: "#5b9dff" },
  narrator:  { bg: "rgba(240,167,61,0.22)",  label: "#f0a73d" },
  character: { bg: "rgba(185,140,255,0.22)", label: "#b98cff" },
  music:     { bg: "rgba(87,201,122,0.20)",  label: "#57c97a" },
  sfx:       { bg: "rgba(246,113,79,0.20)",  label: "#f6714f" },
};
const TRACK_KINDS: TrackKind[] = ["narrator", "ambient", "music", "character", "sfx"];

function MultiTrackLanesPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [shotRows, setShotRows] = useState<ShotAudioRow[]>([]);
  const [drawer, setDrawer] = useState<AddTrackDraft | null>(null);
  const [drawerBusy, setDrawerBusy] = useState(false);

  async function loadShots() {
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/cut`);
      const d = await r.json();
      setShotRows((d.shots || []).map((s: any) => ({
        scene_number: s.scene_number,
        voiceover: s.voiceover || "",
        audio_elements: s.audio_elements || [],
      })));
    } catch {}
  }

  useEffect(() => { loadShots(); }, [pipe, runId]);

  async function saveTrack() {
    if (!drawer) return;
    setDrawerBusy(true);
    try {
      await fetch(`${pipe}/pipeline/${runId}/audio`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          op: "add_track",
          scene_number: drawer.scene_number,
          tracks: [{ url: drawer.url.trim(), kind: drawer.kind, start_s: 0, volume: drawer.volume, ducking_db: drawer.ducking_db }],
        }),
      });
      setDrawer(null);
      await loadShots();
    } catch {}
    finally { setDrawerBusy(false); }
  }

  if (shotRows.length === 0) return null;

  return (
    <div className="pt-2 border-t border-edge space-y-2">
      <div className="text-[11px] text-dim uppercase tracking-wide">Multi-track lanes</div>
      <div className="overflow-x-auto">
        {TRACK_KINDS.map((kind) => {
          const c = TRACK_COLORS[kind];
          return (
            <div key={kind} className="flex items-center gap-2 mb-1">
              <span className="w-20 text-[11px] font-mono uppercase shrink-0" style={{ color: c.label }}>{kind}</span>
              <div className="flex flex-1 gap-1">
                {shotRows.map((s) => {
                  const tracksOfKind = s.audio_elements.filter((e) => e.kind === kind);
                  const isNarratorVo = kind === "narrator" && s.voiceover;
                  const hasContent = tracksOfKind.length > 0 || isNarratorVo;
                  return (
                    <div
                      key={s.scene_number}
                      title={tracksOfKind.map((t) => `${t.url} vol:${t.volume} duck:${t.ducking_db}dB`).join("\n") || (isNarratorVo ? s.voiceover : "")}
                      className="h-6 flex-1 min-w-[28px] rounded-sm border border-edge flex items-center justify-center text-[10px] font-mono"
                      style={{ background: hasContent ? c.bg : "#151a20", color: hasContent ? c.label : "#3a424d" }}
                    >
                      {hasContent ? (tracksOfKind.length > 0 ? tracksOfKind.length : "VO") : s.scene_number}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
        <div className="flex items-center gap-2 mt-1.5">
          <span className="w-20 text-[11px] text-dim shrink-0">add</span>
          <div className="flex flex-1 gap-1">
            {shotRows.map((s) => (
              <button
                key={s.scene_number}
                onClick={() => setDrawer({ scene_number: s.scene_number, kind: "ambient", url: "", volume: 1.0, ducking_db: -12 })}
                className="h-6 flex-1 min-w-[28px] rounded-sm border border-dashed border-edge text-[10px] text-dim hover:border-accent hover:text-accent"
                title={`Add track to scene ${s.scene_number}`}
              >+</button>
            ))}
          </div>
        </div>
      </div>

      {drawer && (
        <div className="bg-ink border border-edge rounded-lg p-2.5 space-y-2">
          <div className="text-[12px] font-semibold">Add track — Scene {drawer.scene_number}</div>
          <div className="flex flex-wrap gap-2 items-end">
            <label className="text-[11px] text-dim">
              Kind
              <select
                value={drawer.kind}
                onChange={(e) => setDrawer((d) => d && { ...d, kind: e.target.value as TrackKind })}
                className="ml-2 bg-panel border border-edge rounded text-fg text-[11px] px-1.5 py-0.5"
              >
                {TRACK_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            </label>
            <label className="text-[11px] text-dim flex-1 min-w-[180px]">
              File path
              <input
                value={drawer.url}
                onChange={(e) => setDrawer((d) => d && { ...d, url: e.target.value })}
                placeholder="absolute path or R2 URL"
                className="ml-2 w-full bg-panel border border-edge rounded text-fg text-[11px] px-1.5 py-0.5 font-mono"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <label className="text-[11px] text-dim flex items-center gap-1.5">
              Vol
              <input type="range" min={0} max={2} step={0.05} value={drawer.volume}
                onChange={(e) => setDrawer((d) => d && { ...d, volume: parseFloat(e.target.value) })} className="w-24" />
              <span className="font-mono w-8">{drawer.volume.toFixed(2)}</span>
            </label>
            <label className="text-[11px] text-dim flex items-center gap-1.5">
              Duck
              <input type="range" min={-30} max={0} step={1} value={drawer.ducking_db}
                onChange={(e) => setDrawer((d) => d && { ...d, ducking_db: parseInt(e.target.value) })} className="w-24" />
              <span className="font-mono w-10">{drawer.ducking_db}dB</span>
            </label>
            <div className="flex gap-1.5">
              <button disabled={drawerBusy || !drawer.url.trim()} onClick={saveTrack}
                className="text-good border border-good/40 rounded px-2.5 py-0.5 text-[11px] disabled:opacity-50"
                style={{ background: "rgba(87,201,122,0.12)" }}>
                {drawerBusy ? "saving…" : "Save"}
              </button>
              <button onClick={() => setDrawer(null)} className="border border-edge text-dim rounded px-2.5 py-0.5 text-[11px]">Cancel</button>
            </div>
          </div>
          <div className="text-[10px] text-dim">Duck applies when narrator/character also present — ambient/music reduced by dB value.</div>
        </div>
      )}
    </div>
  );
}

// ── Audio controls (split from AudioTimelinePanel) ────────────────────────────

function AudioControlsPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [duck, setDuck] = useState(0.35);
  const [music, setMusic] = useState("");
  const [busy, setBusy] = useState("");
  const [casting, setCasting] = useState<Record<string, string>>({});
  const [castRows, setCastRows] = useState<{ name: string; voice_id: string }[]>([{ name: "narrator", voice_id: "" }]);

  async function act(op: string, extra: any = {}) {
    setBusy(op);
    try { await fetch(`${pipe}/pipeline/${runId}/audio`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ op, ...extra }) }); }
    catch {} finally { setBusy(""); }
  }

  async function saveCasting() {
    setBusy("cast");
    const map: any = {};
    castRows.forEach((r) => { if (r.name.trim()) map[r.name.trim()] = { voice_id: r.voice_id.trim() }; });
    try { await fetch(`${pipe}/pipeline/${runId}/voices`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ casting: map }) }); }
    catch {} finally { setBusy(""); }
  }

  return (
    <div className="bg-panel border border-edge rounded-xl p-3 space-y-3">
      <div className="text-[11px] text-dim uppercase tracking-wide">Audio Mix</div>

      {/* VO duck */}
      <label className="flex items-center gap-2 text-[13px]">
        <span className="text-dim w-16">VO duck</span>
        <input type="range" min={0} max={1} step={0.05} value={duck}
          onChange={(e) => setDuck(parseFloat(e.target.value))}
          onMouseUp={() => act("set_duck", { level: duck })} className="flex-1" />
        <span className="font-mono w-10 text-[12px]">{duck.toFixed(2)}</span>
      </label>

      {/* Music bed */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-dim text-[13px] w-16">Music</span>
        <input value={music} onChange={(e) => setMusic(e.target.value)}
          placeholder="mood / genre / tempo"
          className="bg-ink border border-edge rounded-md text-fg text-[13px] px-2 py-1 flex-1 min-w-[160px]" />
        <button disabled={!!busy || !music.trim()}
          onClick={() => act("gen_music", { music_prompt: music.trim(), instrumental: true })}
          className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50"
          style={{ background: "rgba(91,157,255,0.12)" }}>
          {busy === "gen_music" ? "generating…" : "Generate"}
        </button>
      </div>

      {/* Reassemble */}
      <div className="flex items-center gap-2 pt-2 border-t border-edge">
        <button disabled={!!busy}
          onClick={() => act("reassemble")}
          className="text-good border border-good/40 rounded-md px-3 py-1.5 text-[13px] disabled:opacity-50"
          style={{ background: "rgba(87,201,122,0.12)" }}>
          {busy === "reassemble" ? "assembling…" : "Reassemble cut"}
        </button>
        <span className="text-[11px] text-dim">Approved takes → first cut · holds for unapproved shots</span>
      </div>

      {/* Multi-track lanes + add-track drawer */}
      <MultiTrackLanesPanel pipe={pipe} runId={runId} />

      {/* Voice casting */}
      <div className="pt-2 border-t border-edge">
        <div className="text-[11px] text-dim uppercase tracking-wide mb-1.5">Voice casting</div>
        {castRows.map((r, i) => (
          <div key={i} className="flex gap-2 mb-1">
            <input value={r.name}
              onChange={(e) => setCastRows((p) => p.map((x, j) => j === i ? { ...x, name: e.target.value } : x))}
              placeholder="character" className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 w-36" />
            <input value={r.voice_id}
              onChange={(e) => setCastRows((p) => p.map((x, j) => j === i ? { ...x, voice_id: e.target.value } : x))}
              placeholder="voice_id" className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 flex-1 font-mono" />
          </div>
        ))}
        <div className="flex gap-2 mt-1">
          <button onClick={() => setCastRows((p) => [...p, { name: "", voice_id: "" }])}
            className="text-accent border border-accent/40 rounded px-2 py-0.5 text-[12px]"
            style={{ background: "rgba(91,157,255,0.12)" }}>＋</button>
          <button disabled={!!busy} onClick={saveCasting}
            className="text-good border border-good/40 rounded px-2 py-0.5 text-[12px] disabled:opacity-50"
            style={{ background: "rgba(87,201,122,0.12)" }}>{busy === "cast" ? "saving…" : "Save casting"}</button>
        </div>
      </div>
    </div>
  );
}
