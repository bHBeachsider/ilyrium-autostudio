"use client"

import { Sidebar } from "@/components/dashboard/sidebar"
import { Header } from "@/components/dashboard/header"
import { IdeaBoard } from "@/components/sandbox/idea-board"
import { DataSourcePipeline } from "@/components/sandbox/data-source-pipeline"
import { EpisodeGenerator } from "@/components/sandbox/episode-generator"
import { SampleEpisode } from "@/components/sandbox/sample-episode"
import { VideoDimension } from "@/components/sandbox/video-dimension"
import { ProjectSwitcher } from "@/components/sandbox/project-switcher"
import { ProjectsGrid } from "@/components/sandbox/projects-grid"
import { ProjectsProvider, useProjects } from "@/lib/projects"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

function SandboxContent() {
  const { ideas, addIdea, activeProject, openProjectId, closeProject } = useProjects()
  const isOpen = openProjectId !== null

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header section="Studio" page="Idea Sandbox" />
        <main className="flex-1 overflow-y-auto bg-slate-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            {isOpen ? (
              <>
                <div className="flex flex-col gap-4 border-b border-slate-800 pb-6">
                  <Button
                    variant="ghost"
                    onClick={closeProject}
                    className="-ml-2 w-fit text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  >
                    <ArrowLeft data-icon="inline-start" />
                    All projects
                  </Button>
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                    <div className="flex flex-col gap-1">
                      <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
                        {activeProject?.name ?? "Idea Sandbox"}
                      </h1>
                      <p className="text-sm text-slate-400">
                        Prototype concepts, ingest content, and explore the video dimension.
                      </p>
                    </div>
                    <ProjectSwitcher />
                  </div>
                </div>

                <EpisodeGenerator ideas={ideas} />

                <IdeaBoard ideas={ideas} onCreateIdea={addIdea} />

                <SampleEpisode />

                <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
                  <div className="min-w-0 lg:col-span-3">
                    <DataSourcePipeline onIngest={addIdea} />
                  </div>
                  <div className="min-w-0 lg:col-span-2">
                    <VideoDimension />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex flex-col gap-1 border-b border-slate-800 pb-6">
                  <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Idea Sandbox</h1>
                  <p className="text-sm text-slate-400">
                    Each project is its own workspace for prototyping show concepts and generating episodes.
                  </p>
                </div>

                <ProjectsGrid />
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default function SandboxPage() {
  return (
    <ProjectsProvider>
      <SandboxContent />
    </ProjectsProvider>
  )
}
