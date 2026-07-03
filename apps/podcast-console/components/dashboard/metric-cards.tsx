import { Download, Users, Gauge, TrendingUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const metrics = [
  {
    label: "Total Downloads (7D)",
    value: "1,236",
    trend: "+12% vs last week",
    icon: Download,
  },
  {
    label: "New Subscribers",
    value: "184",
    trend: "+8.4% vs last week",
    icon: Users,
  },
  {
    label: "Latest Episode Pacing",
    value: "327 / day",
    trend: "+19% vs avg.",
    icon: Gauge,
  },
]

export function MetricCards() {
  return (
    <section aria-label="High-level analytics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {metrics.map(({ label, value, trend, icon: Icon }) => (
        <Card key={label} className="border-slate-800 bg-slate-900">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-slate-400">{label}</CardTitle>
            <span className="flex size-9 items-center justify-center rounded-lg bg-slate-800 text-emerald-400">
              <Icon className="size-4.5" aria-hidden="true" />
            </span>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold tracking-tight text-slate-50">{value}</p>
            <p className="mt-2 flex items-center gap-1 text-xs font-medium text-emerald-400">
              <TrendingUp className="size-3.5" aria-hidden="true" />
              {trend}
            </p>
          </CardContent>
        </Card>
      ))}
    </section>
  )
}
