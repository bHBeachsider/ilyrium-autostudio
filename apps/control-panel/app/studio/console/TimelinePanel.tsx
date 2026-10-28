"use client";

import { useEffect, useState } from "react";

// Track-kind colour palette (background / text)
const TRACK_COLORS: Record<string, { bg: string; label: string }> = {
  ambient:   { bg: "rgba(91,157,255,0.18)",   label: "#5b9dff" },
  narrator:  { bg: "rgba(240,167,61,0.22)",   label: "#f0a73d" },
  character: { bg: "rgba(185,140,255,0.22)",  label: "#b98cff" },
  music:     { bg: "rgba(87,201,122,0.20)",   label: "#57c97a" },
  sfx:       { bg: "rgba(246,113,79,0.20)",   label: "#f6714f" },
};
const TRACK_KINDS = ["ambient", "narrator", "character", "music", "sfx"] as const;
type TrackKind = typeof TRACK_KINDS[number];

interface AudioElement {
  url: string;
  kind: TrackKind;
  start_s: number;
  volume: number;
  ducking_db: number;
}

interface ShotRow {
  scene_number: number;
  voiceover: string;
  has_video: boolean;
  audio_elements: AudioElement[];
}

interface CutData {
  run_id: string;
  audio_duck: number;
  music: boolean;
  voice_casting: Record<string, unknown>;
  cut: { cut_id: string; file: string | null; public_url: string | null; release: unknown } | null;
  shots: ShotRow[];
}

// Drawer state for adding a new track to a specific shot
interface AddTrackDraft {
  scene_number: number;
  kind: TrackKind;
  url: string;
  volume: number;
  ducking_db: number;
}

export function TimelinePanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [cut, setCut] = useState<CutData | null>(null);
  const [duck, setDuck] = useState(0.35);
  const [music, setMusic] = useState("");
  const [busy, setBusy] = useState("");
  const [drawer, setDrawer] = useState<AddTrackDraft | null>(null);
  const [drawerBusy, setDrawerBusy] = useState(false);

  async function load() {
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/cut`);
      const d = await r.json();
      setCut(d);
      if (typeof d.audio_duck === "number") setDuck(d.audio_duck);
    } catch {}
  }
  useEffect(() => { load(); }, [runId]);

  async function act(op: string, extra: Record<string, unknown> = {}) {
    setBusy(op);
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/audio`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ op, ...extra }),
      });
      const d = await r.json();
      if (d.run_id || d.shots) {
        setCut(d);
        if (typeof d.audio_duck === "number") setDuck(d.audio_duck);
      }
    } catch {}
    finally { setBusy(""); }
  }

  async function saveTrack() {
    if (!drawer) return;
    setDrawerBusy(true);
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/audio`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          op: "add_track",
          scene_number: drawer.scene_number,
          tracks: [{
            url: drawer.url.trim(),
            kind: drawer.kind,
            start_s: 0,
            volume: drawer.volume,
            ducking_db: drawer.ducking_db,
          }],
        }),
      });
      const d = await r.json();
      if (d.shots) setCut(d);
      setDrawer(null);
    } catch {}
    finally { setDrawerBusy(false); }
  }

  const cutSrc = cut?.cut?.public_url || (cut?.cut?.file ? `${pipe}/media/${runId}/${cut.cut.file}` : "");
  const shots = cut?.shots || [];

  return (
    <div className="mb-4 space-y-3">
      {/* Master preview */}
      <div className="aspect-video bg-black rounded-md overflow-hidden flex items-center justify-center text-dim text-[13px]">
        {cutSrc
          ? <video src={cutSrc} controls className="w-full h-full object-contain" />
          : "no cut assembled yet — Reassemble below"}
      </div>

      {/* Waveform scrubber placeholder + multi-track lanes */}
      {shots.length > 0 && (
        <div className="bg-ink border border-edge rounded-lg p-3 overflow-x-auto">
          {/* Track-kind rows */}
          {(["narrator", "ambient", "music", "character", "sfx"] as TrackKind[]).map((kind) => {
            const c = TRACK_COLORS[kind];
            return (
              <div key={kind} className="flex items-center gap-2 mb-1.5">
                <span className="w-20 text-[11px] font-mono uppercase shrink-0" style={{ color: c.label }}>
                  {kind}
                </span>
                <div className="flex flex-1 gap-1">
                  {shots.map((s) => {
                    const tracksOfKind = s.audio_elements.filter((e) => e.kind === kind);
                    const isNarratorVo = kind === "narrator" && s.voiceover;
                    const hasContent = tracksOfKind.length > 0 || isNarratorVo;
                    return (
                      <div
                        key={s.scene_number}
                        title={tracksOfKind.map((t) => `${t.url} vol:${t.volume} duck:${t.ducking_db}dB`).join("\n") || (isNarratorVo ? s.voiceover : "")}
                        className="h-7 flex-1 min-w-[36px] rounded-sm border border-edge flex items-center justify-center text-[10px] font-mono relative"
                        style={{
                          background: hasContent ? c.bg : "#151a20",
                          color: hasContent ? c.label : "#3a424d",
                        }}
                      >
                        {hasContent
                          ? (tracksOfKind.length > 0 ? tracksOfKind.length : "VO")
                          : s.scene_number}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* Per-shot "Add track" buttons */}
          <div className="flex items-center gap-2 mt-2">
            <span className="w-20 text-[11px] text-dim shrink-0">add</span>
            <div className="flex flex-1 gap-1">
              {shots.map((s) => (
                <button
                  key={s.scene_number}
                  onClick={() =>
                    setDrawer({
                      scene_number: s.scene_number,
                      kind: "ambient",
                      url: "",
                      volume: 1.0,
                      ducking_db: -12,
                    })
                  }
                  className="h-7 flex-1 min-w-[36px] rounded-sm border border-dashed border-edge text-[10px] text-dim hover:border-accent hover:text-accent"
                  title={`Add track to scene ${s.scene_number}`}
                >
                  +
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Add-track drawer */}
      {drawer && (
        <div className="bg-ink border border-edge rounded-lg p-3 space-y-2">
          <div className="text-[13px] font-semibold">
            Add track — Scene {drawer.scene_number}
          </div>

          <div className="flex flex-wrap gap-2 items-end">
            {/* Kind */}
            <label className="text-[12px] text-dim">
              Kind
              <select
                value={drawer.kind}
                onChange={(e) => setDrawer((d) => d && { ...d, kind: e.target.value as TrackKind })}
                className="ml-2 bg-panel border border-edge rounded-md text-fg text-[12px] px-2 py-1"
              >
                {TRACK_KINDS.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </label>

            {/* File path / URL */}
            <label className="text-[12px] text-dim flex-1 min-w-[200px]">
              File path
              <input
                value={drawer.url}
                onChange={(e) => setDrawer((d) => d && { ...d, url: e.target.value })}
                placeholder="absolute local path or R2 URL"
                className="ml-2 w-full bg-panel border border-edge rounded-md text-fg text-[12px] px-2 py-1 font-mono"
              />
            </label>
          </div>

          <div className="flex flex-wrap gap-4 items-center">
            {/* Volume */}
            <label className="text-[12px] text-dim flex items-center gap-2">
              Volume
              <input
                type="range" min={0} max={2} step={0.05} value={drawer.volume}
                onChange={(e) => setDrawer((d) => d && { ...d, volume: parseFloat(e.target.value) })}
                className="w-28"
              />
              <span className="font-mono w-10">{drawer.volume.toFixed(2)}</span>
            </label>

            {/* Ducking */}
            <label className="text-[12px] text-dim flex items-center gap-2">
              Duck (dB)
              <input
                type="range" min={-30} max={0} step={1} value={drawer.ducking_db}
                onChange={(e) => setDrawer((d) => d && { ...d, ducking_db: parseInt(e.target.value) })}
                className="w-28"
              />
              <span className="font-mono w-10">{drawer.ducking_db} dB</span>
            </label>

            <div className="flex gap-2">
              <button
                disabled={drawerBusy || !drawer.url.trim()}
                onClick={saveTrack}
                className="text-good border border-good/40 rounded-md px-3 py-1 text-[12px] disabled:opacity-50"
                style={{ background: "rgba(87,201,122,0.12)" }}
              >
                {drawerBusy ? "saving…" : "Save track"}
              </button>
              <button
                onClick={() => setDrawer(null)}
                className="border border-edge text-dim rounded-md px-3 py-1 text-[12px]"
              >
                Cancel
              </button>
            </div>
          </div>
          <div className="text-[11px] text-dim">
            Ducking applies when a narrator or character track is also present for this scene — ambient and music tracks will be reduced by the dB value you set.
          </div>
        </div>
      )}

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-edge">
        <label className="flex items-center gap-2 text-[13px]">
          <span className="text-dim">VO duck</span>
          <input
            type="range" min={0} max={1} step={0.05} value={duck}
            onChange={(e) => setDuck(parseFloat(e.target.value))}
            onMouseUp={() => act("set_duck", { level: duck })}
          />
          <span className="font-mono w-10">{duck.toFixed(2)}</span>
        </label>

        <span className="flex items-center gap-2">
          <input
            value={music}
            onChange={(e) => setMusic(e.target.value)}
            placeholder="music bed: mood / genre / tempo"
            className="bg-ink border border-edge rounded-md text-fg text-[13px] px-2 py-1 w-56"
          />
          <button
            disabled={!!busy || !music.trim()}
            onClick={() => act("gen_music", { music_prompt: music.trim(), instrumental: true })}
            className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50"
            style={{ background: "rgba(91,157,255,0.12)" }}
          >
            {busy === "gen_music" ? "generating…" : "Generate music"}
          </button>
        </span>

        <button
          disabled={!!busy}
          onClick={() => act("reassemble")}
          className="text-good border border-good/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50"
          style={{ background: "rgba(87,201,122,0.12)" }}
        >
          {busy === "reassemble" ? "assembling…" : "Reassemble cut"}
        </button>
      </div>

      {/* Voice casting */}
      {cut && (
        <VoiceCasting
          pipe={pipe}
          runId={runId}
          casting={cut.voice_casting || {}}
          onSaved={setCut}
        />
      )}
    </div>
  );
}

function VoiceCasting({
  pipe, runId, casting, onSaved,
}: {
  pipe: string;
  runId: string;
  casting: Record<string, unknown>;
  onSaved: (d: CutData) => void;
}) {
  const [rows, setRows] = useState<{ name: string; voice_id: string }[]>(
    Object.keys(casting).length
      ? Object.entries(casting).map(([name, v]: [string, unknown]) => ({ name, voice_id: (v as Record<string, string>).voice_id || "" }))
      : [{ name: "narrator", voice_id: "" }],
  );
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    const map: Record<string, { voice_id: string }> = {};
    rows.forEach((r) => { if (r.name.trim()) map[r.name.trim()] = { voice_id: r.voice_id.trim() }; });
    try {
      const res = await fetch(`${pipe}/pipeline/${runId}/voices`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ casting: map }),
      });
      const d = await res.json();
      if (d.run_id) onSaved(d as CutData);
    } catch {}
    finally { setBusy(false); }
  }

  return (
    <div className="mt-3 pt-3 border-t border-edge">
      <div className="text-[12px] text-dim uppercase tracking-wide mb-1.5">
        Voice casting (ElevenLabs voice_id per character)
      </div>
      {rows.map((r, i) => (
        <div key={i} className="flex gap-2 mb-1">
          <input
            value={r.name}
            onChange={(e) => setRows((p) => p.map((x, j) => j === i ? { ...x, name: e.target.value } : x))}
            placeholder="character (e.g. narrator)"
            className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 w-40"
          />
          <input
            value={r.voice_id}
            onChange={(e) => setRows((p) => p.map((x, j) => j === i ? { ...x, voice_id: e.target.value } : x))}
            placeholder="voice_id"
            className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 flex-1 font-mono"
          />
        </div>
      ))}
      <div className="flex gap-2 mt-1">
        <button
          onClick={() => setRows((p) => [...p, { name: "", voice_id: "" }])}
          className="text-accent border border-accent/40 rounded px-2 py-0.5 text-[12px]"
          style={{ background: "rgba(91,157,255,0.12)" }}
        >
          + character
        </button>
        <button
          disabled={busy}
          onClick={save}
          className="text-good border border-good/40 rounded px-2 py-0.5 text-[12px] disabled:opacity-50"
          style={{ background: "rgba(87,201,122,0.12)" }}
        >
          {busy ? "saving…" : "Save casting"}
        </button>
      </div>
    </div>
  );
}

export default TimelinePanel;
