"use client"

/**
 * Thin adapter over the projects context. The video playlist is now owned
 * per-project by ProjectsProvider; this hook preserves the original
 * useVideoPlaylist() API so the player and episode generator stay unchanged.
 */
import { useProjects, type PlaylistVideo, type VideoKind } from "@/lib/projects"

export type { PlaylistVideo, VideoKind }

export function useVideoPlaylist() {
  const { videos, selectedVideoId, selectedVideo, selectVideo, addVideo, removeVideo } = useProjects()
  return {
    videos,
    selectedId: selectedVideoId,
    selected: selectedVideo,
    select: selectVideo,
    addVideo,
    removeVideo,
  }
}
