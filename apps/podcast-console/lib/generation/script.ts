import { generateText, Output } from "ai"
import * as z from "zod"

// Two-host script generation, shared by the sandbox route (/api/generate-episode),
// two-gate draft scripts, and the production pipeline.

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

export type GeneratedScript = z.infer<typeof episodeSchema>

export type ScriptRequest = {
  topic: string
  summary?: string
  sources?: string[]
  targetMinutes?: number
  feedback?: string
  previousScript?: { speaker: string; text: string }[]
}

export async function generateScript(req: ScriptRequest): Promise<GeneratedScript> {
  // ~140 spoken words per minute; scale segment count to the target runtime.
  const targetMinutes = Math.min(30, Math.max(2, Math.round(req.targetMinutes || 5)))
  const targetWords = targetMinutes * 140
  const minSegments = Math.max(8, targetMinutes * 3)
  const maxSegments = Math.max(12, targetMinutes * 5)

  const grounded = !!req.sources && req.sources.length > 0
  const sourceContext = grounded
    ? `\n\nGround the conversation in these ingested source signals:\n${req.sources!.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
    : ""

  // Verified-content contract: with real sources present, the script may only
  // assert what they support, and must attribute specifics on air. The ungrounded
  // sandbox path keeps the original behavior.
  const groundingRules = grounded
    ? "STRICT SOURCING RULES: every specific fact in the script (numbers, dollar amounts, dates, names, " +
      "votes, quotes, decisions) must come from the provided source material — invent nothing. Attribute " +
      "specifics on air by outlet name (e.g. \"according to WPTV\" or \"the Palm Beach Post reports\"). " +
      "If sources conflict, say so; if they are silent on a detail, omit it rather than guessing. " +
      "Hosts may add context, explanation and color, but never new facts. "
    : ""

  // Revision pass: when the producer gives feedback on a finished episode, fold it in
  // and rewrite the whole script. Include the prior script (capped) for reference.
  const feedback = req.feedback?.trim()
  const prevScript = Array.isArray(req.previousScript) ? req.previousScript.slice(0, 50) : []
  const revisionContext = feedback
    ? `\n\nThis is a REVISION of an existing episode. Apply this producer feedback and rewrite the full two-host script accordingly:\n"${feedback}"` +
      (prevScript.length > 0
        ? `\n\nThe previous version (revise per the feedback, do not repeat it verbatim):\n${prevScript
            .map((s) => `${s.speaker}: ${s.text}`)
            .join("\n")}`
        : "")
    : ""

  const { output } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: episodeSchema }),
    system:
      "You are the showrunner for 'Palm Beach County Weekly', a local-news podcast. " +
      "You write curated, NotebookLM-style episodes as a natural, engaging conversation between two co-hosts: " +
      "Host A (warm, curious anchor) and Host B (sharp analyst who adds context). " +
      "Keep it factual, locally relevant, and conversational. Alternate speakers frequently. " +
      groundingRules +
      "Open with a quick hook, cover the key angles, and close with a takeaway. " +
      "When producer feedback is provided, treat it as the top priority and revise the whole episode to satisfy it. " +
      `This episode must run about ${targetMinutes} minutes when spoken aloud — roughly ${targetWords} total words across ${minSegments}-${maxSegments} segments. ` +
      `Set estimatedMinutes to ${targetMinutes}.`,
    messages: [
      {
        role: "user",
        content:
          `Create a curated, ~${targetMinutes}-minute podcast episode about: "${req.topic}".` +
          (req.summary ? `\n\nContext: ${req.summary}` : "") +
          sourceContext +
          revisionContext,
      },
    ],
  })

  return output
}
