"use client"

import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2, Lock, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const [password, setPassword] = React.useState("")
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error ?? `HTTP ${res.status}`)
      }
      router.replace(params.get("from") || "/")
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.")
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500 text-slate-950">
          <Mic className="size-5" aria-hidden="true" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-base font-semibold text-slate-100">Palm Beach County Weekly</span>
          <span className="text-sm text-slate-400">Podcast Studio</span>
        </div>
      </div>
      <Input
        type="password"
        placeholder="Studio password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        autoFocus
        className="bg-slate-900"
      />
      {error && <p className="text-sm text-rose-400">{error}</p>}
      <Button type="submit" disabled={busy || !password} className="gap-1.5">
        {busy ? <Loader2 className="size-4 animate-spin" /> : <Lock className="size-4" aria-hidden="true" />}
        {busy ? "Signing in…" : "Enter studio"}
      </Button>
    </form>
  )
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <React.Suspense fallback={null}>
        <LoginForm />
      </React.Suspense>
    </main>
  )
}
