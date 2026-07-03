import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { ReviewQueue } from "@/components/review/review-queue"
import { dbReady } from "@/lib/db"
import { Database, ListChecks } from "lucide-react"

export const dynamic = "force-dynamic"

export default function ReviewPage() {
  const configured = dbReady()
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header section="Studio" page="Review Queue" />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                  <ListChecks className="size-4.5" aria-hidden="true" />
                </span>
                <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Review Queue</h1>
              </div>
              <p className="text-sm text-slate-400">
                Agent-proposed episode ideas. Nothing is produced or published without an approval here.
              </p>
            </div>
            {!configured ? (
              <div className="flex flex-col items-start gap-2 rounded-xl border border-amber-700/40 bg-amber-500/5 p-5">
                <span className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <Database className="size-4" aria-hidden="true" />
                  Database not connected
                </span>
                <p className="max-w-prose text-sm text-slate-400">
                  The review queue needs <code className="rounded bg-slate-800 px-1 py-0.5 text-slate-200">DATABASE_URL</code> in{" "}
                  <code className="rounded bg-slate-800 px-1 py-0.5 text-slate-200">apps/podcast-console/.env.local</code>.
                </p>
              </div>
            ) : (
              <ReviewQueue />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
