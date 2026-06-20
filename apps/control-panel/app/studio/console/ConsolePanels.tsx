"use client";

import { Fragment, useState } from "react";
import { useRouter } from "next/navigation";

// Interactive panes for the Oversight Console (Phase 1 reconcile): project filter, the
// risk-scored rights queue with approve/override actions (→ /api/studio/approve), and an
// asset detail drill-down. Receives serialized data from the server component; mutates via
// the API then refreshes. Assets are uri-addressed with a lowercase assetType + rating
// (no checksum/provenance/C2PA); rights are the risk-based model.

type Risk = { score: number; tier: string; severity: string; factors: string[] };
type AssetRow = { id: string; assetType: string | null; uri: string; rating: string; projectId: string | null; projectTitle: string; model: string | null };
type QueueRow = { rightsId: string; assetId: string | null; assetUri: string | null; projectId: string | null; projectTitle: string; approvedForRelease: boolean; releaseStatus: string | null; riskLevel: string | null; risk: Risk };
type RunRow = { id: string; when: string; humanGateStatus: string | null; agentName: string | null; plane: string | null; projectId: string | null };
type AssetMap = Record<string, { uri: string; assetType: string | null; model: string | null }>;

const SEV: Record<string, string> = { high: "#f85149", medium: "#d29922", low: "#3fb950", override: "#bc8cff" };
const short = (s?: string | null, n = 8) => (s ? s.slice(0, n) + "…" : "—");
const uriTail = (u?: string | null, n = 18) => (u ? (u.length > n ? "…" + u.slice(-n) : u) : "—");
const fmt = (iso: string) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

function Pane({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="bg-panel border border-edge rounded-xl p-4 min-h-56 overflow-auto">
      <div className="flex justify-between items-baseline mb-3">
        <h2 className="m-0 text-[15px] font-semibold">{title}</h2>
        {hint && <span className="text-[11px] text-dim">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

export default function ConsolePanels({ assets, queue, runs, projectOpts, assetMap }:
  { assets: AssetRow[]; queue: QueueRow[]; runs: RunRow[]; projectOpts: { id: string; title: string }[]; assetMap: AssetMap }) {
  const router = useRouter();
  const [project, setProject] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [openApprove, setOpenApprove] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("brad");
  const [overrideReason, setOverrideReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ id: string; text: string; ok: boolean } | null>(null);

  const inProject = (id: string | null) => project === "all" || id === project;
  const fAssets = assets.filter((a) => inProject(a.projectId));
  const fQueue = queue.filter((q) => inProject(q.projectId));
  const fRuns = runs.filter((r) => inProject(r.projectId));

  async function approve(item: QueueRow, mode: "clear" | "override") {
    if (!reviewer.trim()) { setMsg({ id: item.rightsId, text: "Reviewer required.", ok: false }); return; }
    if (mode === "override" && !overrideReason.trim()) { setMsg({ id: item.rightsId, text: "Override reason required.", ok: false }); return; }
    if (!item.projectId) { setMsg({ id: item.rightsId, text: "Master has no project id.", ok: false }); return; }
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
        setOpenApprove(null); setOverrideReason("");
        router.refresh();
      } else {
        setMsg({ id: item.rightsId, text: `Failed: ${data.error || res.status}`, ok: false });
      }
    } catch (e: any) {
      setMsg({ id: item.rightsId, text: `Error: ${e?.message || e}`, ok: false });
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      {/* PANE 2 — Workspace + assets (drill-down) */}
      <Pane title="② Workspace + assets" hint="click a row → asset detail">
        <div className="mb-2">
          <select value={project} onChange={(e) => setProject(e.target.value)}
            className="bg-ink border border-edge rounded-md text-fg text-xs px-2 py-1">
            <option value="all">All projects</option>
            {projectOpts.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
        <table className="w-full border-collapse text-xs">
          <thead><tr className="text-dim text-left">
            <th className="py-1 px-1.5">Project</th><th>Type</th><th>URI</th><th>Model</th><th>Rating</th>
          </tr></thead>
          <tbody>
            {fAssets.map((a) => (
              <Fragment key={a.id}>
                <tr onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                  className="border-t border-edge cursor-pointer hover:bg-ink">
                  <td className="py-1 px-1.5">{a.projectTitle}</td>
                  <td><span className={a.assetType === "master" ? "text-mauve" : "text-dim"}>{a.assetType ?? "—"}</span></td>
                  <td className="font-mono text-dim">{uriTail(a.uri, 14)}</td>
                  <td>{a.model ?? "—"}</td>
                  <td><span className={a.rating === "clean" ? "text-dim" : "text-amber"}>{a.rating}</span></td>
                </tr>
                {expanded === a.id && (
                  <tr className="bg-ink">
                    <td colSpan={5} className="px-3 py-2 text-[11px] text-dim">
                      <div className="mb-1 text-fg">Detail for {a.assetType ?? "asset"} {short(a.id)}</div>
                      <div className="break-all font-mono">{a.uri}</div>
                      <div>rating: {a.rating}{a.model ? ` · model: ${a.model}` : ""}</div>
                      {assetMap[a.id] && <div className="font-mono">graph: {assetMap[a.id].assetType ?? "—"} ({assetMap[a.id].model ?? "?"})</div>}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </Pane>

      {/* PANE 3 — Rights queue with approve/override */}
      <Pane title="③ Rights · risk queue" hint="A4 release decisions">
        <div className="flex items-center gap-2 mb-2 text-[11px]">
          <span className="text-dim">reviewer</span>
          <input value={reviewer} onChange={(e) => setReviewer(e.target.value)}
            className="bg-ink border border-edge rounded-md text-fg px-2 py-1 w-28" />
        </div>
        {fQueue.length === 0 && <div className="text-dim text-[13px]">No release candidates.</div>}
        {fQueue.map((item) => (
          <div key={item.rightsId} className="bg-ink border border-edge rounded-lg p-2.5 mb-2 border-l-[3px]"
            style={{ borderLeftColor: item.approvedForRelease ? "#3fb950" : SEV[item.risk.severity] }}>
            <div className="flex justify-between items-center">
              <span className="font-semibold text-[13px]">{item.projectTitle}</span>
              <span className="text-[11px]" style={{ color: item.approvedForRelease ? "#3fb950" : SEV[item.risk.severity] }}>
                {item.approvedForRelease ? `RELEASED · ${item.releaseStatus ?? ""}` : `${item.risk.tier} · risk ${item.risk.score} · ${item.risk.severity}`}
              </span>
            </div>
            <div className="text-[11px] text-dim mt-1">
              {item.approvedForRelease ? "approved for release" : (item.risk.factors.join(" · ") || "ready — confirm + approve")}
            </div>

            {!item.approvedForRelease && (
              <div className="mt-2">
                {openApprove === item.rightsId ? (
                  <div className="border border-edge rounded-md p-2 bg-panel">
                    <div className="text-[11px] text-dim mb-2">
                      Clear the substantive risks (<b className="text-fg">likeness / music / trademark</b>) and accept the A4 release decision. This is non-delegable.
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <button disabled={busy === item.rightsId} onClick={() => approve(item, "clear")}
                        className="bg-good/20 text-good border border-good/40 rounded-md px-3 py-1 text-xs disabled:opacity-50">
                        {busy === item.rightsId ? "…" : "✓ Clear & approve"}
                      </button>
                      <button disabled={busy === item.rightsId} onClick={() => setOpenApprove(null)}
                        className="border border-edge text-dim rounded-md px-3 py-1 text-xs">Cancel</button>
                    </div>
                    <div className="mt-2 flex gap-2 items-center">
                      <input placeholder="override reason (logged)" value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)}
                        className="bg-ink border border-edge rounded-md text-fg px-2 py-1 text-[11px] flex-1" />
                      <button disabled={busy === item.rightsId} onClick={() => approve(item, "override")}
                        className="bg-mauve/15 text-mauve border border-mauve/40 rounded-md px-3 py-1 text-[11px] disabled:opacity-50">
                        Override
                      </button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => { setOpenApprove(item.rightsId); setMsg(null); }}
                    className="bg-accent/15 text-accent border border-accent/40 rounded-md px-3 py-1 text-xs">
                    Approve…
                  </button>
                )}
              </div>
            )}
            {msg?.id === item.rightsId && (
              <div className="text-[11px] mt-1" style={{ color: msg.ok ? "#3fb950" : "#f85149" }}>{msg.text}</div>
            )}
          </div>
        ))}
      </Pane>

      {/* PANE 4 — Trace timeline */}
      <Pane title="④ Trace timeline" hint="agent · render · approval runs">
        {fRuns.length === 0 && <div className="text-dim text-[13px]">No runs recorded yet.</div>}
        {fRuns.map((run) => {
          const gs = run.humanGateStatus;
          const color = gs === "approved" || gs === "auto_approved" ? "#3fb950" : gs === "rejected" ? "#f85149" : "#d29922";
          return (
            <div key={run.id} className="flex gap-2.5 text-xs py-1.5 border-t border-edge">
              <span className="text-dim min-w-24">{fmt(run.when)}</span>
              <span className="min-w-20" style={{ color }}>{gs ?? "—"}</span>
              <span className="flex-1">
                <b>{run.agentName ?? "run"}</b>
                {run.plane && <span className="text-mauve"> · {run.plane}</span>}
              </span>
            </div>
          );
        })}
      </Pane>
    </>
  );
}
