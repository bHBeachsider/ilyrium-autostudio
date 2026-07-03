import { Lightbulb, FlaskConical, Rocket } from "lucide-react"

export type Stage = "draft" | "testing" | "shipped"

export type EpisodeSegment = {
  speaker: "Host A" | "Host B"
  text: string
}

export type GeneratedEpisode = {
  title: string
  description: string
  estimatedMinutes: number
  segments: EpisodeSegment[]
}

export type Idea = {
  id: string
  title: string
  summary: string
  stage: Stage
  sources: number
  video: boolean
}

export const stageMeta: Record<
  Stage,
  { label: string; icon: typeof Lightbulb; className: string }
> = {
  draft: { label: "Draft", icon: Lightbulb, className: "bg-slate-800 text-slate-300" },
  testing: { label: "Sandboxing", icon: FlaskConical, className: "bg-amber-500/15 text-amber-400" },
  shipped: { label: "Shipped", icon: Rocket, className: "bg-emerald-500/15 text-emerald-400" },
}

export const initialIdeas: Idea[] = [
  {
    id: "seed-1",
    title: "Daily 60-second county brief",
    summary: "Auto-generate a short audio + video recap from top local signals each morning.",
    stage: "testing",
    sources: 3,
    video: true,
  },
  {
    id: "seed-2",
    title: "Commission meeting tracker",
    summary: "Cluster commission-related signals and surface vote outcomes as episode segments.",
    stage: "draft",
    sources: 2,
    video: false,
  },
  {
    id: "seed-3",
    title: "Hurricane season explainer series",
    summary: "Seasonal explainer reels pulled from NWS feeds and local video sources.",
    stage: "shipped",
    sources: 4,
    video: true,
  },
]
