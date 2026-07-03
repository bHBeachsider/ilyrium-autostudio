"use client"

import { useState } from "react"
import { Play, Pause, Film, Sparkles, Eye, Clock, TrendingUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const clips = [
  { id: "1", title: "Commission Vote — Highlight", duration: "0:42", source: "WPTV", retention: "71%" },
  { id: "2", title: "Beach Restoration Recap", duration: "1:08", source: "Internal", retention: "64%" },
  { id: "3", title: "Mayor Interview — Cold Open", duration: "0:55", source: "YouTube", retention: "58%" },
]

const videoStats = [
  { label: "Video signals (7D)", value: "312", icon: Film },
  { label: "Avg. watch time", value: "0:47", icon: Clock },
  { label: "Clip CTR", value: "6.8%", icon: TrendingUp },
]

export function VideoDimension() {
  const [playing, setPlaying] = useState(false)
  const [active, setActive] = useState(clips[0])

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <Film className="size-4.5" aria-hidden="true" />
          </span>
          <div>
            <CardTitle className="text-slate-50">Video Dimension</CardTitle>
            <CardDescription className="text-slate-400">
              Preview and generate video clips from ingested sources.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {/* Preview surface */}
        <div className="relative aspect-video overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? "Pause preview" : "Play preview"}
              className="flex size-16 items-center justify-center rounded-full bg-emerald-500 text-slate-950 transition-transform hover:scale-105"
            >
              {playing ? (
                <Pause className="size-7" aria-hidden="true" />
              ) : (
                <Play className="size-7 translate-x-0.5" aria-hidden="true" />
              )}
            </button>
            <p className="text-sm font-medium text-slate-300">{active.title}</p>
          </div>
          <div className="absolute bottom-0 left-0 right-0 flex items-center gap-3 bg-gradient-to-t from-slate-950 to-transparent p-4">
            <span className="text-xs text-slate-400">{active.source}</span>
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-700">
              <div className={cn("h-full rounded-full bg-emerald-500 transition-all", playing ? "w-1/3" : "w-0")} />
            </div>
            <span className="text-xs tabular-nums text-slate-400">{active.duration}</span>
          </div>
          <Badge className="absolute left-3 top-3 gap-1 bg-emerald-500 text-slate-950">
            <Eye className="size-3" aria-hidden="true" />
            {active.retention} retention
          </Badge>
        </div>

        {/* Generate */}
        <Button variant="outline" className="border-slate-700 bg-slate-800/60 text-slate-100 hover:bg-slate-800">
          <Sparkles data-icon="inline-start" />
          Generate clip from latest signal
        </Button>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2">
          {videoStats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <Icon className="size-4 text-emerald-400" aria-hidden="true" />
              <p className="mt-2 text-lg font-semibold text-slate-50">{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>

        {/* Clip list */}
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Generated clips</p>
          <ul className="flex flex-col gap-1.5">
            {clips.map((clip) => (
              <li key={clip.id}>
                <button
                  type="button"
                  onClick={() => {
                    setActive(clip)
                    setPlaying(false)
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors",
                    active.id === clip.id
                      ? "border-emerald-500/40 bg-emerald-500/10"
                      : "border-slate-800 bg-slate-950/40 hover:bg-slate-800/60",
                  )}
                >
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-slate-800 text-slate-300">
                    <Film className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-100">{clip.title}</p>
                    <p className="text-xs text-slate-500">
                      {clip.source} · {clip.duration}
                    </p>
                  </div>
                  <span className="text-xs font-medium text-emerald-400">{clip.retention}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
