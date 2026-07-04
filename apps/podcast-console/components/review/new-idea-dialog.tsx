"use client"

import * as React from "react"
import { Lightbulb, Link2, Loader2, PenLine } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

type Mode = "write" | "article"

export function NewIdeaDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = React.useState(false)
  const [mode, setMode] = React.useState<Mode>("write")
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [title, setTitle] = React.useState("")
  const [summary, setSummary] = React.useState("")
  const [angle, setAngle] = React.useState("")
  const [url, setUrl] = React.useState("")
  const [analysisNote, setAnalysisNote] = React.useState<string | null>(null)

  async function submit() {
    setBusy(true)
    setError(null)
    setAnalysisNote(null)
    try {
      if (mode === "write") {
        const res = await fetch("/api/ideas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, summary: summary || undefined, angle: angle || undefined }),
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`)
        setTitle("")
        setSummary("")
        setAngle("")
        setOpen(false)
      } else {
        const res = await fetch("/api/ideas/reverse-engineer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`)
        const gaps: string[] = body.analysis?.gaps ?? []
        setAnalysisNote(
          `Proposed: "${body.idea?.title}"` + (gaps.length ? ` — built on gaps: ${gaps.slice(0, 2).join("; ")}` : ""),
        )
        setUrl("")
      }
      onCreated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" className="gap-1.5" />}>
        <Lightbulb className="size-4" aria-hidden="true" />
        New idea
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Propose an episode idea</DialogTitle>
          <DialogDescription>
            Lands in the queue as proposed — the approval gate applies to your ideas too.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={mode === "write" ? "default" : "outline"}
              onClick={() => setMode("write")}
              className="gap-1"
            >
              <PenLine className="size-3.5" aria-hidden="true" /> Write it
            </Button>
            <Button
              size="sm"
              variant={mode === "article" ? "default" : "outline"}
              onClick={() => setMode("article")}
              className="gap-1"
            >
              <Link2 className="size-3.5" aria-hidden="true" /> From competitor article
            </Button>
          </div>

          {mode === "write" ? (
            <>
              <Input placeholder="Episode title *" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Input placeholder="Angle (optional)" value={angle} onChange={(e) => setAngle(e.target.value)} />
              <Textarea
                placeholder="Summary — what should the episode cover? (optional)"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="min-h-20"
              />
            </>
          ) : (
            <>
              <Input
                placeholder="https://… (article URL to reverse-engineer)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                The analyst extracts the story, its facts, sourcing and blind spots, then pitches a
                differentiated local episode. Production still verifies against our own trusted sources.
              </p>
            </>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
          {analysisNote && <p className="rounded-lg border border-border bg-muted/30 p-2 text-xs">{analysisNote}</p>}
          <Button onClick={submit} disabled={busy || (mode === "write" ? !title.trim() : !url.trim())} className="gap-1.5">
            {busy && <Loader2 className="size-4 animate-spin" />}
            {busy ? (mode === "article" ? "Analyzing article…" : "Saving…") : mode === "article" ? "Analyze & propose" : "Propose idea"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
