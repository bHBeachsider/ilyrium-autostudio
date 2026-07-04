import { generateText, Output } from "ai"
import * as z from "zod"
import { requireSql, ensureSchema, type IdeaRow } from "@/lib/db"
import { usableFullText } from "@/lib/research"
import { notifyIdeaProposed, telegramEnabled } from "@/lib/telegram"

// Competitor-article reverse engineering: given a published article URL, extract
// its text, deconstruct what makes the story work (facts, sources, angle, gaps),
// and file a LOCALIZED episode idea into the review queue. The competitor piece
// is inspiration only — production still researches and verifies against our own
// trusted sources, so nothing from the article is trusted or republished as-is.

const analysisSchema = z.object({
  story: z.string().describe("What actually happened, in 2-3 sentences"),
  angle: z.string().describe("The editorial angle the article took, one sentence"),
  keyFacts: z.array(z.string()).max(12).describe("The concrete facts/figures the article reports"),
  citedSources: z
    .array(z.string())
    .max(10)
    .describe("People, documents, agencies or outlets the article cites as its sources"),
  gaps: z
    .array(z.string())
    .max(8)
    .describe("Questions the article leaves unanswered or angles it did not pursue"),
  idea: z.object({
    title: z.string().describe("Punchy episode title for OUR show covering this story with a distinct lens"),
    angle: z.string().describe("Our angle — differentiated from the article's, one sentence"),
    summary: z.string().describe("2-3 sentence outline of what our episode covers"),
    rationale: z.string().describe("Why this story matters to a Palm Beach County construction/real-estate audience"),
  }),
})

export type ArticleAnalysis = z.infer<typeof analysisSchema>

/** Strip an HTML document to readable text. Crude but dependency-free; paywalled
 * or JS-rendered pages degrade to whatever text is server-rendered. */
export function htmlToText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<(?:nav|header|footer|aside|form|noscript)[\s\S]*?<\/(?:nav|header|footer|aside|form|noscript)>/gi, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<br\s*\/?>|<\/p>|<\/div>|<\/h[1-6]>|<\/li>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&quot;/g, '"')
    .replace(/&#x27;|&apos;/g, "'")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s*\n\s*/g, "\n")
    .trim()
}

const MAX_ARTICLE_CHARS = 12_000

export async function fetchCompetitorArticle(url: string): Promise<string> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 20_000)
  try {
    const res = await fetch(url, {
      headers: {
        // A browser-ish UA: many news CMSes serve bots a consent shell.
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        Accept: "text/html,application/xhtml+xml",
      },
      signal: controller.signal,
      redirect: "follow",
    })
    if (!res.ok) throw new Error(`Article fetch failed (${res.status}) for ${url}`)
    const text = htmlToText(await res.text())
    const usable = usableFullText(text)
    if (!usable) {
      throw new Error(
        "Could not extract readable article text (likely paywalled or JS-rendered). Try a different URL or paste the idea manually.",
      )
    }
    return usable.slice(0, MAX_ARTICLE_CHARS)
  } finally {
    clearTimeout(timer)
  }
}

export async function reverseEngineerArticle(url: string): Promise<{ analysis: ArticleAnalysis; idea: IdeaRow }> {
  const sql = requireSql()
  await ensureSchema()
  const articleText = await fetchCompetitorArticle(url)

  const { output } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: analysisSchema }),
    system:
      "You are a story editor for 'Palm Beach County Weekly', a podcast on construction, real estate and " +
      "local government in Palm Beach County, Florida. You reverse-engineer competitor articles: identify the " +
      "story, its facts, its sourcing, and its blind spots — then pitch OUR OWN episode on the story with a " +
      "differentiated, locally-relevant angle (often built on the gaps the article left). Never propose simply " +
      "reading the competitor's work on air.",
    messages: [
      {
        role: "user",
        content: `Competitor article (from ${new URL(url).hostname}):\n\n${articleText}`,
      },
    ],
  })

  const refs = [`Competitor: ${new URL(url).hostname} — ${url}`, ...output.gaps.slice(0, 3).map((g) => `Gap: ${g}`)]
  const rows = (await sql`
    INSERT INTO podcast_ideas (title, summary, angle, rationale, source_refs, status, created_by)
    VALUES (${output.idea.title}, ${output.idea.summary}, ${output.idea.angle}, ${output.idea.rationale},
            ${JSON.stringify(refs)}::jsonb, 'proposed', 'article_analyst')
    RETURNING *`) as IdeaRow[]

  if (telegramEnabled()) await notifyIdeaProposed(rows[0]).catch(() => {})
  console.log(`[article_analyst] ${url} -> "${output.idea.title}" (${output.keyFacts.length} facts, ${output.gaps.length} gaps)`)
  return { analysis: output, idea: rows[0] }
}
