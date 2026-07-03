"use client"

import * as React from "react"
import { Check, Clapperboard, Loader2, MessageCircleWarning, Sparkles, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { IdeaRow, JobRow, ScriptRow } from "@/lib/db"

type IdeasResponse = { ideas: IdeaRow[]; scripts: ScriptRow[]; jobs: JobRow[]; twoGate: boolean; error?: string }

const STEP_LABELS: Record<string, string> = {
  script: "writing script",
  audio: "synthesizing voices",
  images: "generating scenes",
  video: "rendering video",
  finalize: "publishing to archive",
  done: "done",
}

const STATUS_CHIPS: Record<string, string> = {
  proposed: "bg-sky-500/15 text-sky-300",
  needs_changes: "bg-amber-500/15 text-amber-300",
  approved: "bg-emerald-500/15 text-emerald-300",
  rejected: "bg-rose-500/15 text-rose-300",
  producing: "bg-violet-500/15 text-violet-300",
  produced: "bg-emerald-500/15 text-emerald-300",
  published: "bg-emerald-500/25 text-emerald-200",
}

function Chip({ value }: { value: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CHIPS[value] ?? "bg-slate-800 text-slate-300"}`}
    >
      {value.replace("_", " ")}
    </span>
  )
}

export function ReviewQueue() {
  const [data, setData] = React.useState<IdeasResponse | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [generating, setGenerating] = React.useState(false)
  const [busyId, setBusyId] = React.useState<string | null>(null)
  const [notes, setNotes] = React.useState<Record<string, string>>({})
  const [producing, setProducing] = React.useState<Record<string, JobRow>>({})

  const load = React.useCallback(async () => {
    try {
      const res = await fetch("/api/ideas")
      const body = (await res.json()) as IdeasResponse
      if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`)
      setData(body)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ideas.")
    }
  }, [])

  React.useEffect(() => {
    void load()
  }, [load])

  async function generate() {
    setGenerating(true)
    try {
      const res = await fetch("/api/ideas/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count: 5 }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.")
    } finally {
      setGenerating(false)
    }
  }

  async function decide(ideaId: string, decision: "approved" | "rejected" | "needs_changes") {
    setBusyId(ideaId)
    try {
      const res = await fetch(`/api/ideas/${ideaId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, note: notes[ideaId] || undefined }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed.")
    } finally {
      setBusyId(null)
    }
  }

  async function decideScript(scriptId: string, decision: "approved" | "rejected") {
    setBusyId(scriptId)
    try {
      const res = await fetch(`/api/scripts/${scriptId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Script decision failed.")
    } finally {
      setBusyId(null)
    }
  }

  // Drive a job to completion: call /step until done or failed, refreshing the list.
  async function produce(ideaId: string) {
    setBusyId(ideaId)
    try {
      const startRes = await fetch(`/api/ideas/${ideaId}/produce`, { method: "POST" })
      const startBody = await startRes.json().catch(() => ({}))
      if (!startRes.ok) throw new Error(startBody.error ?? `HTTP ${startRes.status}`)
      let job: JobRow = startBody.job
      setProducing((p) => ({ ...p, [ideaId]: job }))
      while (job.step !== "done" && job.status !== "failed") {
        const res = await fetch(`/api/jobs/${job.id}/step`, { method: "POST" })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) {
          setProducing((p) => ({ ...p, [ideaId]: body.job ?? job }))
          throw new Error(body.error ?? `HTTP ${res.status}`)
        }
        job = body.job
        setProducing((p) => ({ ...p, [ideaId]: job }))
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Production failed.")
      await load()
    } finally {
      setBusyId(null)
    }
  }

  const ideas = data?.ideas ?? []
  const queue = ideas.filter((i) => i.status === "proposed" || i.status === "needs_changes")
  const decided = ideas.filter((i) => i.status !== "proposed" && i.status !== "needs_changes").slice(0, 12)
  const scriptByIdea = new Map((data?.scripts ?? []).map((s) => [s.idea_id, s]))
  const jobByIdea = new Map((data?.jobs ?? []).map((j) => [j.idea_id, j]))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          {queue.length} awaiting review
          {data?.twoGate ? " · two-gate mode (idea + script approval)" : ""}
        </p>
        <Button onClick={generate} disabled={generating} className="gap-1.5">
          {generating ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" aria-hidden="true" />}
          {generating ? "Generating…" : "Generate ideas"}
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-700/40 bg-rose-500/5 p-4 text-sm text-rose-300">{error}</div>
      )}

      {queue.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-12 text-center">
          <ListEmptyIcon />
          <p className="text-sm font-medium text-slate-300">Queue is empty</p>
          <p className="max-w-prose text-sm text-slate-500">
            Run &quot;Generate ideas&quot; — the agent proposes episodes from recent source material.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {queue.map((idea) => {
            const script = scriptByIdea.get(idea.id)
            const busy = busyId === idea.id
            return (
              <li key={idea.id} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-balance text-base font-semibold text-slate-100">{idea.title}</h3>
                    <Chip value={idea.status} />
                    {idea.score != null && (
                      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                        score {Number(idea.score).toFixed(1)}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-500">by {idea.created_by ?? "unknown"}</span>
                </div>
                {idea.angle && <p className="text-sm italic text-slate-400">{idea.angle}</p>}
                {idea.summary && <p className="text-sm text-slate-300">{idea.summary}</p>}
                {idea.rationale && (
                  <p className="rounded-lg border border-slate-800 bg-slate-950/50 p-2.5 text-xs text-slate-400">
                    <span className="font-medium text-slate-300">Why now: </span>
                    {idea.rationale}
                  </p>
                )}
                {Array.isArray(idea.source_refs) && idea.source_refs.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {idea.source_refs.map((ref, i) => (
                      <span key={i} className="rounded-full bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">
                        {ref}
                      </span>
                    ))}
                  </div>
                )}
                {idea.review_note && idea.status === "needs_changes" && (
                  <p className="flex items-start gap-1.5 text-xs text-amber-300/90">
                    <MessageCircleWarning className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                    {idea.review_note}
                  </p>
                )}
                <div className="flex flex-col gap-2 border-t border-slate-800 pt-3">
                  <Textarea
                    placeholder="Optional review note…"
                    value={notes[idea.id] ?? ""}
                    onChange={(e) => setNotes((n) => ({ ...n, [idea.id]: e.target.value }))}
                    className="min-h-8 bg-slate-950/50 text-sm"
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => decide(idea.id, "approved")} disabled={busy} className="gap-1">
                      <Check className="size-3.5" aria-hidden="true" /> Approve
                    </Button>
                    {idea.status === "proposed" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => decide(idea.id, "needs_changes")}
                        disabled={busy}
                      >
                        Request changes
                      </Button>
                    )}
                    <Button size="sm" variant="outline" onClick={() => decide(idea.id, "rejected")} disabled={busy} className="gap-1 text-rose-300">
                      <X className="size-3.5" aria-hidden="true" /> Reject
                    </Button>
                    {busy && <Loader2 className="size-4 animate-spin self-center text-slate-500" />}
                  </div>
                </div>
                {script && <ScriptPanel script={script} onDecide={decideScript} busy={busyId === script.id} />}
              </li>
            )
          })}
        </ul>
      )}

      {decided.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-slate-300">Recently decided</h2>
          <ul className="flex flex-col gap-2">
            {decided.map((idea) => {
              const script = scriptByIdea.get(idea.id)
              const job = producing[idea.id] ?? jobByIdea.get(idea.id)
              const busy = busyId === idea.id
              const scriptGateOpen = !data?.twoGate || script?.status === "approved"
              const canProduce =
                (idea.status === "approved" && scriptGateOpen) || (idea.status === "producing" && job?.status === "failed")
              return (
                <li
                  key={idea.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800/70 bg-slate-900/60 px-4 py-2.5"
                >
                  <span className="text-sm text-slate-300">{idea.title}</span>
                  <span className="flex items-center gap-2">
                    {script && data?.twoGate && (
                      <span className="text-xs text-slate-500">script: {script.status}</span>
                    )}
                    {busy && job && job.status !== "failed" ? (
                      <span className="flex items-center gap-1.5 text-xs text-violet-300">
                        <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                        {STEP_LABELS[job.step] ?? job.step}…
                      </span>
                    ) : job?.status === "failed" ? (
                      <span className="max-w-64 truncate text-xs text-rose-300" title={job.error ?? ""}>
                        failed at {STEP_LABELS[job.step] ?? job.step}
                      </span>
                    ) : null}
                    {canProduce && !busy && (
                      <Button size="sm" onClick={() => produce(idea.id)} className="gap-1">
                        <Clapperboard className="size-3.5" aria-hidden="true" />
                        {job?.status === "failed" ? "Retry production" : "Produce"}
                      </Button>
                    )}
                    {idea.status === "produced" && idea.episode_id && (
                      <a href="/episode-archive" className="text-xs text-emerald-300 underline underline-offset-2">
                        view in archive
                      </a>
                    )}
                    {idea.reviewer && <span className="text-xs text-slate-500">by {idea.reviewer}</span>}
                    <Chip value={idea.status} />
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

function ScriptPanel({
  script,
  onDecide,
  busy,
}: {
  script: ScriptRow
  onDecide: (id: string, decision: "approved" | "rejected") => void
  busy: boolean
}) {
  const [open, setOpen] = React.useState(false)
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium text-slate-300">
          Draft script v{script.version} · {script.segments.length} segments · ~{script.estimated_minutes ?? "?"} min ·{" "}
          <Chip value={script.status} />
        </p>
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={() => setOpen((o) => !o)}>
            {open ? "Hide" : "Read"}
          </Button>
          {script.status === "draft" && (
            <>
              <Button size="sm" onClick={() => onDecide(script.id, "approved")} disabled={busy}>
                Approve script
              </Button>
              <Button size="sm" variant="outline" onClick={() => onDecide(script.id, "rejected")} disabled={busy}>
                Reject
              </Button>
            </>
          )}
        </div>
      </div>
      {open && (
        <div className="mt-2 flex max-h-64 flex-col gap-1.5 overflow-y-auto">
          {script.segments.map((s, i) => (
            <p key={i} className="text-xs text-slate-400">
              <span className="font-medium text-slate-300">{s.speaker}:</span> {s.text}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

function ListEmptyIcon() {
  return <Sparkles className="size-8 text-slate-600" aria-hidden="true" />
}
