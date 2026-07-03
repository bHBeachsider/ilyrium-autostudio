import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { ImportDialog } from "@/components/archive/import-dialog"
import { DistributeButton } from "@/components/archive/distribute-button"
import { dbReady, ensureSchema, requireSql, type DistributionRow, type EpisodeRow, type EpisodeSource } from "@/lib/db"
import { Archive, AudioLines, CalendarDays, FolderOpen, Gavel, MessageSquare, Database } from "lucide-react"

// Always read fresh from the DB.
export const dynamic = "force-dynamic"

async function loadEpisodes(): Promise<{ episodes: EpisodeRow[]; distributions: Map<string, DistributionRow[]> }> {
  if (!dbReady()) return { episodes: [], distributions: new Map() }
  try {
    const sql = requireSql()
    await ensureSchema()
    const rows = (await sql`SELECT * FROM podcast_episodes ORDER BY created_at DESC`) as unknown as EpisodeRow[]
    const dists = (await sql`SELECT * FROM podcast_distributions ORDER BY created_at`) as unknown as DistributionRow[]
    const byEpisode = new Map<string, DistributionRow[]>()
    for (const d of dists) {
      const list = byEpisode.get(d.episode_id) ?? []
      list.push(d)
      byEpisode.set(d.episode_id, list)
    }
    return { episodes: rows, distributions: byEpisode }
  } catch {
    return { episodes: [], distributions: new Map() }
  }
}

const DIST_CHIP: Record<string, string> = {
  published: "bg-emerald-500/15 text-emerald-300",
  draft: "bg-sky-500/15 text-sky-300",
  assets_ready: "bg-violet-500/15 text-violet-300",
  manual: "bg-amber-500/15 text-amber-300",
  pending: "bg-slate-800 text-slate-400",
  failed: "bg-rose-500/15 text-rose-300",
}

// week_of is a Postgres `date`; the Neon driver decodes it to a JS Date at LOCAL
// midnight, so format from local date parts (String(date).slice would garble it,
// toISOString could shift a day in positive-UTC-offset zones).
function fmtWeekOf(value: unknown): string {
  if (value instanceof Date) {
    const m = String(value.getMonth() + 1).padStart(2, "0")
    const d = String(value.getDate()).padStart(2, "0")
    return `${value.getFullYear()}-${m}-${d}`
  }
  return String(value).slice(0, 10)
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })
}

const SOURCE_BADGES: Record<EpisodeSource, { label: string; className: string }> = {
  generated: { label: "Generated", className: "bg-emerald-500/15 text-emerald-300" },
  imported_local: { label: "Imported · Local", className: "bg-sky-500/15 text-sky-300" },
  imported_api: { label: "Imported · PermitHub", className: "bg-violet-500/15 text-violet-300" },
  imported_rss: { label: "Imported · RSS", className: "bg-amber-500/15 text-amber-300" },
}

function SourceBadge({ source }: { source: EpisodeSource }) {
  const badge = SOURCE_BADGES[source] ?? SOURCE_BADGES.generated
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
      {badge.label}
    </span>
  )
}

export default async function EpisodeArchivePage() {
  const configured = dbReady()
  const { episodes, distributions } = await loadEpisodes()

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header section="Studio" page="Episode Archive" />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                    <Archive className="size-4.5" aria-hidden="true" />
                  </span>
                  <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Episode Archive</h1>
                </div>
                <p className="text-sm text-slate-400">
                  Every generated and imported episode, persisted to your studio database.
                </p>
              </div>
              {configured && <ImportDialog />}
            </div>

            {!configured ? (
              <div className="flex flex-col items-start gap-2 rounded-xl border border-amber-700/40 bg-amber-500/5 p-5">
                <span className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <Database className="size-4" aria-hidden="true" />
                  Database not connected
                </span>
                <p className="max-w-prose text-sm text-slate-400">
                  Add a Neon connection string as <code className="rounded bg-slate-800 px-1 py-0.5 text-slate-200">DATABASE_URL</code> in{" "}
                  <code className="rounded bg-slate-800 px-1 py-0.5 text-slate-200">apps/podcast-console/.env.local</code> and restart the
                  dev server. Until then, episodes stay session-only and won&apos;t appear here after a reload.
                </p>
              </div>
            ) : episodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-12 text-center">
                <Archive className="size-8 text-slate-600" aria-hidden="true" />
                <p className="text-sm font-medium text-slate-300">No episodes yet</p>
                <p className="max-w-prose text-sm text-slate-500">
                  Generate and render an episode in the Idea Sandbox — it&apos;ll be saved here automatically.
                </p>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {episodes.map((ep) => {
                  const segs = Array.isArray(ep.segments) ? ep.segments : []
                  const preview = segs[0]?.text ?? ""
                  const dists = distributions.get(ep.id) ?? []
                  return (
                    <li key={ep.id}>
                      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 transition-colors hover:border-slate-700">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-balance text-base font-semibold text-slate-100">{ep.title}</h3>
                            <SourceBadge source={ep.source} />
                          </div>
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                            <AudioLines className="size-3" aria-hidden="true" />~{ep.estimated_minutes ?? "?"} min
                          </span>
                        </div>
                        {ep.description && <p className="text-pretty text-sm text-slate-400">{ep.description}</p>}
                        {preview && (
                          <p className="line-clamp-2 rounded-lg border border-slate-800 bg-slate-950/50 p-2.5 text-xs text-slate-400">
                            {preview}
                          </p>
                        )}
                        {ep.audio_url && (
                          <audio controls preload="none" src={ep.audio_url} className="h-10 w-full">
                            <a href={ep.audio_url}>Download audio</a>
                          </audio>
                        )}
                        {ep.video_url && (
                          <video controls preload="none" src={ep.video_url} className="max-h-72 w-full rounded-lg bg-black" />
                        )}
                        {(ep.audio_url || ep.video_url) && (
                          <div className="flex flex-wrap items-center gap-2">
                            <DistributeButton episodeId={ep.id} />
                            {dists.map((d) =>
                              d.url ? (
                                <a
                                  key={d.id}
                                  href={d.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium underline-offset-2 hover:underline ${DIST_CHIP[d.status] ?? DIST_CHIP.pending}`}
                                  title={d.error ?? undefined}
                                >
                                  {d.channel}: {d.status}
                                </a>
                              ) : (
                                <span
                                  key={d.id}
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${DIST_CHIP[d.status] ?? DIST_CHIP.pending}`}
                                  title={d.error ?? undefined}
                                >
                                  {d.channel}: {d.status}
                                </span>
                              ),
                            )}
                          </div>
                        )}
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800 pt-3 text-xs text-slate-500">
                          {ep.project_name && (
                            <span className="inline-flex items-center gap-1">
                              <FolderOpen className="size-3.5" aria-hidden="true" />
                              {ep.project_name}
                            </span>
                          )}
                          {ep.jurisdiction && (
                            <span className="inline-flex items-center gap-1">
                              <Gavel className="size-3.5" aria-hidden="true" />
                              {ep.jurisdiction}
                              {ep.week_of ? ` · week of ${fmtWeekOf(ep.week_of)}` : ""}
                            </span>
                          )}
                          <span className="inline-flex items-center gap-1">
                            <MessageSquare className="size-3.5" aria-hidden="true" />
                            {segs.length} segment{segs.length === 1 ? "" : "s"}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays className="size-3.5" aria-hidden="true" />
                            {fmtDate(ep.created_at)}
                          </span>
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
