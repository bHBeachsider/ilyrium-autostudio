import { generateText, Output } from "ai"
import * as z from "zod"

export const maxDuration = 60

const episodeSchema = z.object({
  title: z.string().describe("Punchy, specific episode title"),
  description: z.string().describe("2-3 sentence episode summary for show notes"),
  estimatedMinutes: z.number().describe("Estimated runtime in minutes"),
  segments: z
    .array(
      z.object({
        speaker: z.enum(["Host A", "Host B"]).describe("Which of the two hosts is speaking"),
        text: z.string().describe("The spoken line, conversational and natural"),
      }),
    )
    .describe("The back-and-forth conversational script between two hosts"),
})

export async function POST(req: Request) {
  if (!process.env.PERPLEXITY_API_KEY && !process.env.AI_GATEWAY_API_KEY) {
    // AI Gateway works zero-config for OpenAI in v0; no hard requirement here.
  }

  let body: {
    topic?: string
    summary?: string
    sources?: string[]
    targetMinutes?: number
    feedback?: string
    previousScript?: { speaker: string; text: string }[]
  }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid request body." }, { status: 400 })
  }

  const topic = body.topic?.trim()
  if (!topic) {
    return Response.json({ error: "A topic or idea title is required." }, { status: 400 })
  }

  // ~140 spoken words per minute; scale segment count to the target runtime.
  const targetMinutes = Math.min(30, Math.max(2, Math.round(body.targetMinutes || 5)))
  const targetWords = targetMinutes * 140
  const minSegments = Math.max(8, targetMinutes * 3)
  const maxSegments = Math.max(12, targetMinutes * 5)

  const sourceContext =
    body.sources && body.sources.length > 0
      ? `\n\nGround the conversation in these ingested source signals:\n${body.sources.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
      : ""

  // Revision pass: when the producer gives feedback on a finished episode, fold it in
  // and rewrite the whole script. Include the prior script (capped) for reference.
  const feedback = body.feedback?.trim()
  const prevScript = Array.isArray(body.previousScript) ? body.previousScript.slice(0, 50) : []
  const revisionContext = feedback
    ? `\n\nThis is a REVISION of an existing episode. Apply this producer feedback and rewrite the full two-host script accordingly:\n"${feedback}"` +
      (prevScript.length > 0
        ? `\n\nThe previous version (revise per the feedback, do not repeat it verbatim):\n${prevScript
            .map((s) => `${s.speaker}: ${s.text}`)
            .join("\n")}`
        : "")
    : ""

  try {
    const { output } = await generateText({
      model: "openai/gpt-5-mini",
      output: Output.object({ schema: episodeSchema }),
      system:
        "You are the showrunner for 'Palm Beach County Weekly', a local-news podcast. " +
        "You write curated, NotebookLM-style episodes as a natural, engaging conversation between two co-hosts: " +
        "Host A (warm, curious anchor) and Host B (sharp analyst who adds context). " +
        "Keep it factual, locally relevant, and conversational. Alternate speakers frequently. " +
        "Open with a quick hook, cover the key angles, and close with a takeaway. " +
        "When producer feedback is provided, treat it as the top priority and revise the whole episode to satisfy it. " +
        `This episode must run about ${targetMinutes} minutes when spoken aloud — roughly ${targetWords} total words across ${minSegments}-${maxSegments} segments. ` +
        `Set estimatedMinutes to ${targetMinutes}.`,
      messages: [
        {
          role: "user",
          content:
            `Create a curated, ~${targetMinutes}-minute podcast episode about: "${topic}".` +
            (body.summary ? `\n\nContext: ${body.summary}` : "") +
            sourceContext +
            revisionContext,
        },
      ],
    })

    return Response.json({ episode: output })
  } catch (err) {
    console.log("[v0] Episode generation failed:", err instanceof Error ? err.message : err)
    return Response.json({ error: "Failed to generate the episode script. Please try again." }, { status: 500 })
  }
}
