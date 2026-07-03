"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Mic,
  LayoutDashboard,
  Archive,
  ListChecks,
  Workflow,
  BarChart3,
  DollarSign,
  Settings,
  FlaskConical,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Idea Sandbox", icon: FlaskConical, href: "/sandbox" },
  { label: "Review Queue", icon: ListChecks, href: "/review" },
  // Not built yet in this export — shown as disabled "Soon" rather than dead links.
  { label: "Episode Archive", icon: Archive, href: "/episode-archive" },
  { label: "Production Pipeline", icon: Workflow, href: "#", soon: true },
  { label: "Analytics", icon: BarChart3, href: "#", soon: true },
  { label: "Monetization", icon: DollarSign, href: "#", soon: true },
  { label: "Settings", icon: Settings, href: "#", soon: true },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
      <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500 text-slate-950">
          <Mic className="size-5" aria-hidden="true" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-slate-100">Palm Beach County</span>
          <span className="text-xs text-slate-400">Weekly Studio</span>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-4" aria-label="Main navigation">
        {navItems.map(({ label, icon: Icon, href, soon }) => {
          const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href) && href !== "#"
          if (soon) {
            return (
              <div
                key={label}
                title={`${label} — coming soon`}
                aria-disabled="true"
                className="group flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600"
              >
                <Icon className="size-4.5 shrink-0 text-slate-700" aria-hidden="true" />
                {label}
                <span className="ml-auto rounded-full border border-slate-800 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                  Soon
                </span>
              </div>
            )
          }
          return (
            <Link
              key={label}
              href={href}
              aria-current={isActive ? "page" : undefined}
              title={label}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100",
              )}
            >
              <Icon
                className={cn(
                  "size-4.5 shrink-0 transition-colors",
                  isActive ? "text-emerald-400" : "text-slate-500 group-hover:text-slate-300",
                )}
                aria-hidden="true"
              />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-slate-800 p-4">
        <div className="rounded-lg bg-slate-900 p-3">
          <p className="text-xs font-medium text-slate-300">Storage</p>
          <p className="mt-1 text-xs text-slate-500">68% of 50 GB used</p>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full w-[68%] rounded-full bg-emerald-500" />
          </div>
        </div>
      </div>
    </aside>
  )
}
