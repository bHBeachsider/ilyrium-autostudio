import { generateText, Output } from "ai"
import * as z from "zod"
import type { EpisodeRow } from "@/lib/db"
import { envFlag, type Publisher, type PublishResult } from "./types"

// YouTube publisher, manual-export mode. Full YouTube Data API OAuth is staged
// behind a future "connect YouTube" step; until then this channel produces a
// ready-to-upload package: the rendered MP4's URL plus generated title,
// description and tags — recorded as status 'manual'.

const metaSchema = z.object({
  title: z.string().describe("YouTube title, <=95 chars, specific and clickable without being clickbait"),
  description: z
    .string()
    .describe("YouTube description: 2-3 paragraphs, then a short chapter-less summary of topics covered"),
  tags: z.array(z.string()).max(15).describe("Relevant YouTube tags"),
})

export const youtubePublisher: Publisher = {
  id: "youtube",
  enabled() {
    return envFlag("PUBLISH_YOUTUBE_ENABLED")
  },
  disabledReason() {
    return "PUBLISH_YOUTUBE_ENABLED is not 'true'."
  },
  async publish(episode: EpisodeRow): Promise<PublishResult> {
    if (!episode.video_url) throw new Error("Episode has no video_url to export.")
    const { output } = await generateText({
      model: "openai/gpt-5-mini",
      output: Output.object({ schema: metaSchema }),
      system:
        "You write YouTube metadata for 'Palm Beach County Weekly', a local news podcast about construction, " +
        "real estate and local government in Palm Beach County, Florida.",
      messages: [
        {
          role: "user",
          content: `Episode title: ${episode.title}\nDescription: ${episode.description ?? ""}\nFirst lines:\n${episode.segments
            .slice(0, 6)
            .map((s) => `${s.speaker}: ${s.text}`)
            .join("\n")}`,
        },
      ],
    })
    return {
      status: "manual",
      url: episode.video_url,
      detail: {
        note: "Manual export: download the MP4 and upload with the drafted metadata (YouTube OAuth not connected).",
        videoUrl: episode.video_url,
        draft: output,
      },
    }
  },
}
