"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Download, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

type SourceKind = "local" | "permithub_api" | "rss"

const SOURCES: { kind: SourceKind; label: string; hint: string }[] = [
  { kind: "local", label: "Local files", hint: "Producer output in PBC_PODCAST_DIR (week folders)" },
  { kind: "permithub_api", label: "PermitHub API", hint: "GET /api/admin/podcast/episodes (may be empty)" },
  { kind: "rss", label: "RSS feed", hint: "Podcast feed URL (defaults to PODCAST_RSS_URL)" },
]

type ImportSummary = {
  source: string
  scanned: number
  imported: number
  updated: number
  skipped: number
  errors: { guid: string; message: string }[]
  error?: string
}

export function ImportDialog() {
  const router = useRouter()
  const [source, setSource] = React.useState<SourceKind>("local")
  const [url, setUrl] = React.useState("")
  const [busy, setBusy] = React.useState(false)
  const [result, setResult] = React.useState<ImportSummary | null>(null)

  async function runImport() {
    setBusy(true)
    setResult(null)
    try {
      const res = await fetch("/api/episodes/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, ...(source === "rss" && url.trim() ? { url: url.trim() } : {}) }),
      })
      const body = (await res.json().catch(() => ({}))) as ImportSummary
      setResult(res.ok ? body : { ...body, error: body.error ?? `Import failed (${res.status})` } as ImportSummary)
      if (res.ok) router.refresh()
    } catch {
      setResult({ source, scanned: 0, imported: 0, updated: 0, skipped: 0, errors: [], error: "Network error." })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" className="gap-1.5" />}>
        <Download className="size-4" aria-hidden="true" />
        Import
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import episodes</DialogTitle>
          <DialogDescription>Pull produced episodes into the archive. Re-imports are idempotent.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          {SOURCES.map((s) => (
            <button
              key={s.kind}
              type="button"
              onClick={() => setSource(s.kind)}
              className={`flex flex-col items-start gap-0.5 rounded-lg border p-2.5 text-left transition-colors ${
                source === s.kind ? "border-primary bg-primary/10" : "border-border hover:bg-muted/50"
              }`}
            >
              <span className="text-sm font-medium">{s.label}</span>
              <span className="text-xs text-muted-foreground">{s.hint}</span>
            </button>
          ))}
          {source === "rss" && (
            <Input
              placeholder="https://feeds.transistor.fm/… (optional if PODCAST_RSS_URL set)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          )}
          <Button onClick={runImport} disabled={busy} className="mt-1 gap-1.5">
            {busy && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            {busy ? "Importing…" : "Run import"}
          </Button>
          {result && (
            <div className="rounded-lg border border-border bg-muted/30 p-2.5 text-xs">
              {result.error ? (
                <p className="text-destructive">{result.error}</p>
              ) : (
                <p>
                  Scanned {result.scanned} · imported {result.imported} · updated {result.updated} · skipped{" "}
                  {result.skipped}
                </p>
              )}
              {result.errors?.slice(0, 3).map((e) => (
                <p key={e.guid} className="mt-1 text-destructive">
                  {e.guid}: {e.message}
                </p>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
