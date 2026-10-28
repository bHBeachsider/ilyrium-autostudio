"use client";
import { useCallback, useEffect, useState } from "react";

type JobStatus = "queued" | "running" | "done" | "failed" | "cancelled";

type Job = {
  job_id: string;
  op: string;
  status: JobStatus;
  scene_number?: number | null;
  model?: string | null;
  eta_s?: number | null;
  cost_cents?: number | null;
  error?: string | null;
};

const DOT: Record<JobStatus, string> = {
  queued: "🟡", running: "🟠", done: "🟢", failed: "🔴", cancelled: "⚪",
};

export default function QueueRail({ pipe }: { pipe: string }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${pipe}/pipeline/jobs`);
      if (r.ok) {
        const d = await r.json();
        setJobs(d.jobs || []);
      } else {
        setJobs([]);
      }
    } catch { setJobs([]); }
    finally { setLoaded(true); }
  }, [pipe]);

  useEffect(() => {
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [load]);

  async function act(verb: "cancel" | "retry", job_id: string) {
    setBusy(job_id);
    try { await fetch(`${pipe}/pipeline/jobs/${job_id}/${verb}`, { method: "POST" }); await load(); }
    catch {} finally { setBusy(null); }
  }

  const active = jobs.filter((j) => j.status === "running" || j.status === "queued");
  const recent = jobs.filter((j) => j.status === "done" || j.status === "failed" || j.status === "cancelled").slice(0, 6);

  return (
    <section className="bg-panel border border-edge rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[16px] font-semibold">
          Generation Queue
          {active.length > 0 && (
            <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-bold"
              style={{ background: "rgba(224,161,58,0.25)", color: "#e0a13a" }}>{active.length}</span>
          )}
        </h3>
        <button onClick={load} className="text-[11px] text-dim border border-edge rounded px-2 py-0.5 hover:bg-raised">
          Refresh
        </button>
      </div>

      {!loaded && <div className="text-dim text-[13px]">Loading…</div>}

      {loaded && active.length === 0 && (
        <div className="bg-ink border border-edge rounded-lg px-4 py-3 text-[14px] text-dim">
          Queue is idle — no active jobs.
        </div>
      )}

      <div className="space-y-2">
        {active.map((j) => (
          <div key={j.job_id} className="bg-ink border border-edge rounded-lg p-3 flex items-center gap-3">
            <span className="text-[18px] shrink-0">{DOT[j.status]}</span>
            <div className="flex-1 min-w-0">
              <div className="text-[14px] font-mono truncate">
                {j.op}{j.scene_number != null ? ` · S${j.scene_number}` : ""}
                {j.model ? ` · ${j.model}` : ""}
              </div>
              <div className="text-[11px] text-dim">
                {j.status}
                {j.eta_s != null ? ` · ~${j.eta_s}s left` : ""}
                {j.cost_cents != null ? ` · ${j.cost_cents.toFixed(1)}c` : ""}
              </div>
            </div>
            <button disabled={busy === j.job_id} onClick={() => act("cancel", j.job_id)}
              className="text-[12px] border border-edge rounded px-2 py-0.5 text-dim hover:text-bad disabled:opacity-40">
              Cancel
            </button>
          </div>
        ))}
      </div>

      {recent.length > 0 && (
        <div className="mt-3">
          <div className="text-[11px] text-dim uppercase tracking-wide mb-1.5">Recent</div>
          {recent.map((j) => (
            <div key={j.job_id} className="flex items-center gap-2 py-1 border-b border-edge/40 last:border-0 text-[12px]">
              <span className="text-[14px]">{DOT[j.status]}</span>
              <span className="font-mono text-dim truncate flex-1">
                {j.op}{j.scene_number != null ? ` S${j.scene_number}` : ""}
              </span>
              {j.cost_cents != null && (
                <span className="font-mono shrink-0" style={{ color: "#97a1ad" }}>{j.cost_cents.toFixed(1)}c</span>
              )}
              {j.status === "failed" && (
                <button disabled={busy === j.job_id} onClick={() => act("retry", j.job_id)}
                  className="border border-accent/40 rounded px-1.5 text-accent disabled:opacity-40">
                  Retry
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
