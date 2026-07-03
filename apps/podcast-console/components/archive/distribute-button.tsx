"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Loader2, Send } from "lucide-react"
import { Button } from "@/components/ui/button"

type Outcome = { channel: string; skipped?: string; error?: string; distribution?: { status: string } }

export function DistributeButton({ episodeId }: { episodeId: string }) {
  const router = useRouter()
  const [busy, setBusy] = React.useState(false)
  const [summary, setSummary] = React.useState<string | null>(null)

  async function run() {
    setBusy(true)
    setSummary(null)
    try {
      const res = await fetch(`/api/episodes/${episodeId}/distribute`, { method: "POST" })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`)
      const parts = (body.results as Outcome[]).map((r) =>
        r.skipped ? `${r.channel}: off` : `${r.channel}: ${r.error ? "failed" : r.distribution?.status}`,
      )
      setSummary(parts.join(" · "))
      router.refresh()
    } catch (err) {
      setSummary(err instanceof Error ? err.message : "Distribution failed.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="flex items-center gap-2">
      <Button size="sm" variant="outline" onClick={run} disabled={busy} className="gap-1">
        {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" aria-hidden="true" />}
        {busy ? "Distributing…" : "Distribute"}
      </Button>
      {summary && <span className="text-xs text-slate-500">{summary}</span>}
    </span>
  )
}
