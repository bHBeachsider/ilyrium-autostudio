"use client"

import { CheckCircle2, AlertTriangle, KeyRound } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

const keys = [
  {
    name: "TRANSISTOR_API_KEY",
    status: "configured" as const,
    detail: "Configured",
  },
  {
    name: "GITHUB_DISPATCH_TOKEN",
    status: "configured" as const,
    detail: "Connected",
  },
  {
    name: "PERPLEXITY_API_KEY",
    status: "configured" as const,
    detail: "Connected",
  },
]

export function SystemHealth() {
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <CardTitle className="text-slate-50">System Health</CardTitle>
        <CardDescription className="text-slate-400">API integrations &amp; environment</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {keys.map((key) => {
          const ok = key.status === "configured"
          return (
            <div
              key={key.name}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3"
            >
              <div className="flex items-center gap-3">
                {ok ? (
                  <CheckCircle2 className="size-5 shrink-0 text-emerald-400" aria-hidden="true" />
                ) : (
                  <AlertTriangle className="size-5 shrink-0 text-amber-400" aria-hidden="true" />
                )}
                <code className="font-mono text-xs text-slate-300 sm:text-sm">{key.name}</code>
              </div>
              <Badge
                className={cn(
                  "shrink-0 border",
                  ok
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    : "border-amber-500/30 bg-amber-500/10 text-amber-400",
                )}
              >
                {key.detail}
              </Badge>
            </div>
          )
        })}

        <Dialog>
          <DialogTrigger
            render={
              <Button className="mt-1 w-full bg-emerald-500 text-slate-950 hover:bg-emerald-400">
                <KeyRound data-icon="inline-start" />
                Manage API Keys
              </Button>
            }
          />
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Manage API Keys</DialogTitle>
              <DialogDescription>
                Store credentials used by the production pipeline. Keys are encrypted at rest.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
              {keys.map((key) => (
                <div key={key.name} className="flex flex-col gap-1.5">
                  <label htmlFor={key.name} className="font-mono text-xs text-muted-foreground">
                    {key.name}
                  </label>
                  <input
                    id={key.name}
                    type="password"
                    defaultValue={key.status === "configured" ? "••••••••••••••••" : ""}
                    placeholder="Paste token"
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </div>
              ))}
            </div>
            <DialogFooter>
              <DialogClose
                render={
                  <Button variant="outline">Cancel</Button>
                }
              />
              <DialogClose
                render={
                  <Button className="bg-emerald-500 text-slate-950 hover:bg-emerald-400">Save changes</Button>
                }
              />
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
