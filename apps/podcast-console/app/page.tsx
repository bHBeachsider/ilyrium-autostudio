import Link from "next/link"
import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { loadDashboard, type DashboardData } from "@/lib/dashboard"
import {
  Archive,
  CheckCircle2,
  Clapperboard,
  Database,
  Lightbulb,
  ListChecks,
  Radio,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react"

// Live production dashboard — every panel reads the studio's real state.
export const dynamic = "force-dynamic"

function fmt(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

const STEP_LABELS: Record<string, string> = {
  research: "researching sources",
  script: "writing script",
  verify: "fact-checking",
  audio: "synthesizing voices",
  images: "generating scenes",
  video: "rendering video",
  finalize: "finalizing",
}

const SOURCE_LABEL: Record<string, string> = {
  generated: "Generated",
  imported_local: "Imported",
  imported_api: "Imported",
  imported_rss: "Imported",
}

function MetricCard({ label, value, hint, href }: { label: string; value: number; hint?: string; href: string }) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-1 rounded-xl border border-slate-800 bg-slate-900 p-4 transition-colors hover:border-slate-700"
    >
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-3xl font-semibold tracking-tight text-slate-50">{value}</span>
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
    </Link>
  )
}

export default async function Page() {
  const data: DashboardData = await loadDashboard()

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-col gap-1">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Production Dashboard</h1>
              <p className="text-sm text-slate-400">Live studio state — ideas, pipeline, episodes, and system health.</p>
            </div>

            {!data.configured && (
              <div className="flex items-center gap-2 rounded-xl border border-amber-700/40 bg-amber-500/5 p-4 text-sm text-amber-300">
                <Database className="size-4" aria-hidden="true" />
                Database not connected — metrics unavailable.
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <MetricCard label="Episodes" value={data.counts.episodes} hint="in the archive" href="/episode-archive" />
              <MetricCard label="Published" value={data.counts.published} hint="live on Transistor" href="/episode-archive" />
              <MetricCard
                label="Awaiting review"
                value={data.counts.proposed}
                hint={`${data.counts.approved} approved, ready to produce`}
                href="/review"
              />
              <MetricCard
                label="Gate rejections"
                value={data.counts.rejectedByGate}
                hint="failed jobs (fact-check & errors)"
                href="/review"
              />
            </div>

            <section className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5">
              <div className="flex items-center gap-2">
                <Clapperboard className="size-4 text-emerald-400" aria-hidden="true" />
                <h2 className="text-sm font-semibold text-slate-200">Production pipeline</h2>
              </div>
              {data.pipeline.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Nothing in flight. Approve an idea in the <Link href="/review" className="text-emerald-400 underline underline-offset-2">review queue</Link> and hit Produce.
                </p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {data.pipeline.map((j, i) => (
                    <li key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800/70 bg-slate-950/40 px-3 py-2">
                      <span className="min-w-0 flex-1 truncate text-sm text-slate-300">{j.ideaTitle}</span>
                      <span className="flex items-center gap-2 text-xs">
                        {j.status === "failed" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2 py-0.5 text-rose-300" title={j.error ?? undefined}>
                            <ShieldAlert className="size-3" aria-hidden="true" />
                            failed: {STEP_LABELS[j.step] ?? j.step}
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-violet-500/15 px-2 py-0.5 text-violet-300">
                            {STEP_LABELS[j.step] ?? j.step} · {j.status}
                          </span>
                        )}
                        <span className="text-slate-600">{fmt(j.updatedAt)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <section className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 lg:col-span-1">
                <div className="flex items-center gap-2">
                  <Radio className="size-4 text-emerald-400" aria-hidden="true" />
                  <h2 className="text-sm font-semibold text-slate-200">System health</h2>
                </div>
                <ul className="flex flex-col gap-2">
                  {data.health.map((h) => (
                    <li key={h.name} className="flex items-center justify-between gap-2 text-sm">
                      <span className="text-slate-300">{h.name}</span>
                      <span className={`inline-flex items-center gap-1 text-xs ${h.ok ? "text-emerald-400" : "text-slate-500"}`}>
                        {h.ok ? <ShieldCheck className="size-3.5" aria-hidden="true" /> : <ShieldAlert className="size-3.5" aria-hidden="true" />}
                        {h.detail}
                      </span>
                    </li>
                  ))}
                </ul>
                {data.lastLoopRun && (
                  <p className="border-t border-slate-800 pt-2 text-xs text-slate-500">
                    Last idea-loop run: {data.lastLoopRun.finishedAt ? fmt(data.lastLoopRun.finishedAt) : "incomplete"} —{" "}
                    {String((data.lastLoopRun.counts as Record<string, unknown>).proposed ?? 0)} proposed
                  </p>
                )}
              </section>

              <section className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 lg:col-span-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Archive className="size-4 text-emerald-400" aria-hidden="true" />
                    <h2 className="text-sm font-semibold text-slate-200">Recent episodes</h2>
                  </div>
                  <Link href="/episode-archive" className="text-xs text-emerald-400 underline underline-offset-2">
                    view all
                  </Link>
                </div>
                {data.recentEpisodes.length === 0 ? (
                  <p className="text-sm text-slate-500">No episodes yet.</p>
                ) : (
                  <ul className="flex flex-col gap-2">
                    {data.recentEpisodes.map((e) => (
                      <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800/70 bg-slate-950/40 px-3 py-2">
                        <span className="min-w-0 flex-1 truncate text-sm text-slate-300">{e.title}</span>
                        <span className="flex items-center gap-2 text-xs">
                          {e.claims != null && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-300" title="fact-checked claims">
                              <CheckCircle2 className="size-3" aria-hidden="true" />
                              {e.claims} claims
                            </span>
                          )}
                          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-slate-400">{SOURCE_LABEL[e.source] ?? e.source}</span>
                          {e.published ? (
                            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-emerald-300">published</span>
                          ) : (
                            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-slate-500">unpublished</span>
                          )}
                          <span className="text-slate-600">{fmt(e.createdAt)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link href="/review" className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400">
                <ListChecks className="size-4" aria-hidden="true" /> Review queue
              </Link>
              <Link href="/episode-archive" className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
                <Archive className="size-4" aria-hidden="true" /> Episode archive
              </Link>
              <Link href="/sandbox" className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
                <Lightbulb className="size-4" aria-hidden="true" /> Idea sandbox
              </Link>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
