"use client";

import { Fragment, useState } from "react";
import { useRouter } from "next/navigation";
import Pipeline from "./Pipeline";

/* Ilyrium Studio OS — workspace-driven film console. One project page; the left
   rail swaps the active functional domain (Scripting · Generation · Assembly ·
   Analytics), mirroring DaVinci/Blender "pages". Premium deep-matte look, traffic-
   light state colors, aspect-locked previews, persistent prompt metadata, visible
   diagnostics, and manual override affordances throughout.

   Phase 1 reconcile: projects are id/title-keyed (no externalId); assets are
   uri-addressed with a lowercase assetType + rating (no checksum/provenance/C2PA);
   rights are the risk-based model. */

type Risk = { score: number; tier: string; severity: string; factors: string[] };
type Shot = { shotNumber: number; prompt: string | null };
type Scene = { number: number; title: string | null; shots: Shot[] };
type Project = { id: string; title: string; type: string; status: string; greenlightLevel: string | null; counts: { scenes: number; shots: number; assets: number }; scenes: Scene[] };
type AssetRow = { id: string; assetType: string | null; uri: string; rating: string; projectId: string | null; projectTitle: string; model: string | null; sceneNumber: number | null; createdAt: string };
type QueueRow = { rightsId: string; assetId: string | null; assetUri: string | null; projectId: string | null; projectTitle: string; approvedForRelease: boolean; releaseStatus: string | null; riskLevel: string | null; risk: Risk };
type RunRow = { id: string; when: string; humanGateStatus: string | null; agentName: string | null; plane: string | null; costCents: number | null };
type Kpis = { totalAssets: number; masterCount: number; pendingCount: number; projects: number; estCostCents: number; runOk: number; runFail: number; renderRuns: number; costPerRenderSecCents: number };
type EngineMix = { model: string; count: number; cost: number }[];
type AssetMap = Record<string, { uri: string; assetType: string | null; model: string | null }>;

const SEV: Record<string, string> = { high: "#ef6f6c", medium: "#e0a13a", low: "#57c97a", override: "#b98cff" };
const short = (s?: string | null, n = 8) => (s ? s.slice(0, n) + "…" : "—");
const uriTail = (u?: string | null, n = 18) => (u ? (u.length > n ? "…" + u.slice(-n) : u) : "—");
const fmt = (iso: string) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
const pct = (n: number, d: number) => (d ? Math.round((100 * n) / d) : 0) + "%";

const ICONS: Record<string, React.ReactNode> = {
  script: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>,
  generation: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></svg>,
  assembly: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18M8 4v16M16 4v16" /></svg>,
  analytics: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M4 4v16h16" /><path d="M8 16v-4M12 16V8M16 16v-6" /></svg>,
  pipeline: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="5" cy="6" r="2" /><circle cx="5" cy="18" r="2" /><circle cx="19" cy="12" r="2" /><path d="M7 6h6a4 4 0 0 1 4 4M7 18h6a4 4 0 0 0 4-4" /></svg>,
};
const DOMAINS = [
  { key: "pipeline", label: "Pipeline", sub: "8-stage · auto-draft" },
  { key: "script", label: "Ideation & Scripting", sub: "Pre-Production" },
  { key: "generation", label: "Asset Generation", sub: "Production" },
  { key: "assembly", label: "Timeline & Assembly", sub: "Post" },
  { key: "analytics", label: "Studio Control Plane", sub: "Cost · Trace · Governance" },
];

// The 8 matrix stages as control points; ✓/▢ derived from project state.
const STAGE_DEFS = [
  { n: 1, name: "Brief" }, { n: 2, name: "Script" }, { n: 3, name: "Storyboard" },
  { n: 4, name: "Asset Gen" }, { n: 5, name: "Review" }, { n: 6, name: "Assembly" },
  { n: 7, name: "Rights/Release" }, { n: 8, name: "Delivery/Archive" },
];

function Chip({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="bg-raised border border-edge rounded-md px-3 py-1.5 min-w-[96px]">
      <div className="text-base font-bold font-mono" style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[12px] text-dim uppercase tracking-wide">{label}</div>
    </div>
  );
}

// Traffic-light state for a shot, derived from the asset graph.
function shotState(hasVideo: boolean, hasMaster: boolean) {
  if (hasVideo) return { label: hasMaster ? "IN CUT" : "DONE", color: "#57c97a", cls: "text-good" };
  return { label: "DRAFT", color: "#97a1ad", cls: "text-dim" };
}

export default function Workspace({ projects, assets, queue, runs, assetMap, kpis, engineMix }:
  { projects: Project[]; assets: AssetRow[]; queue: QueueRow[]; runs: RunRow[]; assetMap: AssetMap; kpis: Kpis; engineMix: EngineMix }) {
  const router = useRouter();
  const [domain, setDomain] = useState("pipeline");
  const [pipeTarget, setPipeTarget] = useState<{ externalId: string | null; stage: number } | null>(null);
  const [projId, setProjId] = useState<string>(projects[0]?.id ?? "all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [openApprove, setOpenApprove] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("brad");
  const [overrideReason, setOverrideReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ id: string; text: string; ok: boolean } | null>(null);

  const inProj = (id: string | null) => projId === "all" || id === projId;
  const proj = projects.find((p) => p.id === projId) || null;
  const projAssets = assets.filter((a) => inProj(a.projectId));
  const hasMaster = projAssets.some((a) => a.assetType === "master");
  const videoScenes = new Set(projAssets.filter((a) => a.assetType === "video" && a.sceneNumber != null).map((a) => a.sceneNumber));

  async function approve(item: QueueRow, mode: "clear" | "override") {
    if (!reviewer.trim()) return setMsg({ id: item.rightsId, text: "Reviewer required.", ok: false });
    if (mode === "override" && !overrideReason.trim()) return setMsg({ id: item.rightsId, text: "Override reason required.", ok: false });
    if (!item.projectId) return setMsg({ id: item.rightsId, text: "Master has no project id.", ok: false });
    setBusy(item.rightsId); setMsg(null);
    // Risk-based approve: clear the substantive risks to none/low so the gate can flip
    // approvedForRelease, or log an explicit override. uri pins the specific master.
    const body: any = { projectId: item.projectId, uri: item.assetUri ?? undefined, reviewerId: reviewer.trim() };
    if (mode === "override") { body.override = true; body.overrideReason = overrideReason.trim(); }
    else Object.assign(body, { likenessRisk: "none", musicRisk: "none", trademarkRisk: "none", riskLevel: "low" });
    try {
      const res = await fetch("/api/studio/approve", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      if (res.ok && data.ok) {
        setMsg({ id: item.rightsId, text: data.approvedForRelease ? "✅ Approved for release." : `Recorded; still blocked: ${(data.blockers || []).join("; ")}`, ok: !!data.approvedForRelease });
        setOpenApprove(null); setOverrideReason(""); router.refresh();
      } else setMsg({ id: item.rightsId, text: `Failed: ${data.error || res.status}`, ok: false });
    } catch (e: any) { setMsg({ id: item.rightsId, text: `Error: ${e?.message || e}`, ok: false }); }
    finally { setBusy(null); }
  }

  const projectOpts = projects;

  // Per-stage HITL control points for the selected project (✓ settled / ▢ open).
  const projQueue = queue.filter((q) => q.projectId === projId);
  const released = projQueue.some((q) => q.approvedForRelease);
  const stageState: Record<number, boolean> = !proj ? {} : {
    1: true,
    2: (proj.counts.scenes ?? 0) > 0,
    3: (proj.counts.shots ?? 0) > 0,
    4: projAssets.some((a) => a.assetType === "video"),
    5: projAssets.filter((a) => a.assetType === "video").length > 0, // takes exist to review
    6: hasMaster,
    7: released,
    8: released, // delivery/archive packaging is deferred in Phase 1 (release is the gate)
  };

  return (
    <div className="bg-ink text-fg min-h-screen flex font-sans text-[16px]">
      {/* LEFT RAIL — fixed domain nav (workspace pages) */}
      <nav className="w-[190px] shrink-0 border-r border-edge bg-panel p-3 flex flex-col gap-1">
        <div className="px-2 py-2 mb-2">
          <div className="text-fg font-bold tracking-tight">ILYRIUM</div>
          <div className="text-[12px] text-dim uppercase tracking-widest">Studio OS</div>
        </div>
        {DOMAINS.map((d) => {
          const active = domain === d.key;
          return (
            <button key={d.key} onClick={() => setDomain(d.key)}
              className={"flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors " +
                (active ? "bg-raised text-fg border border-edge" : "text-dim hover:text-fg hover:bg-raised/50 border border-transparent")}>
              <span style={{ color: active ? "#5b9dff" : undefined }}>{ICONS[d.key]}</span>
              <span className="leading-tight">
                <span className="block text-[16px] font-medium">{d.label}</span>
                <span className="block text-[12px] text-dim uppercase tracking-wide">{d.sub}</span>
              </span>
            </button>
          );
        })}
        <div className="mt-auto text-[12px] text-dim px-2 pt-3 border-t border-edge">
          Phase 1 · live from Neon
        </div>
      </nav>

      {/* RIGHT — topbar + active workspace */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="border-b border-edge bg-panel px-5 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <select value={projId} onChange={(e) => setProjId(e.target.value)}
              className="bg-raised border border-edge rounded-md text-fg text-sm px-2.5 py-1.5 font-mono">
              <option value="all">All projects ({projectOpts.length})</option>
              {projectOpts.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
            {proj && <span className="text-[13px] text-dim font-mono">{proj.type} · {proj.status} · {proj.greenlightLevel ?? "—"}</span>}
          </div>
          <div className="flex gap-2 flex-wrap">
            <Chip label="Assets" value={String(kpis.totalAssets)} />
            <Chip label="Masters" value={String(kpis.masterCount)} tone="#b98cff" />
            <Chip label="Pending" value={String(kpis.pendingCount)} tone={kpis.pendingCount ? "#e0a13a" : "#57c97a"} />
            <Chip label="Runs ok" value={pct(kpis.runOk, kpis.runOk + kpis.runFail)} tone={kpis.runFail ? "#e0a13a" : "#57c97a"} />
          </div>
        </header>

        <main className="flex-1 overflow-auto p-5">
          {/* DOMAIN 0 — PIPELINE (8 stage workspaces + auto-draft) */}
          {domain === "pipeline" && <Pipeline target={pipeTarget} />}

          {/* 8-stage control-point stepper (per-project HITL gates) */}
          {proj && domain !== "pipeline" && (
            <div className="flex items-stretch gap-2 mb-5">
              {STAGE_DEFS.map((s) => {
                const ok = stageState[s.n];
                return (
                  <button key={s.n} title={`Open the ${s.name} workspace`}
                    onClick={() => { setPipeTarget({ externalId: proj.title, stage: s.n }); setDomain("pipeline"); }}
                    className="flex-1 flex flex-col items-center justify-center gap-1 px-2 py-3 rounded-lg border text-center cursor-pointer hover:brightness-125 transition"
                    style={{ borderColor: ok ? "#57c97a55" : "#272d36", background: ok ? "rgba(87,201,122,0.08)" : "rgba(255,255,255,0.012)", color: ok ? "#57c97a" : "#97a1ad" }}>
                    <span className="text-[18px] font-semibold">{ok ? "✓" : "▢"} {s.n}</span>
                    <span className="font-mono text-[14px] leading-tight">{s.name}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* ── DOMAIN 1 — IDEATION & SCRIPTING ─────────────────────────── */}
          {domain === "script" && (
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_240px] gap-4">
              <section className="bg-panel border border-edge rounded-xl p-5">
                <h2 className="text-[17px] font-semibold mb-3">{proj?.title ?? "Select a project"} — Script</h2>
                {!proj || proj.scenes.length === 0 ? (
                  <div className="text-dim text-[15px]">No scene cards in the graph for this project. Draft them in the Streamlit Ad Studio, or via the stage agents.</div>
                ) : proj.scenes.map((s) => (
                  <div key={s.number} className="mb-3 border-l-2 border-edge pl-3">
                    <div className="text-[13px] text-dim font-mono mb-1">SCENE {s.number}{s.title ? ` · ${s.title}` : ""}</div>
                    {s.shots.map((sh) => (
                      <p key={sh.shotNumber} className="text-fg/90 text-[15px] leading-relaxed mb-1">{sh.prompt || <span className="text-dim italic">empty prompt</span>}</p>
                    ))}
                  </div>
                ))}
              </section>
              <aside className="bg-panel border border-edge rounded-xl p-4 h-fit">
                <div className="text-[13px] text-dim uppercase tracking-wide mb-2">Metadata</div>
                {proj ? (
                  <dl className="text-[14px] space-y-1.5 font-mono">
                    <div className="flex justify-between"><dt className="text-dim">type</dt><dd>{proj.type}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">status</dt><dd>{proj.status}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">greenlight</dt><dd>{proj.greenlightLevel ?? "—"}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">scenes</dt><dd>{proj.counts.scenes}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">shots</dt><dd>{proj.counts.shots}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">assets</dt><dd>{proj.counts.assets}</dd></div>
                  </dl>
                ) : <div className="text-dim text-sm">—</div>}
                <div className="mt-3 pt-3 border-t border-edge text-[12px] text-dim">Edit raw script in the Ad Studio (Streamlit). This view is the canonical read from Neon.</div>
              </aside>
            </div>
          )}

          {/* ── DOMAIN 2 — ASSET GENERATION ─────────────────────────────── */}
          {domain === "generation" && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[17px] font-semibold">Asset Generation {proj ? `— ${proj.title}` : ""}</h2>
                <span className="text-[13px] text-dim">scene nodes · status from the graph</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
                {(proj?.scenes ?? []).flatMap((s) => s.shots.map((sh) => {
                  const done = videoScenes.has(s.number);
                  const st = shotState(done, hasMaster);
                  const asset = projAssets.find((a) => a.assetType === "video" && a.sceneNumber === s.number);
                  return (
                    <div key={`${s.number}-${sh.shotNumber}`} className="bg-panel border border-edge rounded-lg overflow-hidden">
                      <div className="aspect-video bg-ink flex items-center justify-center text-dim text-[13px] font-mono relative">
                        <span className="absolute top-2 left-2 inline-flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: st.color }} />
                          <span className={st.cls + " text-[12px] uppercase tracking-wide"}>{st.label}</span>
                        </span>
                        {done ? "▶ preview in Studio" : "—"}
                      </div>
                      <div className="p-3">
                        <div className="text-[13px] text-dim font-mono mb-1">SCENE {s.number}</div>
                        <p className="text-[14px] text-fg/90 line-clamp-3" title={sh.prompt || ""}>{sh.prompt || <span className="text-dim italic">empty prompt</span>}</p>
                        <div className="mt-2 flex items-center justify-between text-[12px] font-mono text-dim">
                          <span>{asset?.model ?? "—"}{asset?.rating ? ` · ${asset.rating}` : ""}</span>
                          <span className="text-accent cursor-default" title="Regenerate / edit raw in the Ad Studio">⟳ re-render</span>
                        </div>
                      </div>
                    </div>
                  );
                }))}
                {(!proj || proj.scenes.length === 0) && <div className="text-dim text-[15px]">No scene nodes for this project yet.</div>}
              </div>
            </div>
          )}

          {/* ── DOMAIN 3 — TIMELINE & ASSEMBLY ──────────────────────────── */}
          {domain === "assembly" && (
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4">
              <section>
                <h2 className="text-[17px] font-semibold mb-3">Timeline & Assembly {proj ? `— ${proj.title}` : ""}</h2>
                <div className="aspect-video bg-black border border-edge rounded-lg flex items-center justify-center text-dim text-[14px] font-mono mb-3">
                  {hasMaster ? "■ master cut — open in Studio to play" : "no master assembled yet"}
                </div>
                {/* Multi-track timeline mock */}
                {["VIDEO", "AUDIO", "SFX/MUSIC"].map((track, ti) => (
                  <div key={track} className="flex items-center gap-2 mb-1.5">
                    <span className="w-20 text-[12px] text-dim font-mono uppercase">{track}</span>
                    <div className="flex-1 flex gap-1">
                      {(proj?.scenes ?? []).map((s) => (
                        <div key={s.number} className="h-7 flex-1 rounded-sm border border-edge flex items-center justify-center text-[11px] font-mono"
                          style={{ background: ti === 0 ? "#1b2027" : ti === 1 ? "#171b21" : "#141820", color: videoScenes.has(s.number) || ti > 0 ? "#97a1ad" : "#3a424d" }}>
                          {s.number}
                        </div>
                      ))}
                      {(!proj || proj.scenes.length === 0) && <span className="text-dim text-[13px]">—</span>}
                    </div>
                  </div>
                ))}
              </section>
              <aside className="bg-panel border border-edge rounded-xl p-4 h-fit">
                <div className="text-[13px] text-dim uppercase tracking-wide mb-2">Master render node</div>
                {projAssets.filter((a) => a.assetType === "master").slice(0, 1).map((m) => (
                  <dl key={m.id} className="text-[14px] space-y-1.5 font-mono">
                    <div className="flex justify-between"><dt className="text-dim">uri</dt><dd>{uriTail(m.uri)}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">engine</dt><dd>{m.model ?? "—"}</dd></div>
                    <div className="flex justify-between"><dt className="text-dim">rating</dt><dd>{m.rating}</dd></div>
                  </dl>
                ))}
                {!hasMaster && <div className="text-dim text-sm">Assemble a cut in the Ad Studio (gate-enforced before publish).</div>}
                <div className="mt-3 pt-3 border-t border-edge text-[12px] text-dim">Export / master settings live in the render pipeline. Publishing requires release approval (Analytics → rights queue).</div>
              </aside>
            </div>
          )}

          {/* ── DOMAIN 4 — PIPELINE ANALYTICS & GOVERNANCE ──────────────── */}
          {domain === "analytics" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Cost telemetry / control plane (matrix §8) */}
              <section className="bg-panel border border-edge rounded-xl p-4 lg:col-span-2">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[16px] font-semibold">Control Plane <span className="text-[13px] text-dim font-normal">· cost · provider mix · run health</span></h3>
                  <span className="text-[12px] text-dim">est. spend (not billed)</span>
                </div>
                <div className="flex flex-wrap gap-3 mb-3">
                  <div className="bg-ink border border-edge rounded-lg px-3.5 py-2">
                    <div className="text-xl font-bold font-mono text-amber">${(kpis.estCostCents / 100).toFixed(2)}</div>
                    <div className="text-[12px] text-dim uppercase tracking-wide">est. spend</div>
                  </div>
                  <div className="bg-ink border border-edge rounded-lg px-3.5 py-2">
                    <div className="text-xl font-bold font-mono">{kpis.costPerRenderSecCents.toFixed(1)}¢</div>
                    <div className="text-[12px] text-dim uppercase tracking-wide">est. ¢/render-sec</div>
                  </div>
                  <div className="bg-ink border border-edge rounded-lg px-3.5 py-2">
                    <div className="text-xl font-bold font-mono" style={{ color: kpis.runFail ? "#ef6f6c" : "#57c97a" }}>{kpis.runOk}/{kpis.runOk + kpis.runFail}</div>
                    <div className="text-[12px] text-dim uppercase tracking-wide">runs ok</div>
                  </div>
                  <div className="bg-ink border border-edge rounded-lg px-3.5 py-2">
                    <div className="text-xl font-bold font-mono">{kpis.renderRuns}</div>
                    <div className="text-[12px] text-dim uppercase tracking-wide">render runs</div>
                  </div>
                  <div className="bg-ink border border-edge rounded-lg px-3.5 py-2 opacity-70">
                    <div className="text-xl font-bold font-mono text-dim">—</div>
                    <div className="text-[12px] text-dim uppercase tracking-wide">archive · deferred (Phase 1)</div>
                  </div>
                </div>
                {/* Engine / provider mix */}
                <div className="text-[12px] text-dim uppercase tracking-wide mb-1.5">Engine mix (est. cost)</div>
                {engineMix.length === 0 ? <div className="text-dim text-[14px]">No render runs recorded yet.</div> : (
                  <div className="space-y-1">
                    {engineMix.map((e) => {
                      const max = engineMix[0].cost || 1;
                      return (
                        <div key={e.model} className="flex items-center gap-2 text-[13px]">
                          <span className="w-28 font-mono shrink-0">{e.model}</span>
                          <div className="flex-1 bg-ink rounded h-3 overflow-hidden border border-edge">
                            <div className="h-full bg-accent/40" style={{ width: `${Math.max(4, (e.cost / max) * 100)}%` }} />
                          </div>
                          <span className="w-28 text-right font-mono text-dim">{e.count} · ${(e.cost / 100).toFixed(2)}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Lanes */}
              <section className="bg-panel border border-edge rounded-xl p-4">
                <h3 className="text-[16px] font-semibold mb-3">Lanes <span className="text-[13px] text-dim font-normal">· projects by status</span></h3>
                <div className="flex flex-wrap gap-2">
                  {["draft", "active", "review", "blocked", "approved", "archived", "failed"].map((s) => {
                    const ps = projects.filter((p) => p.status === s);
                    if (!ps.length) return null;
                    return (
                      <div key={s} className="min-w-[150px]">
                        <div className="text-[12px] text-dim uppercase mb-1">{s} · {ps.length}</div>
                        {ps.map((p) => (
                          <div key={p.id} className="bg-ink border border-edge rounded-md p-2 mb-1.5">
                            <div className="text-[14px] font-medium">{p.title}</div>
                            <div className="text-[12px] text-dim font-mono">{p.type} · {p.counts.shots}sh · {p.counts.assets}as</div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Rights queue + approve */}
              <section className="bg-panel border border-edge rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-[16px] font-semibold">Rights · risk queue <span className="text-[13px] text-dim font-normal">· A4 release</span></h3>
                  <span className="text-[13px] text-dim flex items-center gap-1">reviewer
                    <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} className="bg-ink border border-edge rounded text-fg px-2 py-0.5 w-24 font-mono" /></span>
                </div>
                {queue.filter((q) => inProj(q.projectId)).length === 0 && <div className="text-dim text-[15px]">No release candidates.</div>}
                {queue.filter((q) => inProj(q.projectId)).map((item) => (
                  <div key={item.rightsId} className="bg-ink border border-edge rounded-md p-2.5 mb-2 border-l-[3px]"
                    style={{ borderLeftColor: item.approvedForRelease ? "#57c97a" : SEV[item.risk.severity] }}>
                    <div className="flex justify-between items-center">
                      <span className="text-[15px] font-medium">{item.projectTitle}</span>
                      <span className="text-[13px] font-mono" style={{ color: item.approvedForRelease ? "#57c97a" : SEV[item.risk.severity] }}>
                        {item.approvedForRelease ? `RELEASED · ${item.releaseStatus ?? ""}` : `${item.risk.tier} · risk ${item.risk.score}`}
                      </span>
                    </div>
                    <div className="text-[13px] text-dim mt-1">{item.approvedForRelease ? "approved for release" : (item.risk.factors.join(" · ") || "ready — confirm + approve")}</div>
                    {!item.approvedForRelease && (openApprove === item.rightsId ? (
                      <div className="mt-2 border border-edge rounded p-2 bg-panel">
                        <div className="text-[13px] text-dim mb-2">Clear the substantive risks (likeness / music / trademark) and accept the A4 release decision — non-delegable.</div>
                        <div className="flex gap-2 flex-wrap items-center">
                          <button disabled={busy === item.rightsId} onClick={() => approve(item, "clear")} className="text-good border border-good/40 rounded px-3 py-1 text-sm disabled:opacity-50" style={{ background: "rgba(87,201,122,0.12)" }}>{busy === item.rightsId ? "…" : "✓ Clear & approve"}</button>
                          <button onClick={() => setOpenApprove(null)} className="border border-edge text-dim rounded px-3 py-1 text-sm">Cancel</button>
                          <input placeholder="override reason" value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} className="bg-ink border border-edge rounded text-fg px-2 py-1 text-[13px] flex-1 min-w-[120px]" />
                          <button disabled={busy === item.rightsId} onClick={() => approve(item, "override")} className="text-mauve border border-mauve/40 rounded px-3 py-1 text-[13px] disabled:opacity-50" style={{ background: "rgba(185,140,255,0.12)" }}>Override</button>
                        </div>
                      </div>
                    ) : (
                      <button onClick={() => { setOpenApprove(item.rightsId); setMsg(null); }} className="mt-2 text-accent border border-accent/40 rounded px-3 py-1 text-sm" style={{ background: "rgba(91,157,255,0.12)" }}>Approve…</button>
                    ))}
                    {msg?.id === item.rightsId && <div className="text-[13px] mt-1" style={{ color: msg.ok ? "#57c97a" : "#ef6f6c" }}>{msg.text}</div>}
                  </div>
                ))}
              </section>

              {/* Lineage */}
              <section className="bg-panel border border-edge rounded-xl p-4">
                <h3 className="text-[16px] font-semibold mb-2">Workspace + assets <span className="text-[13px] text-dim font-normal">· click for detail</span></h3>
                <table className="w-full border-collapse text-sm">
                  <thead><tr className="text-dim text-left"><th className="py-1">Project</th><th>Type</th><th>URI</th><th>Model</th><th>Rating</th></tr></thead>
                  <tbody>
                    {projAssets.slice(0, 30).map((a) => (
                      <Fragment key={a.id}>
                        <tr onClick={() => setExpanded(expanded === a.id ? null : a.id)} className="border-t border-edge cursor-pointer hover:bg-ink">
                          <td className="py-1 pr-2">{a.projectTitle}</td>
                          <td><span className={a.assetType === "master" ? "text-mauve" : "text-dim"}>{a.assetType ?? "—"}</span></td>
                          <td className="font-mono text-dim">{uriTail(a.uri, 14)}</td>
                          <td className="font-mono">{a.model ?? "—"}</td>
                          <td><span className={a.rating === "clean" ? "text-dim" : "text-amber"}>{a.rating}</span></td>
                        </tr>
                        {expanded === a.id && (
                          <tr className="bg-ink"><td colSpan={5} className="px-3 py-2 text-[13px] text-dim font-mono">
                            <div className="text-fg/80 mb-1 break-all">{a.uri}</div>
                            <div>asset {short(a.id, 12)} · {a.assetType ?? "—"} · {a.rating}{a.model ? ` · ${a.model}` : ""}</div>
                          </td></tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </section>

              {/* Trace */}
              <section className="bg-panel border border-edge rounded-xl p-4">
                <h3 className="text-[16px] font-semibold mb-2">Trace timeline <span className="text-[13px] text-dim font-normal">· agent · render · approval</span></h3>
                {runs.length === 0 && <div className="text-dim text-[15px]">No runs recorded yet.</div>}
                {runs.map((run) => {
                  const gs = run.humanGateStatus;
                  const color = gs === "approved" || gs === "auto_approved" ? "#57c97a" : gs === "rejected" ? "#ef6f6c" : "#e0a13a";
                  return (
                    <div key={run.id} className="flex gap-2.5 text-sm py-1.5 border-t border-edge">
                      <span className="text-dim min-w-24 font-mono">{fmt(run.when)}</span>
                      <span className="min-w-20 font-mono" style={{ color }}>{gs ?? "—"}</span>
                      <span className="flex-1"><b>{run.agentName ?? "run"}</b>{run.plane && <span className="text-dim font-mono"> · {run.plane}</span>}{run.costCents != null && <span className="text-dim"> · ${(run.costCents / 100).toFixed(2)}</span>}</span>
                    </div>
                  );
                })}
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
