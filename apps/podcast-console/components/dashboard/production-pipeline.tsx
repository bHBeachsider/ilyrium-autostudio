"use client"

import { useEffect, useState } from "react"
import {
  FileSearch,
  FileText,
  Mic,
  Loader2,
  CheckCircle2,
  Radio,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const stages = [
  { label: "Sources", icon: FileSearch },
  { label: "Script", icon: FileText },
  { label: "Record", icon: Mic },
  { label: "Processing", icon: Loader2 },
  { label: "Published", icon: Radio },
]

// Processing is the active stage (index 3)
const ACTIVE_INDEX = 3
const TOTAL_SECONDS = 18 * 60 + 57 // 18:57

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function ProductionPipeline() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [position, setPosition] = useState(0)

  useEffect(() => {
    if (!isPlaying) return
    const id = setInterval(() => {
      setPosition((prev) => (prev >= TOTAL_SECONDS ? 0 : prev + 1))
    }, 1000)
    return () => clearInterval(id)
  }, [isPlaying])

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle className="text-slate-50">Active Production: Week of 2026-06-08</CardTitle>
          <CardDescription className="text-slate-400">
            Episode 142 — &ldquo;Coastal Resilience &amp; County Budgets&rdquo;
          </CardDescription>
        </div>
        <Badge className="shrink-0 gap-1.5 border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
          <span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />
          Running
        </Badge>
      </CardHeader>

      <CardContent className="flex flex-col gap-8">
        {/* Stepper */}
        <ol className="flex items-center justify-between">
          {stages.map((stage, index) => {
            const isComplete = index < ACTIVE_INDEX
            const isActive = index === ACTIVE_INDEX
            const Icon = stage.icon
            return (
              <li key={stage.label} className="flex flex-1 flex-col items-center gap-2 last:flex-none">
                <div className="flex w-full items-center">
                  {index !== 0 && (
                    <div
                      className={cn(
                        "h-0.5 flex-1",
                        index <= ACTIVE_INDEX ? "bg-emerald-500" : "bg-slate-800",
                      )}
                    />
                  )}
                  <span
                    className={cn(
                      "flex size-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                      isComplete && "border-emerald-500 bg-emerald-500 text-slate-950",
                      isActive && "border-emerald-500 bg-emerald-500/10 text-emerald-400",
                      !isComplete && !isActive && "border-slate-700 bg-slate-900 text-slate-500",
                    )}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="size-5" aria-hidden="true" />
                    ) : (
                      <Icon className={cn("size-5", isActive && "animate-spin")} aria-hidden="true" />
                    )}
                  </span>
                  {index !== stages.length - 1 && (
                    <div className={cn("h-0.5 flex-1", index < ACTIVE_INDEX ? "bg-emerald-500" : "bg-slate-800")} />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium",
                    isActive ? "text-emerald-400" : isComplete ? "text-slate-300" : "text-slate-500",
                  )}
                >
                  {stage.label}
                </span>
              </li>
            )
          })}
        </ol>

        {/* Processing progress */}
        <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 text-slate-300">
              <Loader2 className="size-4 animate-spin text-emerald-400" aria-hidden="true" />
              Processing audio via GitHub Actions
            </span>
            <span className="font-mono text-slate-400">68%</span>
          </div>
          <Progress value={68} className="[&_[data-slot=progress-indicator]]:bg-emerald-500" />
          <p className="text-xs text-slate-500">Normalizing levels &amp; generating transcript — ETA 3 min</p>
        </div>

        {/* Audio player */}
        <div className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex items-center gap-4">
            <button
              type="button"
              aria-label="Skip back 15 seconds"
              onClick={() => setPosition((p) => Math.max(0, p - 15))}
              className="text-slate-400 transition-colors hover:text-slate-100"
            >
              <SkipBack className="size-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label={isPlaying ? "Pause" : "Play"}
              onClick={() => setIsPlaying((p) => !p)}
              className="flex size-11 items-center justify-center rounded-full bg-emerald-500 text-slate-950 transition-colors hover:bg-emerald-400"
            >
              {isPlaying ? (
                <Pause className="size-5 fill-current" aria-hidden="true" />
              ) : (
                <Play className="size-5 translate-x-0.5 fill-current" aria-hidden="true" />
              )}
            </button>
            <button
              type="button"
              aria-label="Skip forward 15 seconds"
              onClick={() => setPosition((p) => Math.min(TOTAL_SECONDS, p + 15))}
              className="text-slate-400 transition-colors hover:text-slate-100"
            >
              <SkipForward className="size-5" aria-hidden="true" />
            </button>

            <div className="flex flex-1 items-center gap-3">
              <span className="w-10 text-right font-mono text-xs text-slate-400">{formatTime(position)}</span>
              <Slider
                value={[position]}
                max={TOTAL_SECONDS}
                step={1}
                onValueChange={(v) => setPosition(Array.isArray(v) ? v[0] : v)}
                aria-label="Seek"
                className="flex-1"
              />
              <span className="w-10 font-mono text-xs text-slate-400">{formatTime(TOTAL_SECONDS)}</span>
            </div>

            <Volume2 className="hidden size-5 text-slate-400 sm:block" aria-hidden="true" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
