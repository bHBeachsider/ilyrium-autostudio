"use client"

import { useState, useRef, useEffect } from "react"
import {
  Wand2,
  Loader2,
  Mic,
  Film,
  AudioLines,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  Sparkles,
  Download,
  Image as ImageIcon,
  MessageSquarePlus,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import type { Idea, GeneratedEpisode } from "@/lib/sandbox-types"
import { useVideoPlaylist } from "@/lib/video-playlist"
import { useProjects } from "@/lib/projects"

type RenderStage = "idle" | "voicing" | "illustrating" | "composing" | "done"

const renderSteps: { key: Exclude<RenderStage, "idle">; label: string; icon: typeof Mic }[] = [
  { key: "voicing", label: "Synthesizing host voices (TTS)", icon: Mic },
  { key: "illustrating", label: "Generating scene visuals", icon: ImageIcon },
  { key: "composing", label: "Composing video podcast", icon: Film },
  { key: "done", label: "Video episode ready", icon: CheckCircle2 },
]

type SceneImage = { caption: string; blob: Blob; url: string }

const DURATIONS = [5, 10, 15] as const

export function EpisodeGenerator({ ideas }: { ideas: Idea[] }) {
  const { addVideo } = useVideoPlaylist()
  const { generateNonce, activeProject } = useProjects()
  const [topic, setTopic] = useState("")
  const [feedback, setFeedback] = useState("")
  const [targetMinutes, setTargetMinutes] = useState<number>(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [episode, setEpisode] = useState<GeneratedEpisode | null>(null)

  const [renderStage, setRenderStage] = useState<RenderStage>("idle")
  const [renderProgress, setRenderProgress] = useState(0)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [synthInfo, setSynthInfo] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [renderingVideo, setRenderingVideo] = useState(false)
  const [sceneImages, setSceneImages] = useState<SceneImage[]>([])
  const [visualStyle, setVisualStyle] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const audioUrlRef = useRef<string | null>(null)
  const audioBlobRef = useRef<Blob | null>(null)
  const videoUrlRef = useRef<string | null>(null)
  const sceneImagesRef = useRef<SceneImage[]>([])
  const sceneWeightsRef = useRef<number[]>([])
  // Remembers the inputs behind the current episode so "Regenerate with feedback" can
  // re-run the whole pipeline with the same topic/sources plus the producer's notes.
  const lastInputsRef = useRef<{ topic: string; summary?: string; sources?: string[] } | null>(null)

  // Entry button ("New podcast"): scroll the generator into view and focus the topic input.
  useEffect(() => {
    if (generateNonce === 0) return
    document.getElementById("episode-generator")?.scrollIntoView({ behavior: "smooth", block: "start" })
    const id = window.setTimeout(() => document.getElementById("episode-topic")?.focus(), 350)
    return () => window.clearTimeout(id)
  }, [generateNonce])

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current)
      if (videoUrlRef.current) URL.revokeObjectURL(videoUrlRef.current)
      sceneImagesRef.current.forEach((img) => URL.revokeObjectURL(img.url))
    }
  }, [])

  async function generate(
    topicValue: string,
    summary?: string,
    sources?: string[],
    feedbackNote?: string,
  ): Promise<GeneratedEpisode | null> {
    const t = topicValue.trim()
    if (!t || loading) return null
    // Capture the current script before clearing so a revision can reference it.
    const previousScript = feedbackNote ? episode?.segments : undefined
    setLoading(true)
    setError(null)
    setEpisode(null)
    clearAudio()
    setRenderStage("idle")
    setRenderProgress(0)

    try {
      const res = await fetch("/api/generate-episode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: t, summary, sources, targetMinutes, feedback: feedbackNote, previousScript }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || "Generation failed.")
      const ep = data.episode as GeneratedEpisode
      setEpisode(ep)
      lastInputsRef.current = { topic: t, summary, sources }
      return ep
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
      return null
    } finally {
      setLoading(false)
    }
  }

  function clearAudio() {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    if (videoUrlRef.current) {
      URL.revokeObjectURL(videoUrlRef.current)
      videoUrlRef.current = null
    }
    audioBlobRef.current = null
    sceneImagesRef.current.forEach((img) => URL.revokeObjectURL(img.url))
    sceneImagesRef.current = []
    sceneWeightsRef.current = []
    setSceneImages([])
    setVisualStyle(null)
    setAudioUrl(null)
    setSynthInfo(null)
    setVideoUrl(null)
    setRenderingVideo(false)
  }

  // Real TTS synthesis via ElevenLabs (/api/synthesize), then assemble the video preview.
  async function startRender(ep: GeneratedEpisode | null = episode) {
    if (!ep) return
    if (intervalRef.current) clearInterval(intervalRef.current)
    clearAudio()
    setError(null)
    setRenderStage("voicing")
    setRenderProgress(6)

    // Climb progress while voices synthesize (one ElevenLabs call per host turn).
    let p = 6
    intervalRef.current = setInterval(() => {
      p = Math.min(92, p + 2)
      setRenderProgress(p)
    }, 500)

    try {
      const res = await fetch("/api/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments: ep.segments }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || "Synthesis failed.")
      }
      const synthesized = res.headers.get("X-Segments-Synthesized")
      const blob = await res.blob()
      audioBlobRef.current = blob

      const url = URL.createObjectURL(blob)
      audioUrlRef.current = url
      setAudioUrl(url)
      if (synthesized) setSynthInfo(`${synthesized} host turns voiced`)

      // Generate AI scene visuals that track the script (style chosen per episode).
      if (intervalRef.current) clearInterval(intervalRef.current)
      setRenderStage("illustrating")
      let q = 40
      intervalRef.current = setInterval(() => {
        q = Math.min(94, q + 2)
        setRenderProgress(q)
      }, 600)

      try {
        const imgRes = await fetch("/api/generate-images", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: ep.title,
            description: ep.description,
            segments: ep.segments,
          }),
        })
        if (imgRes.ok) {
          const data = (await imgRes.json()) as {
            visualStyle?: string
            images?: { caption: string; dataUrl: string }[]
            weights?: number[]
          }
          const imgs: SceneImage[] = await Promise.all(
            (data.images ?? []).map(async (im) => {
              const b = await (await fetch(im.dataUrl)).blob()
              return { caption: im.caption, blob: b, url: URL.createObjectURL(b) }
            }),
          )
          sceneImagesRef.current = imgs
          sceneWeightsRef.current = Array.isArray(data.weights) ? data.weights : []
          setSceneImages(imgs)
          if (data.visualStyle) setVisualStyle(data.visualStyle)
        }
      } catch {
        // Non-fatal: fall back to the branded waveform background at render time.
      }

      if (intervalRef.current) clearInterval(intervalRef.current)
      setRenderStage("composing")
      setRenderProgress(96)
      setRenderProgress(100)
      setRenderStage("done")
    } catch (err) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      setRenderStage("idle")
      setRenderProgress(0)
      setError(err instanceof Error ? err.message : "Synthesis failed.")
    }
  }

  // Real MP4 render via FFmpeg (/api/render-video): branded background + animated
  // waveform synced to the synthesized ElevenLabs audio.
  async function renderVideo(ep: GeneratedEpisode | null = episode) {
    if (!audioBlobRef.current || renderingVideo) return
    setRenderingVideo(true)
    setError(null)
    try {
      const form = new FormData()
      form.append("audio", audioBlobRef.current, "audio.mp3")
      sceneImagesRef.current.forEach((img, i) => {
        form.append("images", img.blob, `scene-${i}.png`)
      })
      if (sceneWeightsRef.current.length === sceneImagesRef.current.length && sceneWeightsRef.current.length > 0) {
        form.append("weights", JSON.stringify(sceneWeightsRef.current))
      }
      const res = await fetch("/api/render-video", { method: "POST", body: form })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || "Video render failed.")
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      videoUrlRef.current = url
      setVideoUrl(url)

      // Add the finished episode to the shared player playlist with its own
      // object URL so the player manages its lifecycle independently.
      addVideo({
        label: ep?.title ?? "Generated episode",
        url: URL.createObjectURL(blob),
        kind: "generated",
        isObjectUrl: true,
      })

      // Persist episode metadata to the Episode Archive (survives reload). Fire-and-forget;
      // if DATABASE_URL isn't set the route 503s and we skip it — playback is unaffected.
      if (ep) {
        fetch("/api/episodes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            projectId: activeProject?.id ?? null,
            projectName: activeProject?.name ?? null,
            title: ep.title,
            description: ep.description,
            estimatedMinutes: ep.estimatedMinutes,
            segments: ep.segments,
          }),
        }).catch(() => {})
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Video render failed.")
    } finally {
      setRenderingVideo(false)
    }
  }

  function reset() {
    if (intervalRef.current) clearInterval(intervalRef.current)
    clearAudio()
    setEpisode(null)
    setError(null)
    setFeedback("")
    setRenderStage("idle")
    setRenderProgress(0)
  }

  // Refine the finished episode: fold the producer's notes back into the script and
  // re-run the whole pipeline (script -> voices -> visuals -> MP4).
  async function regenerateWithFeedback() {
    const inputs = lastInputsRef.current
    const note = feedback.trim()
    if (!inputs || !note || loading || renderingVideo) return
    const ep = await generate(inputs.topic, inputs.summary, inputs.sources, note)
    if (!ep) return
    setFeedback("")
    await startRender(ep)
    await renderVideo(ep)
  }

  return (
    <Card id="episode-generator" className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <Wand2 className="size-4.5" aria-hidden="true" />
          </span>
          <div>
            <CardTitle className="text-slate-50">Curated Episode Generator</CardTitle>
            <CardDescription className="text-slate-400">
              NotebookLM-style two-host script from your sources, then synthesize real two-host audio.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {/* Topic input */}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="episode-topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") generate(topic)
            }}
            placeholder="Episode topic, e.g. 'Sea level rise and county infrastructure'"
            className="border-slate-700 bg-slate-950/60 text-slate-100 placeholder:text-slate-500"
            aria-label="Episode topic"
          />
          <Button
            onClick={() => generate(topic)}
            disabled={loading || !topic.trim()}
            className="shrink-0 bg-emerald-500 text-slate-950 hover:bg-emerald-400"
          >
            {loading ? <Loader2 data-icon="inline-start" className="animate-spin" /> : <Sparkles data-icon="inline-start" />}
            {loading ? "Generating…" : "Generate episode"}
          </Button>
        </div>

        {/* Target duration */}
        {!episode && !loading && (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Target length</p>
            <div className="flex gap-1.5">
              {DURATIONS.map((m) => {
                const active = targetMinutes === m
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setTargetMinutes(m)}
                    aria-pressed={active}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                      active
                        ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
                        : "border-slate-700 bg-slate-800/60 text-slate-300 hover:text-slate-100",
                    )}
                  >
                    {m} min
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Quick-pick from existing ideas */}
        {ideas.length > 0 && !episode && !loading && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Or curate from a sandbox idea</p>
            <div className="flex flex-wrap gap-2">
              {ideas.slice(0, 5).map((idea) => (
                <button
                  key={idea.id}
                  type="button"
                  onClick={() => {
                    setTopic(idea.title)
                    generate(idea.title, idea.summary)
                  }}
                  className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-emerald-500/50 hover:text-emerald-300"
                >
                  {idea.title}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-red-300">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-400">
            <Loader2 className="size-4 animate-spin text-emerald-400" aria-hidden="true" />
            Writing a two-host conversation with gpt-5-mini…
          </div>
        )}

        {/* Generated script */}
        {episode && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-balance text-lg font-semibold text-slate-50">{episode.title}</h3>
                <Badge variant="secondary" className="gap-1 bg-slate-800 text-slate-300">
                  <AudioLines className="size-3" aria-hidden="true" />~{episode.estimatedMinutes} min
                </Badge>
              </div>
              <p className="text-pretty text-sm text-slate-400">{episode.description}</p>
            </div>

            {/* Two-host transcript */}
            <div className="flex max-h-80 flex-col gap-3 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/30 p-4">
              {episode.segments.map((seg, i) => {
                const isA = seg.speaker === "Host A"
                return (
                  <div key={i} className="flex gap-3">
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                        isA ? "bg-emerald-500/15 text-emerald-400" : "bg-sky-500/15 text-sky-400",
                      )}
                      aria-hidden="true"
                    >
                      {isA ? "A" : "B"}
                    </span>
                    <div className="min-w-0">
                      <p className={cn("text-xs font-medium", isA ? "text-emerald-400" : "text-sky-400")}>
                        {seg.speaker}
                      </p>
                      <p className="text-sm leading-relaxed text-slate-200">{seg.text}</p>
                    </div>
                  </div>
                )
              })}
            </div>

            <Separator className="bg-slate-800" />

            {/* Render pipeline (mocked) */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Video podcast synthesis</p>
                <Badge variant="outline" className="border-emerald-700/60 text-emerald-400">
                  <AudioLines data-icon="inline-start" />
                  Voice + AI visuals
                </Badge>
              </div>

              {renderStage === "idle" ? (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    onClick={startRender}
                    className="flex-1 bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                  >
                    <Mic data-icon="inline-start" />
                    Synthesize video podcast
                  </Button>
                  <Button
                    variant="outline"
                    onClick={reset}
                    className="border-slate-700 bg-slate-800/60 text-slate-100 hover:bg-slate-800"
                  >
                    <RotateCcw data-icon="inline-start" />
                    Start over
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <Progress value={renderProgress} className="h-2 bg-slate-800" />
                  <ul className="flex flex-col gap-2">
                    {renderSteps.map(({ key, label, icon: Icon }) => {
                      const order = { voicing: 0, illustrating: 1, composing: 2, done: 3 }
                      const current = order[renderStage as Exclude<RenderStage, "idle">]
                      const stepIdx = order[key]
                      const active = stepIdx === current
                      const complete = stepIdx < current || renderStage === "done"
                      return (
                        <li key={key} className="flex items-center gap-2.5 text-sm">
                          <span
                            className={cn(
                              "flex size-7 items-center justify-center rounded-full",
                              complete
                                ? "bg-emerald-500/15 text-emerald-400"
                                : active
                                  ? "bg-amber-500/15 text-amber-400"
                                  : "bg-slate-800 text-slate-500",
                            )}
                          >
                            {active && key !== "done" ? (
                              <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                            ) : (
                              <Icon className="size-3.5" aria-hidden="true" />
                            )}
                          </span>
                          <span className={cn(complete ? "text-slate-200" : active ? "text-slate-100" : "text-slate-500")}>
                            {label}
                          </span>
                        </li>
                      )
                    })}
                  </ul>

                  {renderStage === "done" && (
                    <div className="flex flex-col gap-3">
                      {videoUrl ? (
                        <div className="flex flex-col gap-2 rounded-lg border border-emerald-700/40 bg-emerald-500/5 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-300">
                              <CheckCircle2 className="size-3.5" aria-hidden="true" />
                              MP4 rendered with FFmpeg
                            </span>
                            <a
                              href={videoUrl}
                              download={`${episode.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.mp4`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 hover:text-emerald-300"
                            >
                              <Download className="size-3.5" aria-hidden="true" />
                              Download MP4
                            </a>
                          </div>
                          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                          <video controls src={videoUrl} className="aspect-video w-full rounded-md bg-slate-950" />
                        </div>
                      ) : (
                        <div className="relative aspect-video overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
                          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                            <Film className="size-8 text-emerald-400" aria-hidden="true" />
                            <p className="px-4 text-center text-sm font-medium text-slate-300">{episode.title}</p>
                            <Button
                              onClick={renderVideo}
                              disabled={renderingVideo}
                              size="sm"
                              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                            >
                              {renderingVideo ? (
                                <Loader2 data-icon="inline-start" className="animate-spin" />
                              ) : (
                                <Film data-icon="inline-start" />
                              )}
                              {renderingVideo ? "Rendering MP4…" : "Render MP4 video"}
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* AI-generated scene visuals */}
                      {sceneImages.length > 0 && (
                        <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
                              <ImageIcon className="size-3.5 text-emerald-400" aria-hidden="true" />
                              {sceneImages.length} scene visuals generated
                            </span>
                            {visualStyle && (
                              <Badge variant="secondary" className="bg-slate-800 text-slate-300">
                                {visualStyle}
                              </Badge>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            {sceneImages.map((img, i) => (
                              <figure key={i} className="flex flex-col gap-1">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={img.url || "/placeholder.svg"}
                                  alt={img.caption}
                                  className="aspect-video w-full rounded-md border border-slate-800 object-cover"
                                />
                                <figcaption className="truncate text-[11px] text-slate-500">{img.caption}</figcaption>
                              </figure>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Real synthesized audio track */}
                      {audioUrl && (
                        <div className="flex flex-col gap-2 rounded-lg border border-emerald-700/40 bg-emerald-500/5 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-300">
                              <CheckCircle2 className="size-3.5" aria-hidden="true" />
                              {synthInfo ?? "Audio synthesized"}
                            </span>
                            <a
                              href={audioUrl}
                              download={`${episode.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.mp3`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 hover:text-emerald-300"
                            >
                              <Download className="size-3.5" aria-hidden="true" />
                              Download MP3
                            </a>
                          </div>
                          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                          <audio controls src={audioUrl} className="w-full">
                            Your browser does not support audio playback.
                          </audio>
                        </div>
                      )}

                      {/* Refine: producer notes -> regenerate the whole episode */}
                      <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                        <label
                          htmlFor="episode-feedback"
                          className="flex items-center gap-1.5 text-xs font-medium text-slate-300"
                        >
                          <MessageSquarePlus className="size-3.5 text-emerald-400" aria-hidden="true" />
                          Refine this episode
                        </label>
                        <Textarea
                          id="episode-feedback"
                          value={feedback}
                          onChange={(e) => setFeedback(e.target.value)}
                          placeholder="e.g. Tighten the intro, make Host B more skeptical, add the budget angle, keep it under 4 minutes"
                          rows={3}
                          className="border-slate-700 bg-slate-950 text-slate-100"
                        />
                        <Button
                          onClick={regenerateWithFeedback}
                          disabled={loading || renderingVideo || !feedback.trim()}
                          className="self-end bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                        >
                          {loading || renderingVideo ? (
                            <Loader2 data-icon="inline-start" className="animate-spin" />
                          ) : (
                            <Sparkles data-icon="inline-start" />
                          )}
                          Regenerate with feedback
                        </Button>
                      </div>

                      <Button
                        variant="outline"
                        onClick={reset}
                        className="border-slate-700 bg-slate-800/60 text-slate-100 hover:bg-slate-800"
                      >
                        <RotateCcw data-icon="inline-start" />
                        Generate another episode
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
