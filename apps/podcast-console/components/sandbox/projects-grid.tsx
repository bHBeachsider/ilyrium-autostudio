"use client"

import { useState } from "react"
import { FolderOpen, Plus, Lightbulb, Film, Trash2, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useProjects } from "@/lib/projects"

export function ProjectsGrid() {
  const { projects, activeProjectId, createProject, openProject, openProjectToGenerate, deleteProject } = useProjects()
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState("")
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null)

  function handleCreate() {
    createProject(name)
    setName("")
    setCreateOpen(false)
  }

  // Entry button: drop straight into the episode generator of the active (or first) project.
  function handleNewPodcast() {
    const target = activeProjectId ?? projects[0]?.id
    if (target) openProjectToGenerate(target)
    else openProjectToGenerate(createProject("Untitled project"))
  }

  return (
    <section aria-label="Projects" className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold tracking-tight text-slate-50">Your projects</h2>
          <p className="text-sm text-slate-400">Open a workspace to prototype ideas and generate episodes.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleNewPodcast} className="bg-emerald-500 text-slate-950 hover:bg-emerald-400">
            <Mic data-icon="inline-start" />
            New podcast
          </Button>
          <Button
            onClick={() => setCreateOpen(true)}
            variant="outline"
            className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800 hover:text-slate-50"
          >
            <Plus data-icon="inline-start" />
            New project
          </Button>
        </div>
      </div>

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => {
          const episodes = p.videos.filter((v) => v.kind === "generated").length
          return (
            <li key={p.id}>
              <div className="group flex h-full flex-col gap-4 rounded-lg border border-slate-800 bg-slate-900 p-5 transition-colors hover:border-slate-700">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400">
                    <FolderOpen className="size-5" aria-hidden="true" />
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setPendingDelete({ id: p.id, name: p.name })}
                    aria-label={`Delete ${p.name}`}
                    className="size-8 text-slate-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </div>

                <div className="flex min-w-0 flex-col gap-1">
                  <h3 className="truncate text-base font-semibold text-slate-100">{p.name}</h3>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span className="inline-flex items-center gap-1">
                      <Lightbulb className="size-3.5" aria-hidden="true" />
                      {p.ideas.length} {p.ideas.length === 1 ? "idea" : "ideas"}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Film className="size-3.5" aria-hidden="true" />
                      {episodes} {episodes === 1 ? "episode" : "episodes"}
                    </span>
                  </div>
                </div>

                <Button
                  onClick={() => openProject(p.id)}
                  variant="outline"
                  className="mt-auto border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-slate-50"
                >
                  Open workspace
                </Button>
              </div>
            </li>
          )
        })}

        {/* New project card */}
        <li>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="flex h-full min-h-44 w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-5 text-slate-400 transition-colors hover:border-emerald-500/60 hover:text-emerald-400"
          >
            <Plus className="size-6" aria-hidden="true" />
            <span className="text-sm font-medium">New project</span>
          </button>
        </li>
      </ul>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription className="text-slate-400">
              Give your project a name. You can rename it later.
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="Project name"
            className="border-slate-700 bg-slate-950 text-slate-100"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateOpen(false)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-slate-50"
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} className="bg-emerald-600 text-slate-50 hover:bg-emerald-500">
              Create project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!pendingDelete} onOpenChange={(o) => !o && setPendingDelete(null)}>
        <DialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription className="text-slate-400">
              {pendingDelete ? `Delete "${pendingDelete.name}"? This removes its ideas and videos for this session.` : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPendingDelete(null)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:text-slate-50"
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (pendingDelete) deleteProject(pendingDelete.id)
                setPendingDelete(null)
              }}
              className="bg-red-600 text-slate-50 hover:bg-red-500"
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
