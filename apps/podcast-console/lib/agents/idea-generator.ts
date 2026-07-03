import { generateText, Output } from "ai"
import * as z from "zod"
import { requireSql, ensureSchema, type IdeaRow } from "@/lib/db"

// The idea-generation agent: reads recent content (synced content items + archived
// episodes), proposes distinct episode ideas, dedupes against recent ideas/episodes,
// and files survivors into podcast_ideas as 'proposed'. It never produces anything —
// downstream work is gated on human approval (see lib/ideas.ts).

const AGENT_NAME = "idea_generator"

const ideasSchema = z.object({
  ideas: z
    .array(
      z.object({
        title: z.string().describe("Punchy, specific episode title"),
        angle: z.string().describe("The editorial angle or hook, one sentence"),
        summary: z.string().describe("2-3 sentence outline of what the episode covers"),
        rationale: z.string().describe("Why this is worth an episode now, grounded in the source material"),
        sourceRefs: z.array(z.string()).describe("Which provided source items/titles inspired this idea"),
        score: z.number().min(0).max(10).describe("Editorial promise, 0-10"),
      }),
    )
    .describe("Distinct episode ideas, strongest first"),
})

/** Cheap title-similarity dedup: normalized containment or >60% token overlap. */
export function isDuplicateTitle(title: string, existing: string[]): boolean {
  const norm = (s: string) =>
    s
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, "")
      .trim()
  const tokens = (s: string) => new Set(norm(s).split(/\s+/).filter((t) => t.length > 2))
  const a = norm(title)
  const at = tokens(title)
  for (const other of existing) {
    const b = norm(other)
    if (!a || !b) continue
    if (a === b || a.includes(b) || b.includes(a)) return true
    const bt = tokens(other)
    if (at.size === 0 || bt.size === 0) continue
    let overlap = 0
    for (const t of at) if (bt.has(t)) overlap++
    if (overlap / Math.min(at.size, bt.size) > 0.6) return true
  }
  return false
}

export type GenerateIdeasResult = {
  proposed: IdeaRow[]
  generated: number
  deduped: number
  contextItems: number
  /** Set when the agent refused to run (e.g. no source material to ground in). */
  skipped?: string
}

export async function generateIdeas(opts: { count?: number; prompt?: string } = {}): Promise<GenerateIdeasResult> {
  const sql = requireSql()
  await ensureSchema()
  const count = Math.min(10, Math.max(1, Math.round(opts.count ?? 5)))

  const [items, episodes, recentIdeas] = await Promise.all([
    sql`SELECT title, summary, url FROM podcast_content_items ORDER BY created_at DESC LIMIT 25`,
    sql`SELECT title, description, week_of FROM podcast_episodes ORDER BY created_at DESC LIMIT 20`,
    sql`SELECT title FROM podcast_ideas ORDER BY created_at DESC LIMIT 40`,
  ])

  const sourceLines = [
    ...(items as { title: string; summary: string | null; url: string | null }[]).map(
      (it, i) => `S${i + 1}. ${it.title}${it.summary ? ` — ${it.summary}` : ""}`,
    ),
  ]

  // Grounding is mandatory: without real source material the agent would pitch
  // plausible-sounding but unreported "evergreen" episodes. Refuse instead.
  if (sourceLines.length === 0) {
    const skipped =
      "No synced content items to ground ideas in — register a source (POST /api/sources) and sync it (loop tick) before generating."
    console.warn(`[${AGENT_NAME}] skipped: ${skipped}`)
    return { proposed: [], generated: 0, deduped: 0, contextItems: 0, skipped }
  }

  const episodeTitles = (episodes as { title: string }[]).map((e) => e.title)
  const ideaTitles = (recentIdeas as { title: string }[]).map((i) => i.title)
  const avoid = [...episodeTitles, ...ideaTitles]

  const { output } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: ideasSchema }),
    system:
      "You are the story editor for 'Palm Beach County Weekly', a podcast covering construction, " +
      "real estate, and local government in Palm Beach County, Florida. You pitch specific, " +
      "reportable episode ideas grounded ONLY in the provided source material — every idea's " +
      "sourceRefs must cite the source items (their S-numbers and titles) it is based on, and you " +
      "must not invent ideas that no source item supports. Each idea must be clearly distinct " +
      "from the others and from the avoid-list of already-covered titles.",
    messages: [
      {
        role: "user",
        content:
          `Propose up to ${count} distinct episode ideas — fewer is fine if the source material only supports fewer.` +
          (opts.prompt ? `\n\nEditorial direction from the producer: ${opts.prompt}` : "") +
          `\n\nRecent source material:\n${sourceLines.join("\n")}` +
          (episodeTitles.length > 0 ? `\n\nRecent episodes (context):\n${episodeTitles.join("\n")}` : "") +
          (avoid.length > 0 ? `\n\nAVOID duplicating any of these existing titles/ideas:\n${avoid.join("\n")}` : ""),
      },
    ],
  })

  const proposed: IdeaRow[] = []
  let deduped = 0
  let ungrounded = 0
  const seen = [...avoid]
  for (const idea of output.ideas.slice(0, count)) {
    // Belt-and-braces on the grounding contract: an idea that cites nothing is dropped.
    if (idea.sourceRefs.length === 0) {
      ungrounded++
      continue
    }
    if (isDuplicateTitle(idea.title, seen)) {
      deduped++
      continue
    }
    seen.push(idea.title)
    const rows = (await sql`
      INSERT INTO podcast_ideas (title, summary, angle, rationale, source_refs, status, score, created_by)
      VALUES (${idea.title}, ${idea.summary}, ${idea.angle}, ${idea.rationale},
              ${JSON.stringify(idea.sourceRefs)}::jsonb, 'proposed', ${idea.score}, ${AGENT_NAME})
      RETURNING *
    `) as IdeaRow[]
    proposed.push(rows[0])
  }

  console.log(
    `[${AGENT_NAME}] generated=${output.ideas.length} proposed=${proposed.length} deduped=${deduped} ungrounded=${ungrounded} contextItems=${sourceLines.length}`,
  )
  return { proposed, generated: output.ideas.length, deduped, contextItems: sourceLines.length }
}
