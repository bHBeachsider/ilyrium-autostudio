"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useProjects } from "@/lib/projects"
import { FolderKanban, ChevronsUpDown, Plus, Pencil, Trash2, Check } from "lucide-react"

export function ProjectSwitcher() {
  const { projects, activeProjectId, activeProject, createProject, switchProject, renameProject, deleteProject } =
    useProjects()

  const [createOpen, setCreateOpen] = useState(false)
  const [renameOpen, setRenameOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [draftName, setDraftName] = useState("")

  function openCreate() {
    setDraftName("")
    setCreateOpen(true)
  }
  function openRename() {
    setDraftName(activeProject?.name ?? "")
    setRenameOpen(true)
  }

  function submitCreate() {
    createProject(draftName)
    setCreateOpen(false)
  }
  function submitRename() {
    if (activeProjectId) renameProject(activeProjectId, draftName)
    setRenameOpen(false)
  }
  function confirmDelete() {
    if (activeProjectId) deleteProject(activeProjectId)
    setDeleteOpen(false)
  }

  return (
    <>
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="outline"
                className="h-9 max-w-[16rem] justify-between gap-2 border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800 hover:text-slate-50"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <FolderKanban className="size-4 shrink-0 text-emerald-400" aria-hidden="true" />
                  <span className="truncate">{activeProject?.name ?? "Select project"}</span>
                </span>
                <ChevronsUpDown className="size-4 shrink-0 text-slate-500" aria-hidden="true" />
              </Button>
            }
          />
          <DropdownMenuContent className="w-64">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Projects ({projects.length})</DropdownMenuLabel>
              {projects.map((p) => (
                <DropdownMenuItem
                  key={p.id}
                  onClick={() => switchProject(p.id)}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="truncate">{p.name}</span>
                  {p.id === activeProjectId && (
                    <Check className="size-4 shrink-0 text-emerald-400" aria-hidden="true" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={openCreate}>
              <Plus className="size-4" aria-hidden="true" />
              New project
            </DropdownMenuItem>
            <DropdownMenuItem onClick={openRename}>
              <Pencil className="size-4" aria-hidden="true" />
              Rename current
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => setDeleteOpen(true)}
              className="text-red-400 data-[highlighted]:text-red-300"
            >
              <Trash2 className="size-4" aria-hidden="true" />
              Delete current
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="default"
          onClick={openCreate}
          className="h-9 gap-1.5 bg-emerald-600 text-white hover:bg-emerald-500"
        >
          <Plus className="size-4" aria-hidden="true" />
          New project
        </Button>
      </div>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription className="text-slate-400">
              Each project keeps its own ideas and video playlist.
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitCreate()}
            placeholder="Project name"
            className="border-slate-700 bg-slate-950 text-slate-100"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateOpen(false)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button onClick={submitCreate} className="bg-emerald-600 text-white hover:bg-emerald-500">
              Create project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>Rename project</DialogTitle>
          </DialogHeader>
          <Input
            autoFocus
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitRename()}
            placeholder="Project name"
            className="border-slate-700 bg-slate-950 text-slate-100"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRenameOpen(false)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button onClick={submitRename} className="bg-emerald-600 text-white hover:bg-emerald-500">
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="border-slate-800 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle>Delete project</DialogTitle>
            <DialogDescription className="text-slate-400">
              {`Delete "${activeProject?.name ?? "this project"}"? Its ideas and playlist will be removed. This can't be undone.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              className="border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button onClick={confirmDelete} className="bg-red-600 text-white hover:bg-red-500">
              Delete project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
