import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { MetricCards } from "@/components/dashboard/metric-cards"
import { ProductionPipeline } from "@/components/dashboard/production-pipeline"
import { SystemHealth } from "@/components/dashboard/system-health"
import { RecentEpisodes } from "@/components/dashboard/recent-episodes"

export default function Page() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-col gap-1">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Production Dashboard</h1>
              <p className="text-sm text-slate-400">
                Monitor your pipeline, audience pulse, and distribution health at a glance.
              </p>
            </div>

            <MetricCards />
            <ProductionPipeline />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="min-w-0 lg:col-span-1">
                <SystemHealth />
              </div>
              <div className="min-w-0 lg:col-span-2">
                <RecentEpisodes />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
