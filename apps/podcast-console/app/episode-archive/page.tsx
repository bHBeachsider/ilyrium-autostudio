import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { dbReady, ensureSchema, requireSql, type EpisodeRow } from "@/lib/db"
import { Archive, AudioLines, CalendarDays, FolderOpen, MessageSquare, Database } from "lucide-react"

// Always read fresh from the DB.
export const dynamic = "force-dynamic"

async function loadEpisodes(): Promise<EpisodeRow[]> {
  if (!dbReady()) return []
  try {
    const sql = requireSql()
    await ensureSchema()
    const rows = await sql`SELECT * FROM podcast_episodes ORDER BY created_at DESC`
    return rows as unknown as EpisodeRow[]
  } catch {
    return []
  }
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })
}

export default async function EpisodeArchivePage() {
  const configured = dbReady()
  const episodes = await loadEpisodes()

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header section="Studio" page="Episode Archive" />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                  <Archive className="size-4.5" aria-hidden="true" />
                </span>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Episode Archive</h1>
              </div>
              <p className="text-sm text-slate-400">
                Every generated episode, persisted to your studio database.
              </p>
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
                  return (
                    <li key={ep.id}>
                      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 transition-colors hover:border-slate-700">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <h3 className="text-balance text-base font-semibold text-slate-100">{ep.title}</h3>
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
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800 pt-3 text-xs text-slate-500">
                          {ep.project_name && (
                            <span className="inline-flex items-center gap-1">
                              <FolderOpen className="size-3.5" aria-hidden="true" />
                              {ep.project_name}
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
