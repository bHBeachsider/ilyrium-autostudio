import { generateText, experimental_generateImage as generateImage, Output } from "ai"
import * as z from "zod"
import type { Segment } from "@/lib/db"

// Scene planning + image generation, shared by /api/generate-images and the
// production pipeline. Returns raw bytes; callers decide dataUrl vs blob storage.

const sceneSchema = z.object({
  visualStyle: z
    .string()
    .describe(
      "One short phrase describing the cohesive visual style chosen for THIS episode, e.g. 'sunlit architectural photography' or 'editorial flat illustration'",
    ),
  scenes: z
    .array(
      z.object({
        caption: z.string().describe("Very short on-screen caption (3-6 words) for this scene"),
        startSegmentIndex: z
          .number()
          .int()
          .describe(
            "The 0-based index of the transcript line where THIS scene's topic begins. Must be non-decreasing across scenes; the first scene must start at 0.",
          ),
        imagePrompt: z
          .string()
          .describe(
            "A detailed, self-contained image generation prompt for a 16:9 frame that visually represents what is being discussed at this point in the episode. No text or words in the image.",
          ),
      }),
    )
    .min(4)
    .max(10)
    .describe("Ordered scenes that track the episode's narrative arc, each anchored to where its topic is discussed"),
})

export type EpisodeImages = {
  visualStyle: string
  images: { caption: string; bytes: Buffer; mediaType: string }[]
  weights: number[]
}

export async function generateEpisodeImages(input: {
  title: string
  description?: string | null
  segments: Segment[]
}): Promise<EpisodeImages> {
  const segments = input.segments
  const transcript = segments.map((s, i) => `[${i}] ${s.speaker}: ${s.text}`).join("\n")
  const sceneCount = Math.min(10, Math.max(5, Math.round(segments.length / 2)))

  // 1) Derive a per-episode visual style + ordered scene prompts from the script.
  const { output: plan } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: sceneSchema }),
    system:
      "You are the art director for 'Palm Beach County Weekly', a local-news video podcast. " +
      "Given an episode script, first decide ONE cohesive visual style that best fits this specific topic " +
      "(it may be photoreal, editorial illustration, cinematic, archival-documentary, etc. — choose per episode). " +
      "Then break the episode into ordered visual scenes. CRITICAL: each scene's image must depict exactly what is " +
      "being discussed in the transcript lines it covers, and you must set startSegmentIndex to the transcript line " +
      "number (shown in [brackets]) where that topic begins. The first scene starts at 0 and indices must increase. " +
      "Each scene gets a vivid, self-contained image prompt in the chosen style for a 16:9 frame that literally " +
      "illustrates the subject of those lines (a place, object, person, or concept mentioned). " +
      "Keep imagery locally relevant to Palm Beach County, Florida where natural. " +
      "Never include text, captions, logos, or watermarks in the image prompts.",
    messages: [
      {
        role: "user",
        content: `Episode: "${input.title}"\n${input.description ? `Summary: ${input.description}\n` : ""}\nProduce exactly ${sceneCount} scenes for this transcript. Each line is prefixed with its [index]:\n\n${transcript}`,
      },
    ],
  })

  // Normalize scene start indices (clamp, sort-safe, force first scene to 0) so each
  // scene maps to a contiguous block of transcript lines.
  const starts = plan.scenes.map((s, i) =>
    i === 0 ? 0 : Math.min(Math.max(0, Math.round(s.startSegmentIndex)), segments.length - 1),
  )
  for (let i = 1; i < starts.length; i++) {
    if (starts[i] < starts[i - 1]) starts[i] = starts[i - 1]
  }

  // Weight each scene by how much narration (character count) its segment block covers,
  // so the renderer can hold each image while its topic is actually spoken.
  const charLen = segments.map((s) => Math.max(1, s.text.trim().length))
  const rawWeights = starts.map((start, i) => {
    const end = i < starts.length - 1 ? starts[i + 1] : segments.length
    let sum = 0
    for (let j = start; j < end; j++) sum += charLen[j] ?? 0
    return Math.max(1, sum)
  })

  // Blend the topical weighting with a uniform baseline so visuals still track the
  // discussion, but no single image dominates the screen if the model bunches scenes.
  const totalRaw = rawWeights.reduce((a, b) => a + b, 0)
  const nScenes = rawWeights.length
  const BLEND = 0.6 // share driven by narration coverage; the rest is evenly spread
  const weights = rawWeights.map((w) => {
    const topical = w / totalRaw
    const uniform = 1 / nScenes
    return Math.round((BLEND * topical + (1 - BLEND) * uniform) * 1000)
  })

  // 2) Generate each scene image in the chosen style (Imagen 4 Fast via AI Gateway).
  const images = await Promise.all(
    plan.scenes.map(async (scene) => {
      const { image } = await generateImage({
        model: "google/imagen-4.0-fast-generate-001",
        prompt: `${scene.imagePrompt}. Style: ${plan.visualStyle}. Cinematic 16:9 composition, high detail, no text.`,
        aspectRatio: "16:9",
      })
      return {
        caption: scene.caption,
        bytes: Buffer.from(image.base64, "base64"),
        mediaType: image.mediaType ?? "image/png",
      }
    }),
  )

  return { visualStyle: plan.visualStyle, images, weights }
}
