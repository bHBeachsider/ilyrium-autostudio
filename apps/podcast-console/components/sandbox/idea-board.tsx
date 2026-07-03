"use client"

import { useState } from "react"
import { Plus, Sparkles } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Field, FieldLabel } from "@/components/ui/field"
import { cn } from "@/lib/utils"
import { type Idea, stageMeta } from "@/lib/sandbox-types"

export function IdeaBoard({
  ideas,
  onCreateIdea,
}: {
  ideas: Idea[]
  onCreateIdea: (idea: { title: string; summary: string }) => void
}) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [summary, setSummary] = useState("")

  function createIdea() {
    if (!title.trim()) return
    onCreateIdea({ title: title.trim(), summary: summary.trim() })
    setTitle("")
    setSummary("")
    setOpen(false)
  }

  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
              <Sparkles className="size-4.5" aria-hidden="true" />
            </span>
            <div>
              <CardTitle className="text-slate-50">Idea Sandbox</CardTitle>
              <CardDescription className="text-slate-400">
                Spin up and experiment with new show concepts before they ship.
              </CardDescription>
            </div>
          </div>
          <Button
            onClick={() => setOpen((o) => !o)}
            className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
          >
            <Plus data-icon="inline-start" />
            New idea
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {open && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex flex-col gap-4">
              <Field>
                <FieldLabel htmlFor="idea-title">Idea title</FieldLabel>
                <Input
                  id="idea-title"
                  placeholder="e.g. Weekend events digest"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="idea-summary">Concept</FieldLabel>
                <Textarea
                  id="idea-summary"
                  placeholder="What signal does this pull from? What format?"
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  rows={3}
                />
              </Field>
              <div className="flex items-center justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => setOpen(false)}
                  className="text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                >
                  Cancel
                </Button>
                <Button
                  onClick={createIdea}
                  disabled={!title.trim()}
                  className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
                >
                  Add to sandbox
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {ideas.map((idea) => {
            const stage = stageMeta[idea.stage]
            const StageIcon = stage.icon
            return (
              <div
                key={idea.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4 transition-colors hover:border-slate-700"
              >
                <div className="flex items-start justify-between gap-2">
                  <Badge variant="secondary" className={cn("gap-1", stage.className)}>
                    <StageIcon className="size-3" aria-hidden="true" />
                    {stage.label}
                  </Badge>
                  {idea.video && (
                    <Badge variant="secondary" className="gap-1 bg-slate-800 text-slate-300">
                      Video
                    </Badge>
                  )}
                </div>
                <div className="flex flex-col gap-1">
                  <h3 className="text-sm font-semibold text-slate-100 text-balance">{idea.title}</h3>
                  <p className="text-xs leading-relaxed text-slate-400">{idea.summary}</p>
                </div>
                <div className="mt-auto flex items-center justify-between border-t border-slate-800 pt-3">
                  <span className="text-xs text-slate-500">
                    {idea.sources} source{idea.sources === 1 ? "" : "s"}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300"
                  >
                    Open sandbox
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
