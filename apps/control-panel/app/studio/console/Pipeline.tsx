"use client";

import { useEffect, useState } from "react";
import ConsoleShell from "./ConsoleShell";
import AstriaRefine from "./AstriaRefine";
import StageChecklist from "./StageChecklist";

// 8-stage pipeline workspaces (full build — installment 3). Spin up a project from
// one director prompt, then fine-tune each stage with text/image ingestion and
// run / confirm / approve / re-enter controls. Talks to the Python pipeline service
// (studio_pipeline_service.py) — CORS-open to this origin.
const PIPE = process.env.NEXT_PUBLIC_PIPELINE_URL || "http://127.0.0.1:8800";

const STAGES = [
  "Brief", "Script", "Storyboard", "Asset Gen", "Review", "Assembly", "Rights/Release", "Delivery/Archive",
];
const mark: Record<string, string> = { approved: "✓", done: "•", running: "…", blocked: "⛔", pending: "▢" };
const tone: Record<string, string> = { approved: "#57c97a", done: "#97a1ad", running: "#f0a73d", blocked: "#ef6f6c", pending: "#97a1ad" };
const PROJECT_TYPES = ["SHORT", "AD", "PILOT", "FEATURE", "MUSIC_VIDEO", "TRAILER"];
const GENRE_PACKS = ["opera", "narrative", "comedy", "documentary", "music_video", "ad", "trailer"];

export default function Pipeline({ target }: { target?: { externalId: string | null; stage: number } | null }) {
  const [runs, setRuns] = useState<any[]>([]);
  const [runId, setRunId] = useState<string>("");
  const [st, setSt] = useState<any>(null);
  const [view, setView] = useState<number>(1);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("auto_draft");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [up, setUp] = useState(true);
  const [briefFiles, setBriefFiles] = useState<File[]>([]);
  const [conf, setConf] = useState<any>(null);
  // New film-project scaffold form
  const [npName, setNpName] = useState("");
  const [npType, setNpType] = useState("SHORT");
  const [npKernel, setNpKernel] = useState("");
  const [npPacks, setNpPacks] = useState<string[]>([]);

  async function listRuns() {
    try { const r = await fetch(`${PIPE}/pipeline`); const d = await r.json(); setRuns(d.runs || []); setUp(true); }
    catch { setUp(false); }
  }
  useEffect(() => { listRuns(); }, []);

  // Adopt an existing campaign (clicked from the top stage stepper) into a run so its
  // stage workspaces open, then jump to the requested stage.
  async function adopt(ext: string, stage: number) {
    setMsg(null);
    try {
      const r = await fetch(`${PIPE}/pipeline/adopt`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ externalId: ext }) });
      const d = await r.json();
      if (d.run_id) { setRunId(d.run_id); setSt(d.state); setView(stage || d.state?.stage || 1); setUp(true); listRuns(); }
      else setMsg({ ok: false, t: d.error || "could not open this project" });
    } catch { setUp(false); setMsg({ ok: false, t: `Pipeline service offline at ${PIPE} — start studio_pipeline_service.py.` }); }
  }
  useEffect(() => {
    if (!target) return;
    if (target.stage) setView(target.stage);                 // always select the stage, even if adoption is pending/fails
    if (target.externalId) adopt(target.externalId, target.stage);
  }, [target?.externalId, target?.stage]);

  // Persist the open project + active stage, and re-open the workspaces WITH the main layer
  // on remount (domain switch / reload / service restart). adopt() is idempotent, so this
  // rebuilds the run if the service was restarted.
  const SESSION_KEY = "ilyrium.pipeline.session";
  useEffect(() => {
    const ext = st?.campaign_id;
    if (ext) { try { localStorage.setItem(SESSION_KEY, JSON.stringify({ externalId: ext, view })); } catch {} }
  }, [st?.campaign_id, view]);
  useEffect(() => {
    if (target?.externalId || runId) return;                 // an explicit click or a live run wins
    try {
      const s = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
      if (s?.externalId) adopt(s.externalId, s.view || 1);
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function call(path: string, body?: any, method = "POST") {
    setBusy(path); setMsg(null);
    try {
      const r = await fetch(`${PIPE}${path}`, method === "GET" ? {} :
        { method, headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });
      const d = await r.json();
      if (!r.ok && d.error) { setMsg({ ok: false, t: d.error }); }
      if (d.state) { setSt(d.state); setView(d.state.stage || view); }
      if (d.run_id) { setRunId(d.run_id); listRuns(); }
      if (d.error && d.state) setMsg({ ok: false, t: d.error });
      return d;
    } catch (e: any) { setUp(false); setMsg({ ok: false, t: `Service unreachable at ${PIPE} — start studio_pipeline_service.py.` }); }
    finally { setBusy(""); }
  }

  // Read a File as text (docs) or base64 (images).
  const readText = (f: File) => new Promise<string>((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result)); fr.readAsText(f); });
  const readB64 = (f: File) => new Promise<string>((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1]); fr.readAsDataURL(f); });

  async function startProject() {
    if (!prompt.trim()) return;
    let fullPrompt = prompt.trim();
    const images: { name: string; b64: string }[] = [];
    for (const f of briefFiles) {
      if (f.type.startsWith("image/")) {
        images.push({ name: f.name, b64: await readB64(f) });
      } else {                                  // .md/.txt/.csv etc → appended to the brief
        const txt = await readText(f);
        fullPrompt += `\n\n--- attached: ${f.name} ---\n${txt}`;
      }
    }
    const d = await call("/pipeline/start", { prompt: fullPrompt, mode, images });
    if (d?.run_id) { setBriefFiles([]); }
  }
  const loadRun = async (id: string) => { setRunId(id); const d = await call(`/pipeline/${id}`, undefined, "GET"); };

  // Scaffold a NEW film project (governed tree) from the console. Defaults to a blank
  // per-project kernel named after the project — no New-Harnomy inheritance.
  async function createScaffold() {
    if (!npName.trim()) return;
    const d = await call("/projects/scaffold", {
      name: npName.trim(), type: npType, kernel: npKernel.trim(), genre_packs: npPacks,
    });
    if (d?.ok) {
      setMsg({ ok: true, t: `Scaffolded ${d.slug} (${d.type}${d.genre_packs?.length ? ", " + d.genre_packs.join("+") : ""}) — kernel '${d.kernel}'. Draft scenes in the Script stage, then it'll open here.` });
      setNpName(""); setNpKernel(""); setNpPacks([]); listRuns();
    }
  }
  const togglePack = (p: string) => setNpPacks((cur) => cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]);

  // Live progress: while a run is executing in the background, poll its status so the
  // stage rail + workspace reflect each stage completing without the user reloading.
  useEffect(() => {
    if (!runId || !(st?.status === "running" || st?.status === "ready")) return;
    const id = setInterval(async () => {
      try {
        const r = await fetch(`${PIPE}/pipeline/${runId}`);
        const d = await r.json();
        if (d.state) { setSt(d.state); setView((v) => d.state.stage || v); }
        if (d.state && d.state.status !== "running") listRuns();
      } catch { /* keep polling; transient */ }
    }, 3000);
    return () => clearInterval(id);
  }, [runId, st?.status]);

  // Phase 5 — surface the split: pull the mechanical verdict (guaranteed green) + the
  // human judgment checklist whenever the run advances.
  useEffect(() => {
    if (!runId) { setConf(null); return; }
    let alive = true;
    fetch(`${PIPE}/pipeline/${runId}/conformance`)
      .then((r) => r.json()).then((d) => { if (alive) setConf(d); }).catch(() => {});
    return () => { alive = false; };
  }, [runId, st?.stage, st?.status]);

  async function addNote(stage: number, file?: File | null) {
    const body: any = { stage, note, by: "brad" };
    if (file) {
      const b64: string = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1]); fr.readAsDataURL(file); });
      body.image_b64 = b64; body.image_name = file.name;
    }
    await call(`/pipeline/${runId}/note`, body); setNote("");
  }

  const gstatus = st?.status, gstage = st?.stage;
  const curStage = st?.stages?.[String(view)] || {};
  const stageDef = (n: number) => ({ costly: n === 4 || n === 6, gate: n === 7 });

  return (
    <div>
      {/* New project + run picker */}
      <section className="bg-panel border border-edge rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[16px] font-semibold">＋ New project from a director prompt</h3>
          {!up && <span className="text-[13px]" style={{ color: "#ef6f6c" }}>pipeline service offline ({PIPE})</span>}
        </div>
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={2}
          placeholder="e.g., a punchy 15s Instagram ad for a Ft. Pierce taco bar"
          className="w-full bg-ink border border-edge rounded-md text-fg text-[15px] p-2.5 mb-2" />
        <div className="flex items-center gap-2 flex-wrap">
          <select value={mode} onChange={(e) => setMode(e.target.value)} className="bg-ink border border-edge rounded-md text-fg text-[14px] px-2 py-1.5">
            <option value="auto_draft">auto_draft — run to a first cut, pause at the gate</option>
            <option value="assisted">assisted — confirm before costly stages</option>
            <option value="manual">manual — approve every stage</option>
          </select>
          <label className="text-dim border border-edge rounded-md px-2.5 py-1.5 text-[13px] cursor-pointer hover:bg-raised/50">
            ＋ attach docs / images
            <input type="file" multiple accept=".md,.txt,.csv,.json,image/*" className="hidden"
              onChange={(e) => setBriefFiles(Array.from(e.target.files || []))} />
          </label>
          <button disabled={!!busy} onClick={startProject} className="text-accent border border-accent/40 rounded-md px-3 py-1.5 text-[14px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>
            {busy === "/pipeline/start" ? "spinning up…" : "Spin up project"}
          </button>
          {runs.length > 0 && (
            <select value={runId} onChange={(e) => loadRun(e.target.value)} className="bg-ink border border-edge rounded-md text-fg text-[14px] px-2 py-1.5 ml-auto font-mono">
              <option value="">— load run —</option>
              {runs.map((r) => <option key={r.run_id} value={r.run_id}>{r.campaign_id || r.run_id} · {r.status} @{r.stage}</option>)}
            </select>
          )}
        </div>
        {briefFiles.length > 0 && (
          <div className="text-[12px] text-dim mt-2 flex flex-wrap gap-1.5">
            {briefFiles.map((f, i) => (
              <span key={i} className="bg-ink border border-edge rounded px-1.5 py-0.5 font-mono">
                {f.type.startsWith("image/") ? "🖼" : "📄"} {f.name}
              </span>
            ))}
          </div>
        )}
        {(st?.status === "running" || st?.status === "ready") && (
          <div className="mt-2">
            <div className="text-[13px] flex items-center gap-2" style={{ color: "#f0a73d" }}>
              <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: "#f0a73d" }} />
              running stage {st.stage} — {STAGES[st.stage - 1]}
              {st?.heartbeat?.total ? <span className="font-mono"> · {st.heartbeat.done}/{st.heartbeat.total}</span> : null}
            </div>
            {st?.heartbeat?.msg && (
              <div className="text-[12px] text-dim mt-1 font-mono pl-4">↳ {st.heartbeat.msg}</div>
            )}
            {Array.isArray(st?.log) && st.log.length > 0 && (
              <div className="text-[11px] text-dim mt-1 pl-4 max-h-24 overflow-auto font-mono leading-relaxed">
                {st.log.slice(-6).map((l: any, i: number) => (
                  <div key={i}>{l.t ? <span className="opacity-60">{l.t} </span> : null}{l.msg}</div>
                ))}
              </div>
            )}
          </div>
        )}
        {msg && <div className="text-[13px] mt-2" style={{ color: msg.ok ? "#57c97a" : "#ef6f6c" }}>{msg.t}</div>}
      </section>

      {/* New film project — scaffold the governed tree (name / type / genre packs / kernel) */}
      <section className="bg-panel border border-edge rounded-xl p-4 mb-4">
        <h3 className="text-[16px] font-semibold mb-2">＋ New film project (scaffold)</h3>
        <div className="flex items-center gap-2 flex-wrap">
          <input value={npName} onChange={(e) => setNpName(e.target.value)} placeholder="Project name (e.g. Satesh)"
            className="bg-ink border border-edge rounded-md text-fg text-[14px] px-2.5 py-1.5 min-w-[200px]" />
          <select value={npType} onChange={(e) => setNpType(e.target.value)} className="bg-ink border border-edge rounded-md text-fg text-[14px] px-2 py-1.5">
            {PROJECT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={npKernel} onChange={(e) => setNpKernel(e.target.value)} placeholder="kernel (blank = new, named after project)"
            className="bg-ink border border-edge rounded-md text-fg text-[14px] px-2.5 py-1.5 min-w-[240px]" />
          <button disabled={!!busy || !npName.trim()} onClick={createScaffold}
            className="text-accent border border-accent/40 rounded-md px-3 py-1.5 text-[14px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>
            {busy === "/projects/scaffold" ? "scaffolding…" : "Create project"}
          </button>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 items-center">
          <span className="text-[12px] text-dim uppercase tracking-wide">genre packs</span>
          {GENRE_PACKS.map((p) => (
            <label key={p} className="text-[13px] text-dim flex items-center gap-1 cursor-pointer">
              <input type="checkbox" checked={npPacks.includes(p)} onChange={() => togglePack(p)} /> {p}
            </label>
          ))}
        </div>
        <div className="text-[12px] text-dim mt-1.5">Builds the governed project tree — 8 stages, style kernel, casting-canon folders (loras/&lt;char&gt;/source·refs·lora), QA checklist, scenes starter. Draft scenes in the Script stage, then it opens here.</div>
      </section>

      {/* Phase 5 — surface the split: mechanical (deterministic, guaranteed) vs judgment (stochastic, yours) */}
      {st && conf && (
        <section className="bg-panel border border-edge rounded-xl p-4 mb-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-[12px] text-dim uppercase tracking-wide mb-1.5">Mechanical layer · deterministic</div>
            {conf?.mechanical?.ok ? (
              <div className="text-[14px] flex items-center gap-2" style={{ color: "#57c97a" }}>
                <span>✓</span> conformant by construction — format is settled
              </div>
            ) : (
              <div className="text-[13px]" style={{ color: "#ef6f6c" }}>
                {conf?.mechanical?.violations} violation(s):
                <span className="font-mono"> {Object.entries(conf?.mechanical?.by_category || {}).map(([k, v]) => `${k}×${v}`).join("  ")}</span>
              </div>
            )}
            {conf?.throughput && (
              <div className="text-[12px] text-dim mt-2 font-mono">
                throughput: {conf.throughput.units_per_min}/min · {conf.throughput.workers}w · first-pass {conf.throughput.first_pass_rate ?? "—"}
              </div>
            )}
          </div>
          <div>
            <div className="text-[12px] text-dim uppercase tracking-wide mb-1.5">Judgment layer · yours to decide</div>
            <ul className="text-[13px] space-y-1">
              {(conf?.judgment || []).map((j: any) => (
                <li key={j.key} className="flex items-start gap-2 text-fg">
                  <span style={{ color: "#b98cff" }}>◇</span><span>{j.label}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {!st ? (
        <div className="bg-panel border border-edge rounded-xl p-4 text-[15px]">
          {target?.externalId ? (
            <div>
              <div className="text-fg mb-1">Opening <span className="font-mono">{target.externalId}</span>{target.stage ? ` · stage ${target.stage} (${STAGES[target.stage - 1]})` : ""}…</div>
              <div className="text-dim text-[13px]">
                {up
                  ? "This stage's workspace needs a live run. If it doesn't open, the project may have no scenes yet — draft them in stage 2 (Script) or spin one up above."
                  : `Pipeline service offline at ${PIPE}. Start studio_pipeline_service.py, then click the stage again.`}
              </div>
            </div>
          ) : (
            <span className="text-dim">Spin up a project, or load an existing run, to open its 8 stage workspaces.</span>
          )}
        </div>
      ) : (
        <ConsoleShell layout="split" panels={{ browser: { bare: true, node: (
          /* Stage rail */
          <nav className="bg-panel border border-edge rounded-xl p-2 h-fit">
            {STAGES.map((name, i) => {
              const n = i + 1; const s = st.stages?.[String(n)] || {}; const active = view === n;
              return (
                <button key={n} onClick={() => setView(n)}
                  className={"w-full flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-[14px] " + (active ? "bg-raised border border-edge" : "border border-transparent hover:bg-raised/50")}>
                  <span style={{ color: tone[s.status] || "#97a1ad" }}>{mark[s.status] || "▢"}</span>
                  <span className="font-mono">{n} {name}</span>
                  {gstage === n && <span className="ml-auto text-[11px]" style={{ color: "#f0a73d" }}>●</span>}
                </button>
              );
            })}
          </nav>
        ) }, main: { bare: true, node: (
          /* Stage workspace */
          <section className="bg-panel border border-edge rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[17px] font-semibold">{view}. {STAGES[view - 1]}</h3>
              <span className="text-[13px] font-mono" style={{ color: tone[curStage.status] || "#97a1ad" }}>
                {curStage.status || "pending"}{gstage === view ? " · current" : ""}
              </span>
            </div>

            {curStage.result && <div className="bg-ink border border-edge rounded-md p-2.5 mb-3 text-[14px] text-fg/90">{String(curStage.result)}</div>}

            {/* All 8 stage workspaces open WITH the run and stay MOUNTED (persistent sub-layers):
                only the active stage is visible, the rest are hidden but keep their loaded data
                and edits, so switching stages is instant and never resets state. */}
            {runId && (
              <>
                <div className={view === 1 ? "" : "hidden"}>
                  {st?.campaign_id && <StageChecklist pipe={PIPE} project={st.campaign_id} initialStage={1} />}
                  <BriefPanel pipe={PIPE} runId={runId} />
                </div>
                <div className={view === 2 ? "" : "hidden"}><ScriptPanel pipe={PIPE} runId={runId} /></div>
                <div className={view === 3 ? "" : "hidden"}><StoryboardPanel pipe={PIPE} runId={runId} /></div>
                <div className={(view === 4 || view === 5) ? "" : "hidden"}><AssetGenPanel pipe={PIPE} runId={runId} /></div>
                <div className={view === 6 ? "" : "hidden"}><AudioTimelinePanel pipe={PIPE} runId={runId} /></div>
                <div className={view === 7 ? "" : "hidden"}><RightsPanel state={st} pipe={PIPE} runId={runId} /></div>
                <div className={view === 8 ? "" : "hidden"}><DeliveryPanel pipe={PIPE} runId={runId} externalId={st?.campaign_id} /></div>
              </>
            )}

            {/* Per-stage ingestion (text + image) */}
            <div className="mb-3">
              <div className="text-[12px] text-dim uppercase tracking-wide mb-1">Ingest / fine-tune this stage</div>
              <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
                placeholder="note, direction, or reference description…" className="w-full bg-ink border border-edge rounded-md text-fg text-[14px] p-2 mb-2" />
              <div className="flex items-center gap-2">
                <label className="text-accent border border-accent/40 rounded-md px-2.5 py-1 text-[13px] cursor-pointer" style={{ background: "rgba(91,157,255,0.12)" }}>
                  📎 image
                  <input type="file" accept="image/*" className="hidden" onChange={(e) => addNote(view, e.target.files?.[0])} />
                </label>
                <button disabled={!!busy || !note.trim()} onClick={() => addNote(view)} className="border border-edge text-fg rounded-md px-3 py-1 text-[13px] disabled:opacity-40">Add note</button>
              </div>
              {(curStage.notes || []).length > 0 && (
                <ul className="mt-2 text-[13px] text-dim space-y-1">
                  {curStage.notes.map((nt: any, i: number) => <li key={i} className="font-mono">• {nt.note}</li>)}
                </ul>
              )}
            </div>

            {/* Stage actions */}
            <div className="flex flex-wrap gap-2 pt-3 border-t border-edge">
              {gstatus === "awaiting_approval" && stageDef(gstage).costly && !st.stages?.[String(gstage)]?.confirmed && st.stages?.[String(gstage)]?.status !== "done" ? (
                <button disabled={!!busy} onClick={() => call(`/pipeline/${runId}/confirm`)} className="text-amber border border-amber/40 rounded-md px-3 py-1.5 text-[14px]" style={{ background: "rgba(240,167,61,0.12)" }}>Confirm cost & run</button>
              ) : gstatus === "awaiting_approval" && gstage === 7 ? (
                <ApproveGate busy={!!busy} onApprove={(nl, ov, reason) => call(`/pipeline/${runId}/approve`, { reviewer: "brad", no_likeness_confirmed: nl, override: ov, override_reason: reason })} />
              ) : gstatus === "awaiting_approval" ? (
                <button disabled={!!busy} onClick={() => call(`/pipeline/${runId}/approve`, { reviewer: "brad" })} className="text-good border border-good/40 rounded-md px-3 py-1.5 text-[14px]" style={{ background: "rgba(87,201,122,0.12)" }}>Approve & advance</button>
              ) : gstatus === "complete" ? (
                <span className="text-good text-[14px]">✓ pipeline complete</span>
              ) : (
                <button disabled={!!busy} onClick={() => call(`/pipeline/${runId}/advance`)} className="text-accent border border-accent/40 rounded-md px-3 py-1.5 text-[14px]" style={{ background: "rgba(91,157,255,0.12)" }}>{busy ? "running…" : "Advance"}</button>
              )}
              <button disabled={!!busy} onClick={() => call(`/pipeline/${runId}/reenter`, { stage: view })} className="border border-edge text-dim rounded-md px-3 py-1.5 text-[14px]">Re-enter stage {view}</button>
            </div>
          </section>
        ) } }} />
      )}
    </div>
  );
}

// Stage 4 — Asset Generation: per-shot take grid with generate / Aleph-edit / select.
const CAMERAS = ["", "locked / static", "slow push in", "pull back", "pan left", "pan right",
  "orbit left", "orbit right", "tilt up", "handheld"];
const ENGINES = ["grok-imagine", "veo3.1", "kling", "runway", "runway:veo3.1", "comfyui"];

function AssetGenPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [shots, setShots] = useState<any[]>([]);
  const [busy, setBusy] = useState<string>("");
  const [dir, setDir] = useState<Record<number, { engine: string; camera: string; lighting: string; motion: string; prompt: string }>>({});
  const [recos, setRecos] = useState<any[]>([]);   // kernel-ranked models for this project

  async function load() {
    try { const r = await fetch(`${pipe}/pipeline/${runId}/shots`); const d = await r.json(); setShots(d.shots || []); } catch {}
  }
  useEffect(() => { load(); }, [runId]);
  // Pre-rank the model dropdown against the project kernel (recommend_models).
  useEffect(() => {
    fetch(`${pipe}/pipeline/${runId}/models?need=i2v`).then((r) => r.json())
      .then((d) => setRecos(d.models || [])).catch(() => setRecos([]));
  }, [runId]);

  const topModel = recos.find((m) => m.available)?.id || "runway";
  const recoFor = (id: string) => recos.find((m) => m.id === id);
  const d = (n: number) => dir[n] || { engine: topModel, camera: "", lighting: "", motion: "", prompt: "" };
  const setD = (n: number, patch: any) => setDir((p) => ({ ...p, [n]: { ...d(n), ...patch } }));
  const instruction = (n: number) => [d(n).camera, d(n).lighting && `lighting: ${d(n).lighting}`, d(n).motion && `motion: ${d(n).motion}`].filter(Boolean).join(", ");

  async function act(n: number, op: string, extra: any) {
    setBusy(`${n}:${op}`);
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/shot/${n}/action`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ op, ...extra }) });
      const j = await r.json(); if (j.shots) setShots(j.shots);
    } catch {} finally { setBusy(""); }
  }
  const mediaSrc = (t: any) => t?.public_url || (t?.file ? `${pipe}/media/${runId}/${t.file}` : "");

  const [qc, setQc] = useState<any>(null);
  async function runQc() {
    setBusy("qc");
    try { const r = await fetch(`${pipe}/pipeline/${runId}/qc`, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }); setQc(await r.json()); } catch {} finally { setBusy(""); }
  }

  if (shots.length === 0) return <div className="text-dim text-[14px] mb-3">No shots yet — run Script + Storyboard, or generate the first cut.</div>;

  return (
    <div className="space-y-4 mb-4">
      <div className="flex items-center gap-3">
        <button disabled={!!busy} onClick={runQc} className="border border-edge text-fg rounded-md px-2.5 py-1 text-[12px] disabled:opacity-50">{busy === "qc" ? "scanning…" : "Run frame QC"}</button>
        {qc && (qc.flagged?.length
          ? <span className="text-[12px]" style={{ color: "#ef6f6c" }}>flagged scenes: {qc.flagged.join(", ")}</span>
          : <span className="text-[12px]" style={{ color: "#57c97a" }}>QC clean — no black/freeze/silence</span>)}
      </div>
      {shots.map((s) => {
        const sel = (s.takes || []).find((t: any) => t.take_id === s.selected_take) || (s.takes || []).slice(-1)[0];
        return (
          <div key={s.scene_number} className="bg-ink border border-edge rounded-lg p-3">
            <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-3">
              <div>
                <div className="aspect-video bg-black rounded-md overflow-hidden flex items-center justify-center text-dim text-[12px]">
                  {sel && sel.ok ? (sel.image ? <img src={mediaSrc(sel)} alt={`scene ${s.scene_number} take`} className="w-full h-full object-contain" /> : <video src={mediaSrc(sel)} controls className="w-full h-full object-contain" />) : "no take yet"}
                </div>
                {/* take chips */}
                <div className="flex flex-wrap gap-1 mt-2">
                  {(s.takes || []).map((t: any) => (
                    <button key={t.take_id} onClick={() => act(s.scene_number, "select", { take_id: t.take_id })}
                      className={"text-[11px] font-mono px-1.5 py-0.5 rounded border " + (t.take_id === s.selected_take ? "border-good text-good" : "border-edge text-dim")}>
                      {t.take_id}·{t.model}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[12px] text-dim font-mono mb-1">SCENE {s.scene_number}</div>
                <textarea value={d(s.scene_number).prompt || s.visual_prompt} onChange={(e) => setD(s.scene_number, { prompt: e.target.value })}
                  rows={2} className="w-full bg-panel border border-edge rounded-md text-fg text-[13px] p-2 mb-2" />
                <div className="flex flex-wrap gap-2 items-center mb-2">
                  <select value={d(s.scene_number).engine} onChange={(e) => setD(s.scene_number, { engine: e.target.value })} className="bg-panel border border-edge rounded-md text-fg text-[12px] px-1.5 py-1" title="ranked for this project's kernel">
                    {recos.length > 0
                      ? recos.map((m) => <option key={m.id} value={m.id} disabled={!m.available}>{m.available ? "" : "⚠ "}{m.name} · {m.score}{m.available ? "" : " (set creds)"}</option>)
                      : ENGINES.map((e) => <option key={e} value={e}>{e}</option>)}
                  </select>
                  <select value={d(s.scene_number).camera} onChange={(e) => setD(s.scene_number, { camera: e.target.value })} className="bg-panel border border-edge rounded-md text-fg text-[12px] px-1.5 py-1">
                    {CAMERAS.map((c) => <option key={c} value={c}>{c || "camera…"}</option>)}
                  </select>
                  <input value={d(s.scene_number).lighting} onChange={(e) => setD(s.scene_number, { lighting: e.target.value })} placeholder="lighting" className="bg-panel border border-edge rounded-md text-fg text-[12px] px-2 py-1 w-28" />
                  <input value={d(s.scene_number).motion} onChange={(e) => setD(s.scene_number, { motion: e.target.value })} placeholder="motion / blocking" className="bg-panel border border-edge rounded-md text-fg text-[12px] px-2 py-1 w-36" />
                </div>
                {recoFor(d(s.scene_number).engine)?.why && (
                  <div className="text-[11px] text-dim mb-2">↳ {recoFor(d(s.scene_number).engine).why}</div>
                )}
                <div className="flex flex-wrap gap-2">
                  <button disabled={!!busy} onClick={() => act(s.scene_number, "regenerate", { model: d(s.scene_number).engine, prompt: [d(s.scene_number).prompt || s.visual_prompt, instruction(s.scene_number)].filter(Boolean).join(". ") })}
                    className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>
                    {busy === `${s.scene_number}:regenerate` ? "generating…" : "Generate / Regenerate"}
                  </button>
                  <button disabled={!!busy || !instruction(s.scene_number) || !sel?.ok} onClick={() => act(s.scene_number, "edit", { edit_prompt: instruction(s.scene_number) })}
                    title="Edit the selected take with Runway Gen-4 Aleph (relight / camera / object)"
                    className="text-mauve border border-mauve/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-40" style={{ background: "rgba(185,140,255,0.12)" }}>
                    {busy === `${s.scene_number}:edit` ? "editing…" : "✂ Edit take (Aleph)"}
                  </button>
                </div>
                <div className="text-[11px] text-dim mt-1">Edit applies camera/lighting/motion to the current take via Aleph (non-destructive). Generate makes a new take with the chosen engine.</div>
                <AstriaRefine pipe={pipe} runId={runId} scene={s.scene_number} basePrompt={d(s.scene_number).prompt || s.visual_prompt} onResult={setShots} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Stage 1 — Brief.
const BRIEF_FIELDS = ["audience", "key_message", "vibe", "cta", "format", "duration"];
function BriefPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [prompt, setPrompt] = useState("");
  const [f, setF] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  async function load() {
    try { const r = await fetch(`${pipe}/pipeline/${runId}`); const d = await r.json(); setPrompt(d.state?.prompt || ""); setF(d.state?.brief_fields || {}); } catch {}
  }
  useEffect(() => { load(); }, [runId]);
  async function save() {
    setBusy(true); setMsg("");
    try { const r = await fetch(`${pipe}/pipeline/${runId}/brief`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ prompt, fields: f }) }); const d = await r.json(); setMsg(d.state ? "saved" : (d.error || "failed")); } catch { setMsg("unreachable"); } finally { setBusy(false); }
  }
  return (
    <div className="mb-4 max-w-2xl">
      <div className="text-[12px] text-dim uppercase tracking-wide mb-1">Director prompt</div>
      <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={2} className="w-full bg-ink border border-edge rounded-md text-fg text-[14px] p-2 mb-3" />
      <div className="grid grid-cols-2 gap-2 mb-3">
        {BRIEF_FIELDS.map((k) => (
          <label key={k} className="text-[13px]">
            <span className="text-dim text-[12px] block mb-0.5">{k.replace("_", " ")}</span>
            <input value={f[k] || ""} onChange={(e) => setF((p) => ({ ...p, [k]: e.target.value }))} className="w-full bg-ink border border-edge rounded-md text-fg text-[13px] px-2 py-1" />
          </label>
        ))}
      </div>
      <button disabled={busy} onClick={save} className="text-good border border-good/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(87,201,122,0.12)" }}>{busy ? "saving…" : "Save brief"}</button>
      {msg && <span className="text-[12px] text-dim ml-2">{msg}</span>}
    </div>
  );
}

// Stage 7 — Rights / Release summary + Style-Bible eval (the gate action is the ApproveGate).
function RightsPanel({ state, pipe, runId }: { state: any; pipe: string; runId: string }) {
  const blockers: string[] = state?.last_blockers || [];
  const [evalRep, setEvalRep] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  async function runEval() {
    setBusy(true);
    try { const r = await fetch(`${pipe}/pipeline/${runId}/eval`, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }); const d = await r.json(); setEvalRep(d.report || { error: d.error }); } catch { setEvalRep({ error: "service unreachable" }); } finally { setBusy(false); }
  }
  return (
    <div className="mb-4 bg-ink border border-edge rounded-lg p-3 max-w-2xl">
      <div className="text-[14px] font-semibold mb-2">Rights · Release readiness</div>
      <div className="text-[13px] text-dim mb-2">{state?.qa_summary || "QA runs when the cut reaches this stage."}</div>
      {blockers.length > 0 ? (
        <ul className="text-[13px] space-y-1" style={{ color: "#e0a13a" }}>{blockers.map((b, i) => <li key={i}>• {b}</li>)}</ul>
      ) : <div className="text-[13px]" style={{ color: "#57c97a" }}>No outstanding blockers recorded.</div>}

      <div className="mt-3 pt-3 border-t border-edge">
        <button disabled={busy} onClick={runEval} className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>
          {busy ? "scoring…" : "Run Style-Bible eval"}
        </button>
        {evalRep && !evalRep.error && (
          <div className="mt-2 text-[13px]">
            <div>overall <b style={{ color: evalRep.passed ? "#57c97a" : "#e0a13a" }}>{evalRep.overall_score}</b> / threshold {evalRep.threshold} · {evalRep.n_shots} shots {evalRep.hard_fail && <span style={{ color: "#ef6f6c" }}>· HARD FAIL</span>}</div>
            <table className="mt-1 text-[12px]"><tbody>
              {Object.entries(evalRep.per_dimension || {}).map(([dim, v]: any) => (
                <tr key={dim}><td className="pr-3 font-mono text-dim">{dim}</td><td className="pr-3">avg {v.avg}</td><td style={{ color: v.fails ? "#ef6f6c" : "#97a1ad" }}>{v.fails} fail · {v.warns} warn</td></tr>
              ))}
            </tbody></table>
          </div>
        )}
        {evalRep?.error && <div className="text-[12px] mt-1" style={{ color: "#ef6f6c" }}>{evalRep.error}</div>}
      </div>
      <div className="text-[12px] text-dim mt-2">Use Approve &amp; release below (confirm no-likeness). Eval results are recorded as a Run; the rights ledger + risk queue live in the Studio Control Plane.</div>
    </div>
  );
}

// Stage 8 — Delivery / Archive.
function DeliveryPanel({ pipe, runId, externalId }: { pipe: string; runId: string; externalId?: string }) {
  const [c, setC] = useState<any>(null);
  const [arch, setArch] = useState<string>("");
  const [busy, setBusy] = useState("");
  async function load() { try { const r = await fetch(`${pipe}/pipeline/${runId}/cut`); setC(await r.json()); } catch {} }
  useEffect(() => { load(); }, [runId]);
  async function buildArchive() {
    if (!externalId) { setArch("no project yet"); return; }
    setBusy("archive"); setArch("");
    try { const r = await fetch(`/api/studio/archive`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ externalId }) }); const d = await r.json(); setArch(d.ok ? `Archive ${Math.round(d.completenessScore * 100)}% · ${d.status}${d.missing?.length ? " · missing: " + d.missing.join(", ") : ""}` : (d.error || "failed")); } catch { setArch("control-panel route unreachable"); } finally { setBusy(""); }
  }
  const [deliverMsg, setDeliverMsg] = useState("");
  async function deliver(op: string, extra: any = {}) {
    setBusy(op); setDeliverMsg("");
    try { const r = await fetch(`${pipe}/pipeline/${runId}/deliver`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ op, ...extra }) }); const d = await r.json(); setDeliverMsg(d.ok ? (d.captions ? `captions: ${d.captions.cues} cues (${d.captions.srt})` : `→ ${d.file}`) : (d.error || "failed")); }
    catch { setDeliverMsg("service unreachable"); } finally { setBusy(""); }
  }
  const src = c?.cut?.public_url || (c?.cut?.file ? `${pipe}/media/${runId}/${c.cut.file}` : "");
  const published = c?.cut?.release?.published;
  return (
    <div className="mb-4">
      <div className="aspect-video bg-black rounded-md overflow-hidden flex items-center justify-center text-dim text-[13px] mb-3 max-w-2xl">
        {src ? <video src={src} controls className="w-full h-full object-contain" /> : "no master yet — assemble + approve first"}
      </div>
      <div className="flex flex-wrap items-center gap-3 mb-2">
        <span className="text-[13px]" style={{ color: published ? "#57c97a" : "#97a1ad" }}>{published ? "✓ published to R2 (C2PA attached)" : "not yet published — approve at the rights gate"}</span>
        <button disabled={!!busy} onClick={buildArchive} className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>{busy === "archive" ? "checking…" : "Build / check archive"}</button>
        {arch && <span className="text-[12px] text-dim">{arch}</span>}
      </div>
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-edge">
        <span className="text-[12px] text-dim uppercase tracking-wide mr-1">deliver</span>
        <button disabled={!!busy} onClick={() => deliver("captions")} className="border border-edge text-fg rounded-md px-2.5 py-1 text-[12px] disabled:opacity-50">Captions (SRT/VTT)</button>
        {["9:16", "1:1", "16:9"].map((t) => (
          <button key={t} disabled={!!busy} onClick={() => deliver("preset", { target: t })} className="border border-edge text-fg rounded-md px-2.5 py-1 text-[12px] disabled:opacity-50">{busy === "preset" ? "…" : `Export ${t}`}</button>
        ))}
        {[15, 6].map((s) => (
          <button key={s} disabled={!!busy} onClick={() => deliver("cutdown", { seconds: s })} className="border border-edge text-fg rounded-md px-2.5 py-1 text-[12px] disabled:opacity-50">Cutdown {s}s</button>
        ))}
        <button disabled={!!busy} onClick={() => deliver("ai_cutdown", { seconds: 15 })} className="text-mauve border border-mauve/40 rounded-md px-2.5 py-1 text-[12px] disabled:opacity-50" style={{ background: "rgba(185,140,255,0.12)" }} title="LLM picks the best scenes/order for a 15s cutdown, assembled from existing takes">{busy === "ai_cutdown" ? "editing…" : "AI cutdown 15s"}</button>
        {deliverMsg && <span className="text-[12px] text-dim">{deliverMsg}</span>}
      </div>
      <div className="text-[12px] text-dim mt-2">Captions are timed from the script's voiceover lines; presets letterbox + loudness-normalize the master; cutdowns trim the first N seconds. (Voice-casting + AI cutdowns next.)</div>
    </div>
  );
}

// Stage 2 — Script + Style Kernel editor.
function ScriptPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [scenes, setScenes] = useState<any[]>([]);
  const [kernel, setKernel] = useState<any>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function load() {
    try { const r = await fetch(`${pipe}/pipeline/${runId}/script`); const d = await r.json(); setScenes(d.scenes || []); setKernel(d.kernel || {}); } catch {}
  }
  useEffect(() => { load(); }, [runId]);

  const edit = (i: number, f: string, v: string) => setScenes((p) => p.map((s, j) => j === i ? { ...s, [f]: v } : s));
  const add = () => setScenes((p) => [...p, { scene_number: (p.reduce((m, s) => Math.max(m, s.scene_number), 0) + 1), visual_prompt: "", voiceover: "" }]);
  const remove = (i: number) => setScenes((p) => p.filter((_, j) => j !== i));

  async function save() {
    setBusy(true); setMsg("");
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/script`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ scenes, kernel }) });
      const d = await r.json();
      if (d.scenes) { setScenes(d.scenes); setKernel(d.kernel || kernel); setMsg("saved"); }
      else if (Array.isArray(d.violations)) { setMsg("✗ conformance gate blocked this edit:\n• " + d.violations.join("\n• ")); }
      else setMsg(d.error || "save failed");
    } catch { setMsg("service unreachable"); } finally { setBusy(false); }
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4 mb-4">
      <div>
        {scenes.map((s, i) => (
          <div key={i} className="bg-ink border border-edge rounded-lg p-3 mb-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[12px] text-dim font-mono">SCENE {s.scene_number}</span>
              <button onClick={() => remove(i)} className="text-[12px] text-bad border border-edge rounded px-2 py-0.5">remove</button>
            </div>
            <textarea value={s.visual_prompt} onChange={(e) => edit(i, "visual_prompt", e.target.value)} rows={2} placeholder="visual prompt" className="w-full bg-panel border border-edge rounded-md text-fg text-[13px] p-2 mb-1" />
            <textarea value={s.voiceover} onChange={(e) => edit(i, "voiceover", e.target.value)} rows={1} placeholder="voiceover (spoken words only)" className="w-full bg-panel border border-edge rounded-md text-fg text-[13px] p-2" />
          </div>
        ))}
        <div className="flex gap-2">
          <button onClick={add} className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px]" style={{ background: "rgba(91,157,255,0.12)" }}>＋ scene</button>
          <button disabled={busy} onClick={save} className="text-good border border-good/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(87,201,122,0.12)" }}>{busy ? "saving…" : "Save script + kernel"}</button>
          {msg && <span className="text-[12px] text-dim self-center">{msg}</span>}
        </div>
      </div>
      <aside className="bg-ink border border-edge rounded-lg p-3 h-fit">
        <div className="text-[12px] text-dim uppercase tracking-wide mb-2">Style Kernel</div>
        {["look", "register", "negatives"].map((k) => (
          <div key={k} className="mb-2">
            <div className="text-[12px] text-dim mb-0.5">{k}</div>
            <textarea value={kernel[k] || ""} onChange={(e) => setKernel((p: any) => ({ ...p, [k]: e.target.value }))} rows={k === "look" ? 3 : 2} className="w-full bg-panel border border-edge rounded-md text-fg text-[12px] p-1.5" />
          </div>
        ))}
        <div className="text-[11px] text-dim">Look/register/negatives are injected into every render. Casting canon is edited in the kernel file.</div>
      </aside>
    </div>
  );
}

// Stage 3 — Storyboard / keyframe / anchor manager.
function StoryboardPanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [scenes, setScenes] = useState<any[]>([]);
  const [anchor, setAnchor] = useState<string | null>(null);
  const [busy, setBusy] = useState("");

  async function load() {
    try { const r = await fetch(`${pipe}/pipeline/${runId}/storyboard`); const d = await r.json(); setScenes(d.scenes || []); setAnchor(d.anchor_file || null); } catch {}
  }
  useEffect(() => { load(); }, [runId]);

  async function post(path: string, body: any, tag: string) {
    setBusy(tag);
    try { const r = await fetch(`${pipe}/pipeline/${runId}/${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }); const d = await r.json(); if (d.scenes) { setScenes(d.scenes); setAnchor(d.anchor_file || anchor); } }
    catch {} finally { setBusy(""); }
  }
  async function uploadAnchor(file?: File | null) {
    if (!file) return;
    const b64: string = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1]); fr.readAsDataURL(file); });
    post("anchor", { image_b64: b64, image_name: file.name }, "upload");
  }
  const src = (f: string) => `${pipe}/media/${runId}/${f}`;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="text-[12px] text-dim uppercase tracking-wide">Character anchor</div>
        {anchor ? <img src={src(anchor)} className="h-12 rounded border border-edge" /> : <span className="text-dim text-[12px]">none</span>}
        <label className="text-accent border border-accent/40 rounded-md px-2.5 py-1 text-[12px] cursor-pointer" style={{ background: "rgba(91,157,255,0.12)" }}>
          📎 upload anchor<input type="file" accept="image/*" className="hidden" onChange={(e) => uploadAnchor(e.target.files?.[0])} />
        </label>
        <span className="text-[11px] text-dim">Anchor locks faces across shots (--cref).</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
        {scenes.map((s) => (
          <div key={s.scene_number} className="bg-ink border border-edge rounded-lg overflow-hidden">
            <div className="aspect-video bg-black flex items-center justify-center text-dim text-[12px]">
              {s.keyframe_file ? <img src={src(s.keyframe_file)} className="w-full h-full object-contain" /> : "no keyframe"}
            </div>
            <div className="p-2.5">
              <div className="text-[11px] text-dim font-mono mb-1">SCENE {s.scene_number}</div>
              <p className="text-[12px] text-fg/90 line-clamp-2 mb-2" title={s.visual_prompt}>{s.visual_prompt}</p>
              <div className="flex gap-2">
                <button disabled={!!busy} onClick={() => post("keyframe", { scene_number: s.scene_number }, `kf${s.scene_number}`)} className="text-accent border border-accent/40 rounded px-2 py-0.5 text-[12px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>{busy === `kf${s.scene_number}` ? "…" : "Generate keyframe"}</button>
                {s.keyframe_file && <button disabled={!!busy} onClick={() => post("anchor", { scene_number: s.scene_number }, `an${s.scene_number}`)} className="text-mauve border border-mauve/40 rounded px-2 py-0.5 text-[12px]" style={{ background: "rgba(185,140,255,0.12)" }}>Use as anchor</button>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Stage 6 — Timeline / Audio Mix / Assembly: preview, multi-track view, duck, music, reassemble.
function AudioTimelinePanel({ pipe, runId }: { pipe: string; runId: string }) {
  const [c, setC] = useState<any>(null);
  const [duck, setDuck] = useState(0.35);
  const [music, setMusic] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    try { const r = await fetch(`${pipe}/pipeline/${runId}/cut`); const d = await r.json(); setC(d); if (typeof d.audio_duck === "number") setDuck(d.audio_duck); } catch {}
  }
  useEffect(() => { load(); }, [runId]);

  async function act(op: string, extra: any = {}) {
    setBusy(op);
    try { const r = await fetch(`${pipe}/pipeline/${runId}/audio`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ op, ...extra }) }); const d = await r.json(); if (d.run_id) { setC(d); if (typeof d.audio_duck === "number") setDuck(d.audio_duck); } }
    catch {} finally { setBusy(""); }
  }
  const cutSrc = c?.cut?.public_url || (c?.cut?.file ? `${pipe}/media/${runId}/${c.cut.file}` : "");
  const TRACKS = ["VIDEO", "VO", "MUSIC"];

  return (
    <div className="mb-4">
      <div className="aspect-video bg-black rounded-md overflow-hidden flex items-center justify-center text-dim text-[13px] mb-3">
        {cutSrc ? <video src={cutSrc} controls className="w-full h-full object-contain" /> : "no cut assembled yet — Reassemble below"}
      </div>

      {/* Multi-track timeline (visual) */}
      {(c?.shots || []).length > 0 && TRACKS.map((tr, ti) => (
        <div key={tr} className="flex items-center gap-2 mb-1.5">
          <span className="w-16 text-[11px] text-dim font-mono uppercase">{tr}</span>
          <div className="flex-1 flex gap-1">
            {c.shots.map((s: any) => (
              <div key={s.scene_number} className="h-7 flex-1 rounded-sm border border-edge flex items-center justify-center text-[10px] font-mono"
                style={{ background: ti === 0 ? "#1b2027" : ti === 1 ? "#171b21" : "#141820", color: (ti === 2 && !c.music) ? "#3a424d" : "#97a1ad" }}>
                {ti === 2 ? (c.music ? "♪" : "—") : s.scene_number}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-edge">
        <label className="flex items-center gap-2 text-[13px]">
          <span className="text-dim">VO duck</span>
          <input type="range" min={0} max={1} step={0.05} value={duck}
            onChange={(e) => setDuck(parseFloat(e.target.value))}
            onMouseUp={() => act("set_duck", { level: duck })} />
          <span className="font-mono w-10">{duck.toFixed(2)}</span>
        </label>
        <span className="flex items-center gap-2">
          <input value={music} onChange={(e) => setMusic(e.target.value)} placeholder="music bed: mood / genre / tempo"
            className="bg-ink border border-edge rounded-md text-fg text-[13px] px-2 py-1 w-56" />
          <button disabled={!!busy || !music.trim()} onClick={() => act("gen_music", { music_prompt: music.trim(), instrumental: true })}
            className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(91,157,255,0.12)" }}>
            {busy === "gen_music" ? "generating…" : "Generate music"}
          </button>
        </span>
        <button disabled={!!busy} onClick={() => act("reassemble")}
          className="text-good border border-good/40 rounded-md px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(87,201,122,0.12)" }}>
          {busy === "reassemble" ? "assembling…" : "Reassemble cut"}
        </button>
      </div>

      {/* Voice casting (per character ElevenLabs voice_id) */}
      <VoiceCasting pipe={pipe} runId={runId} casting={c?.voice_casting || {}} onSaved={(d) => setC(d)} />
      </div>
  );
}

function VoiceCasting({ pipe, runId, casting, onSaved }: { pipe: string; runId: string; casting: any; onSaved: (d: any) => void }) {
  const [rows, setRows] = useState<{ name: string; voice_id: string }[]>(
    Object.keys(casting).length ? Object.entries(casting).map(([name, v]: any) => ({ name, voice_id: v.voice_id || "" })) : [{ name: "narrator", voice_id: "" }]
  );
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    const map: any = {};
    rows.forEach((r) => { if (r.name.trim()) map[r.name.trim()] = { voice_id: r.voice_id.trim() }; });
    try { const res = await fetch(`${pipe}/pipeline/${runId}/voices`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ casting: map }) }); const d = await res.json(); if (d.run_id) onSaved(d); } catch {} finally { setBusy(false); }
  }
  return (
    <div className="mt-3 pt-3 border-t border-edge">
      <div className="text-[12px] text-dim uppercase tracking-wide mb-1.5">Voice casting (ElevenLabs voice_id per character)</div>
      {rows.map((r, i) => (
        <div key={i} className="flex gap-2 mb-1">
          <input value={r.name} onChange={(e) => setRows((p) => p.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} placeholder="character (e.g. narrator)" className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 w-40" />
          <input value={r.voice_id} onChange={(e) => setRows((p) => p.map((x, j) => j === i ? { ...x, voice_id: e.target.value } : x))} placeholder="voice_id" className="bg-ink border border-edge rounded-md text-fg text-[12px] px-2 py-1 flex-1 font-mono" />
        </div>
      ))}
      <div className="flex gap-2 mt-1">
        <button onClick={() => setRows((p) => [...p, { name: "", voice_id: "" }])} className="text-accent border border-accent/40 rounded px-2 py-0.5 text-[12px]" style={{ background: "rgba(91,157,255,0.12)" }}>＋ character</button>
        <button disabled={busy} onClick={save} className="text-good border border-good/40 rounded px-2 py-0.5 text-[12px] disabled:opacity-50" style={{ background: "rgba(87,201,122,0.12)" }}>{busy ? "saving…" : "Save casting"}</button>
      </div>
      <div className="text-[11px] text-dim mt-1">Set the VO duck and music bed, then Reassemble. Voice casting per character is next. Publishing happens at the Rights gate (stage 7) → Delivery (stage 8).</div>
    </div>
  );
}

function ApproveGate({ busy, onApprove }: { busy: boolean; onApprove: (nl: boolean, ov: boolean, reason: string) => void }) {
  const [nl, setNl] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex items-center gap-1.5 text-[14px]"><input type="checkbox" checked={nl} onChange={(e) => setNl(e.target.checked)} /> no real-person likeness confirmed</label>
      <button disabled={busy || !nl} onClick={() => onApprove(true, false, "")} className="text-good border border-good/40 rounded-md px-3 py-1.5 text-[14px] disabled:opacity-40" style={{ background: "rgba(87,201,122,0.12)" }}>Approve & release</button>
      <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="override reason" className="bg-ink border border-edge rounded-md text-fg text-[13px] px-2 py-1" />
      <button disabled={busy || !reason.trim()} onClick={() => onApprove(false, true, reason.trim())} className="text-mauve border border-mauve/40 rounded-md px-3 py-1.5 text-[13px]" style={{ background: "rgba(185,140,255,0.12)" }}>Override</button>
    </div>
  );
}
