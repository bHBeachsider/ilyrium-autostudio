"use client"

import { useState } from "react"
import {
  Plus,
  Rss,
  MonitorPlay,
  Podcast,
  AtSign,
  Newspaper,
  Video,
  Radio,
  Pause,
  Trash2,
  Sparkles,
  Search,
  Loader2,
  ArrowRightCircle,
  ExternalLink,
  AlertTriangle,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Field, FieldLabel } from "@/components/ui/field"
import { cn } from "@/lib/utils"

type SourceType = "rss" | "youtube" | "podcast" | "social" | "news" | "video"
type SourceStatus = "live" | "ingesting" | "paused"

type DataSource = {
  id: string
  name: string
  type: SourceType
  status: SourceStatus
  signals: string
  video: boolean
}

type IngestedItem = {
  title: string
  summary: string
  angle: string
  source?: string
}

const typeMeta: Record<SourceType, { label: string; icon: typeof Rss }> = {
  rss: { label: "RSS Feed", icon: Rss },
  youtube: { label: "YouTube", icon: MonitorPlay },
  podcast: { label: "Podcast", icon: Podcast },
  social: { label: "Social", icon: AtSign },
  news: { label: "News Scraper", icon: Newspaper },
  video: { label: "Video Feed", icon: Video },
}

const statusMeta: Record<SourceStatus, { label: string; dot: string; text: string }> = {
  live: { label: "Live", dot: "bg-emerald-400", text: "text-emerald-400" },
  ingesting: { label: "Ingesting", dot: "bg-amber-400 animate-pulse", text: "text-amber-400" },
  paused: { label: "Paused", dot: "bg-slate-500", text: "text-slate-400" },
}

const initialSources: DataSource[] = [
  { id: "1", name: "Palm Beach Post — Local", type: "news", status: "live", signals: "142/day", video: false },
  { id: "2", name: "WPTV News Channel 5", type: "youtube", status: "live", signals: "38/day", video: true },
  { id: "3", name: "County Commission Audio", type: "podcast", status: "ingesting", signals: "6/day", video: false },
  { id: "4", name: "@PBCGov", type: "social", status: "paused", signals: "0/day", video: false },
]

export function DataSourcePipeline({
  onIngest,
}: {
  onIngest?: (item: { title: string; summary: string }) => void
}) {
  const [sources, setSources] = useState<DataSource[]>(initialSources)
  const [name, setName] = useState("")
  const [endpoint, setEndpoint] = useState("")
  const [type, setType] = useState<SourceType>("rss")
  const [video, setVideo] = useState(false)

  // Live ingestion (Perplexity)
  const [query, setQuery] = useState("")
  const [discovering, setDiscovering] = useState(false)
  const [results, setResults] = useState<IngestedItem[]>([])
  const [citations, setCitations] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pulled, setPulled] = useState<Set<string>>(new Set())

  function addSource() {
    if (!name.trim() || !endpoint.trim()) return
    setSources((prev) => [
      {
        id: crypto.randomUUID(),
        name: name.trim(),
        type,
        status: "ingesting",
        signals: "—",
        video,
      },
      ...prev,
    ])
    setName("")
    setEndpoint("")
    setVideo(false)
    setType("rss")
  }

  function removeSource(id: string) {
    setSources((prev) => prev.filter((s) => s.id !== id))
  }

  async function runDiscovery() {
    if (!query.trim() || discovering) return
    setDiscovering(true)
    setError(null)
    setResults([])
    setCitations([])
    setPulled(new Set())
    try {
      const res = await fetch("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: query.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data?.error ?? "Ingestion failed.")
        return
      }
      setResults(Array.isArray(data.items) ? data.items : [])
      setCitations(Array.isArray(data.citations) ? data.citations : [])
    } catch {
      setError("Could not reach the ingestion service.")
    } finally {
      setDiscovering(false)
    }
  }

  function pullToPodcast(item: IngestedItem) {
    onIngest?.({ title: item.title, summary: `${item.summary} — ${item.angle}` })
    setPulled((prev) => new Set(prev).add(item.title))
  }

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <Radio className="size-4.5" aria-hidden="true" />
          </span>
          <div>
            <CardTitle className="text-slate-50">Media Ingestion Spine</CardTitle>
            <CardDescription className="text-slate-400">
              Discover, capture, and route content into the podcast production pipeline.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {/* Live discovery (Perplexity) */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-4">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="size-4 text-emerald-400" aria-hidden="true" />
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-400/90">
              Live discovery · Perplexity
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Input
              placeholder="Ingest a topic, e.g. 'Palm Beach County housing'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runDiscovery()
              }}
              className="flex-1"
            />
            <Button
              onClick={runDiscovery}
              disabled={!query.trim() || discovering}
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              {discovering ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Search data-icon="inline-start" />
              )}
              {discovering ? "Discovering…" : "Discover"}
            </Button>
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {discovering && (
            <ul className="mt-3 flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <li key={i} className="h-16 animate-pulse rounded-lg border border-slate-800 bg-slate-900/60" />
              ))}
            </ul>
          )}

          {!discovering && results.length > 0 && (
            <div className="mt-3 flex flex-col gap-2">
              {results.map((item) => {
                const isPulled = pulled.has(item.title)
                return (
                  <div
                    key={item.title}
                    className="flex items-start gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-100">{item.title}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{item.summary}</p>
                      <p className="mt-1 text-xs text-emerald-400/80">{item.angle}</p>
                      {item.source && (
                        <p className="mt-1 text-[11px] uppercase tracking-wide text-slate-600">{item.source}</p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => pullToPodcast(item)}
                      disabled={isPulled}
                      className={cn(
                        "h-8 shrink-0",
                        isPulled
                          ? "text-emerald-500"
                          : "text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300",
                      )}
                    >
                      <ArrowRightCircle data-icon="inline-start" />
                      {isPulled ? "Added" : "Pull to podcast"}
                    </Button>
                  </div>
                )
              })}

              {citations.length > 0 && (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="text-[11px] uppercase tracking-wide text-slate-600">Sources</span>
                  {citations.slice(0, 5).map((c, i) => (
                    <a
                      key={c}
                      href={c}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-emerald-400"
                    >
                      <ExternalLink className="size-3" aria-hidden="true" />[{i + 1}]
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Add source form */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">Add standing data source</p>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="src-name">Source name</FieldLabel>
                <Input
                  id="src-name"
                  placeholder="e.g. Sun Sentinel — Politics"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="src-endpoint">Feed URL / handle</FieldLabel>
                <Input
                  id="src-endpoint"
                  placeholder="https:// or @handle"
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                />
              </Field>
            </div>

            <Field>
              <FieldLabel>Source type</FieldLabel>
              <ToggleGroup
                value={[type]}
                onValueChange={(value) => {
                  const next = value[0] as SourceType | undefined
                  if (next) setType(next)
                }}
                className="flex-wrap justify-start gap-2"
              >
                {(Object.keys(typeMeta) as SourceType[]).map((key) => {
                  const Icon = typeMeta[key].icon
                  return (
                    <ToggleGroupItem
                      key={key}
                      value={key}
                      className="gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 text-slate-300 data-[pressed]:border-emerald-500/40 data-[pressed]:bg-emerald-500/15 data-[pressed]:text-emerald-400"
                    >
                      <Icon className="size-4" aria-hidden="true" />
                      {typeMeta[key].label}
                    </ToggleGroupItem>
                  )
                })}
              </ToggleGroup>
            </Field>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Switch id="video-signal" checked={video} onCheckedChange={setVideo} />
                <Label htmlFor="video-signal" className="text-sm text-slate-300">
                  Capture video dimension
                </Label>
              </div>
              <Button
                onClick={addSource}
                disabled={!name.trim() || !endpoint.trim()}
                className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
              >
                <Plus data-icon="inline-start" />
                Connect source
              </Button>
            </div>
          </div>
        </div>

        {/* Connected sources */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Connected sources ({sources.length})
            </p>
          </div>
          <ul className="flex flex-col gap-2">
            {sources.map((source) => {
              const Icon = typeMeta[source.type].icon
              const status = statusMeta[source.status]
              return (
                <li
                  key={source.id}
                  className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-300">
                    <Icon className="size-4.5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium text-slate-100">{source.name}</p>
                      {source.video && (
                        <Badge variant="secondary" className="gap-1 bg-slate-800 text-slate-300">
                          <Video className="size-3" aria-hidden="true" />
                          Video
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-slate-500">
                      {typeMeta[source.type].label} · {source.signals}
                    </p>
                  </div>
                  <span className={cn("flex items-center gap-1.5 text-xs font-medium", status.text)}>
                    <span className={cn("size-2 rounded-full", status.dot)} />
                    {status.label}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeSource(source.id)}
                    aria-label={`Remove ${source.name}`}
                    className="text-slate-500 hover:bg-slate-800 hover:text-red-400"
                  >
                    {source.status === "paused" ? (
                      <Trash2 className="size-4" aria-hidden="true" />
                    ) : (
                      <Pause className="size-4" aria-hidden="true" />
                    )}
                  </Button>
                </li>
              )
            })}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
