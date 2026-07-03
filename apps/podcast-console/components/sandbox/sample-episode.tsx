"use client"

import { useRef } from "react"
import { PlayCircle, Upload, Trash2, Film, Sparkles, Download } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useVideoPlaylist, type VideoKind } from "@/lib/video-playlist"

const kindBadge: Record<VideoKind, { label: string; className: string }> = {
  default: { label: "Sample", className: "border-emerald-700/60 text-emerald-400" },
  uploaded: { label: "Uploaded", className: "border-sky-700/60 text-sky-400" },
  generated: { label: "Generated", className: "border-amber-700/60 text-amber-400" },
}

export function SampleEpisode() {
  const { videos, selected, selectedId, select, addVideo, removeVideo } = useVideoPlaylist()
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    if (!files) return
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("video/")) continue
      const url = URL.createObjectURL(file)
      addVideo({ label: file.name.replace(/\.[^.]+$/, ""), url, kind: "uploaded", isObjectUrl: true })
    }
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  async function downloadVideo(label: string, url: string) {
    const fileName = `${label.replace(/[^a-z0-9-_]+/gi, "-").replace(/^-+|-+$/g, "") || "episode"}.mp4`
    // Fetch the bytes into a blob first. Triggering a download directly from a
    // same-origin path (e.g. /sample-episode.mp4) gets blocked in the preview
    // proxy ("unauthorized"); downloading from an in-memory object URL avoids that.
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Download failed (${res.status})`)
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = objectUrl
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      a.remove()
      // Revoke after a tick so the browser has started the download.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
    } catch {
      // Last-resort fallback: open in a new tab so the user can save manually.
      window.open(url, "_blank", "noopener,noreferrer")
    }
  }

  return (
    <Card className="border-slate-800 bg-slate-900/60">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-col gap-1">
            <CardTitle className="flex items-center gap-2 text-slate-50">
              <PlayCircle className="size-5 text-emerald-400" aria-hidden="true" />
              Episode Player
            </CardTitle>
            <CardDescription className="text-slate-400">
              Load videos from your device or play episodes you generate. Switch between them or remove any.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              multiple
              className="sr-only"
              aria-label="Upload video files"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              <Upload data-icon="inline-start" />
              Load video
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Active player */}
        <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
          {selected ? (
            <video
              key={selected.id}
              controls
              playsInline
              preload="metadata"
              className="aspect-video w-full"
              poster={selected.kind === "default" ? "/episode-bg.png" : undefined}
            >
              <source src={selected.url} type="video/mp4" />
              {"Your browser does not support the video tag."}
            </video>
          ) : (
            <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 text-slate-500">
              <Film className="size-8" aria-hidden="true" />
              <p className="text-sm">No video loaded. Use “Load video” to add one.</p>
            </div>
          )}
        </div>

        {selected && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-200">{selected.label}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadVideo(selected.label, selected.url)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-slate-50"
            >
              <Download data-icon="inline-start" />
              Download
            </Button>
          </div>
        )}

        {/* Playlist */}
        {videos.length > 0 && (
          <ul className="flex flex-col gap-2">
            {videos.map((v) => {
              const active = v.id === selectedId
              const badge = kindBadge[v.kind]
              return (
                <li
                  key={v.id}
                  className={cn(
                    "flex items-center gap-3 rounded-lg border p-2.5 transition-colors",
                    active
                      ? "border-emerald-500/50 bg-emerald-500/10"
                      : "border-slate-800 bg-slate-950/40 hover:border-slate-700",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => select(v.id)}
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    aria-current={active ? "true" : undefined}
                  >
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-md",
                        active ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800 text-slate-400",
                      )}
                    >
                      {v.kind === "generated" ? (
                        <Sparkles className="size-4" aria-hidden="true" />
                      ) : (
                        <Film className="size-4" aria-hidden="true" />
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-slate-100">{v.label}</span>
                    </span>
                    <Badge variant="outline" className={cn("shrink-0", badge.className)}>
                      {badge.label}
                    </Badge>
                  </button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => downloadVideo(v.label, v.url)}
                    aria-label={`Download ${v.label}`}
                    className="size-8 shrink-0 text-slate-500 hover:bg-emerald-500/10 hover:text-emerald-400"
                  >
                    <Download className="size-4" aria-hidden="true" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeVideo(v.id)}
                    aria-label={`Remove ${v.label}`}
                    className="size-8 shrink-0 text-slate-500 hover:bg-red-500/10 hover:text-red-400"
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
