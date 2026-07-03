"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import type { ReactNode } from "react"
import { type Idea, initialIdeas } from "@/lib/sandbox-types"

export type VideoKind = "default" | "uploaded" | "generated"

export type PlaylistVideo = {
  id: string
  label: string
  url: string
  kind: VideoKind
  /** Object URLs we created and should revoke on removal/unmount. */
  isObjectUrl: boolean
}

export type Project = {
  id: string
  name: string
  ideas: Idea[]
  videos: PlaylistVideo[]
  selectedVideoId: string | null
}

type ProjectsContextValue = {
  // Project-level
  projects: Project[]
  activeProjectId: string | null
  activeProject: Project | null
  /** Which project's workspace is currently open. null = show the projects list. */
  openProjectId: string | null
  createProject: (name?: string) => string
  switchProject: (id: string) => void
  /** Open a project's workspace (also makes it active). */
  openProject: (id: string) => void
  /** Open a project's workspace AND focus the episode generator (entry for "new podcast"). */
  openProjectToGenerate: (id: string) => void
  /** Bumped each time openProjectToGenerate fires; the generator scrolls/focuses on change. */
  generateNonce: number
  /** Return to the projects list. */
  closeProject: () => void
  renameProject: (id: string, name: string) => void
  deleteProject: (id: string) => void

  // Idea actions (scoped to the active project)
  ideas: Idea[]
  addIdea: (idea: { title: string; summary: string }) => void

  // Video playlist actions (scoped to the active project)
  videos: PlaylistVideo[]
  selectedVideoId: string | null
  selectedVideo: PlaylistVideo | null
  selectVideo: (id: string) => void
  addVideo: (video: { label: string; url: string; kind: VideoKind; isObjectUrl: boolean }) => string
  removeVideo: (id: string) => void
}

const ProjectsContext = createContext<ProjectsContextValue | null>(null)

/** Every new project starts with the bundled sample episode in its player. */
function defaultSampleVideo(): PlaylistVideo {
  return {
    id: "default-sample",
    label: "Sample Episode — Foreign Architecture",
    url: "/sample-episode.mp4",
    kind: "default",
    isObjectUrl: false,
  }
}

function makeProject(name: string, opts?: { seedIdeas?: boolean }): Project {
  const sample = defaultSampleVideo()
  return {
    id: crypto.randomUUID(),
    name,
    ideas: opts?.seedIdeas ? initialIdeas : [],
    videos: [sample],
    selectedVideoId: sample.id,
  }
}

export function ProjectsProvider({ children }: { children: ReactNode }) {
  // First project keeps the existing seeded ideas so the app looks familiar.
  const [projects, setProjects] = useState<Project[]>(() => [makeProject("Palm Beach County Weekly", { seedIdeas: true })])
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() => null)
  // null = show the projects list; otherwise the open workspace.
  const [openProjectId, setOpenProjectId] = useState<string | null>(() => null)
  // Bumped when entering a workspace via a "new podcast" entry button so the episode
  // generator can scroll into view + focus its topic input.
  const [generateNonce, setGenerateNonce] = useState(0)

  // Initialize the active id once projects exist.
  const initRef = useRef(false)
  if (!initRef.current && projects.length > 0) {
    initRef.current = true
  }
  const resolvedActiveId = activeProjectId ?? projects[0]?.id ?? null

  const projectsRef = useRef<Project[]>(projects)
  projectsRef.current = projects

  // Revoke any object URLs we created across all projects when unmounting.
  useEffect(() => {
    return () => {
      projectsRef.current.forEach((p) =>
        p.videos.forEach((v) => {
          if (v.isObjectUrl) URL.revokeObjectURL(v.url)
        }),
      )
    }
  }, [])

  const createProject = useCallback<ProjectsContextValue["createProject"]>((name) => {
    const project = makeProject(name?.trim() || "Untitled project")
    setProjects((prev) => [...prev, project])
    setActiveProjectId(project.id)
    // Open the new project's workspace immediately.
    setOpenProjectId(project.id)
    return project.id
  }, [])

  const switchProject = useCallback((id: string) => setActiveProjectId(id), [])

  const openProject = useCallback((id: string) => {
    setActiveProjectId(id)
    setOpenProjectId(id)
  }, [])

  const openProjectToGenerate = useCallback((id: string) => {
    setActiveProjectId(id)
    setOpenProjectId(id)
    setGenerateNonce((n) => n + 1)
  }, [])

  const closeProject = useCallback(() => setOpenProjectId(null), [])

  const renameProject = useCallback((id: string, name: string) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, name: name.trim() || p.name } : p)))
  }, [])

  const deleteProject = useCallback((id: string) => {
    // If the open workspace is being deleted, return to the projects list.
    setOpenProjectId((cur) => (cur === id ? null : cur))
    setProjects((prev) => {
      const target = prev.find((p) => p.id === id)
      // Free any object URLs owned by the deleted project.
      target?.videos.forEach((v) => {
        if (v.isObjectUrl) URL.revokeObjectURL(v.url)
      })
      const next = prev.filter((p) => p.id !== id)
      // Always keep at least one project.
      if (next.length === 0) {
        const fresh = makeProject("Untitled project")
        setActiveProjectId(fresh.id)
        return [fresh]
      }
      setActiveProjectId((cur) => (cur === id ? next[next.length - 1].id : cur))
      return next
    })
  }, [])

  // ---- Active-project-scoped helpers ----
  const updateActive = useCallback(
    (updater: (p: Project) => Project) => {
      setProjects((prev) => prev.map((p) => (p.id === resolvedActiveId ? updater(p) : p)))
    },
    [resolvedActiveId],
  )

  const addIdea = useCallback<ProjectsContextValue["addIdea"]>(
    ({ title, summary }) => {
      updateActive((p) => ({
        ...p,
        ideas: [
          {
            id: crypto.randomUUID(),
            title,
            summary: summary || "No description yet.",
            stage: "draft",
            sources: 0,
            video: false,
          },
          ...p.ideas,
        ],
      }))
    },
    [updateActive],
  )

  const selectVideo = useCallback(
    (id: string) => updateActive((p) => ({ ...p, selectedVideoId: id })),
    [updateActive],
  )

  const addVideo = useCallback<ProjectsContextValue["addVideo"]>(
    (video) => {
      const id = crypto.randomUUID()
      updateActive((p) => ({ ...p, videos: [...p.videos, { id, ...video }], selectedVideoId: id }))
      return id
    },
    [updateActive],
  )

  const removeVideo = useCallback(
    (id: string) => {
      updateActive((p) => {
        const target = p.videos.find((v) => v.id === id)
        if (target?.isObjectUrl) URL.revokeObjectURL(target.url)
        const videos = p.videos.filter((v) => v.id !== id)
        const selectedVideoId =
          p.selectedVideoId === id ? (videos.length ? videos[videos.length - 1].id : null) : p.selectedVideoId
        return { ...p, videos, selectedVideoId }
      })
    },
    [updateActive],
  )

  const value = useMemo<ProjectsContextValue>(() => {
    const activeProject = projects.find((p) => p.id === resolvedActiveId) ?? null
    const videos = activeProject?.videos ?? []
    const selectedVideoId = activeProject?.selectedVideoId ?? null
    const selectedVideo = videos.find((v) => v.id === selectedVideoId) ?? null
    return {
      projects,
      activeProjectId: resolvedActiveId,
      activeProject,
      openProjectId,
      createProject,
      switchProject,
      openProject,
      openProjectToGenerate,
      generateNonce,
      closeProject,
      renameProject,
      deleteProject,
      ideas: activeProject?.ideas ?? [],
      addIdea,
      videos,
      selectedVideoId,
      selectedVideo,
      selectVideo,
      addVideo,
      removeVideo,
    }
  }, [
    projects,
    resolvedActiveId,
    openProjectId,
    createProject,
    switchProject,
    openProject,
    openProjectToGenerate,
    generateNonce,
    closeProject,
    renameProject,
    deleteProject,
    addIdea,
    selectVideo,
    addVideo,
    removeVideo,
  ])

  return <ProjectsContext.Provider value={value}>{children}</ProjectsContext.Provider>
}

export function useProjects() {
  const ctx = useContext(ProjectsContext)
  if (!ctx) throw new Error("useProjects must be used within a ProjectsProvider")
  return ctx
}
