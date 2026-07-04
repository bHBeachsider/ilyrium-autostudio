import type { IdeaRow, ResearchBrief, ResearchSource } from "@/lib/db"

// Research step: turn an approved idea into a brief of real, dated, trusted-domain
// sources. Retrieval is Perplexity's Search API (raw ranked rows — we do our own
// claim/source alignment downstream; synthesized answers are never trusted), with
// best-effort full-article text via Jina Reader. Zero sources = hard failure:
// no episode is scripted without material to ground it in.

const SEARCH_API = "https://api.perplexity.ai/search"
const JINA_READER = "https://r.jina.ai/"

/** Local outlets + government domains the show treats as citable. ≤20 (API limit).
 * Override with RESEARCH_TRUSTED_DOMAINS (comma-separated). */
const DEFAULT_TRUSTED_DOMAINS = [
  "palmbeachpost.com",
  "wptv.com",
  "wpbf.com",
  "cbs12.com",
  "gotowncrier.com",
  "bizjournals.com",
  "wlrn.org",
  "sun-sentinel.com",
  "pbcgov.org",
  "discover.pbc.gov",
  "mypalmbeachclerk.com",
  "flgov.com",
]

export function trustedDomains(): string[] {
  const raw = process.env.RESEARCH_TRUSTED_DOMAINS
  if (!raw) return DEFAULT_TRUSTED_DOMAINS
  return raw
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean)
    .slice(0, 20)
}

/** Queries for the search API: the idea itself plus its cited headlines (which are
 * often more specific than the idea title). Capped at 3. */
export function buildQueries(idea: Pick<IdeaRow, "title" | "summary" | "source_refs">): string[] {
  const queries: string[] = [idea.title]
  const refs = Array.isArray(idea.source_refs) ? idea.source_refs : []
  for (const ref of refs) {
    // source_refs look like "S23. $60 Million Acquisition Closed… — Outlet"; strip the prefix.
    const cleaned = ref.replace(/^S\d+\.\s*/, "").split(" — ")[0].trim()
    if (cleaned && cleaned.length > 15 && !queries.includes(cleaned)) queries.push(cleaned)
    if (queries.length >= 3) break
  }
  return queries
}

export function outletFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return "unknown"
  }
}

/** Paywall/teaser heuristic: extracted bodies shorter than this are stubs, not articles. */
const MIN_FULLTEXT_CHARS = 600
const MAX_FULLTEXT_CHARS = 6000

export function usableFullText(text: string | null | undefined): string | undefined {
  if (!text) return undefined
  const trimmed = text.trim()
  if (trimmed.length < MIN_FULLTEXT_CHARS) return undefined
  return trimmed.slice(0, MAX_FULLTEXT_CHARS)
}

type SearchRow = { title?: string; url?: string; snippet?: string; date?: string }

async function searchOnce(query: string, apiKey: string): Promise<SearchRow[]> {
  const res = await fetch(SEARCH_API, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      max_results: 10,
      search_recency_filter: "month",
      // Deep page extraction: snippets carry article body text (~1-2k chars),
      // which is the primary verification material. (Do not combine with
      // max_tokens_per_page — the API 500s on the combination.)
      search_context_size: "high",
      search_domain_filter: trustedDomains(),
    }),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(`Perplexity search failed (${res.status}): ${detail.slice(0, 200)}`)
  }
  const body = (await res.json().catch(() => ({}))) as { results?: SearchRow[] }
  return Array.isArray(body.results) ? body.results : []
}

/** Best-effort clean article text via Jina Reader. Only attempted with a key —
 * Jina rejects anonymous calls from many networks — and failures/paywall stubs
 * degrade to the deep search snippet. */
async function fetchArticleText(url: string): Promise<string | undefined> {
  if (!process.env.JINA_API_KEY) return undefined
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 15_000)
    const res = await fetch(`${JINA_READER}${url}`, {
      headers: { Accept: "text/plain", Authorization: `Bearer ${process.env.JINA_API_KEY}` },
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) return undefined
    return usableFullText(await res.text())
  } catch {
    return undefined
  }
}

export async function buildResearchBrief(
  idea: Pick<IdeaRow, "title" | "summary" | "source_refs">,
): Promise<ResearchBrief> {
  const apiKey = process.env.PERPLEXITY_API_KEY
  if (!apiKey) {
    throw new Error("Research requires PERPLEXITY_API_KEY — verified episodes cannot be produced without it.")
  }

  const queries = buildQueries(idea)
  const rows: SearchRow[] = []
  for (const q of queries) {
    try {
      rows.push(...(await searchOnce(q, apiKey)))
    } catch (err) {
      console.warn("[research] query failed:", q, err instanceof Error ? err.message : err)
    }
  }

  // Dedupe by URL, preserve rank order, keep the strongest 8. Rows with no
  // extracted text are useless for verification — drop them.
  const seen = new Set<string>()
  const unique = rows.filter((r) => {
    if (!r.url || !r.title || seen.has(r.url)) return false
    if ((r.snippet ?? "").trim().length < 80) return false
    seen.add(r.url)
    return true
  })
  const top = unique.slice(0, 8)

  if (top.length === 0) {
    throw new Error(
      "Research found zero sources on trusted domains for this idea — cannot script a verified episode. " +
        "Check RESEARCH_TRUSTED_DOMAINS or the idea's specificity.",
    )
  }

  // Full text for the top few sources; the rest stay snippet-only.
  const sources: ResearchSource[] = []
  for (let i = 0; i < top.length; i++) {
    const row = top[i]
    const fullText = i < 4 ? await fetchArticleText(row.url!) : undefined
    sources.push({
      id: `S${i + 1}`,
      title: row.title!,
      url: row.url!,
      outlet: outletFromUrl(row.url!),
      date: row.date ?? null,
      snippet: (row.snippet ?? "").slice(0, 2500),
      ...(fullText ? { fullText } : {}),
    })
  }

  console.log(
    `[research] queries=${queries.length} rows=${rows.length} unique=${unique.length} sources=${sources.length} fullText=${sources.filter((s) => s.fullText).length}`,
  )
  return { sources, queries }
}

/** Render the brief as generateScript sources[] lines (existing grounding param). */
export function briefToScriptSources(brief: ResearchBrief): string[] {
  return brief.sources.map((s) => {
    const body = s.fullText ?? s.snippet
    return `${s.id} [${s.outlet}${s.date ? `, ${s.date}` : ""}] ${s.title} — ${body.slice(0, 1500)}`
  })
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
}

/** The "Sources" show-notes section as HTML: podcast apps and Transistor render
 * the links; site-box's tag-stripped snippet shows clean "Title — outlet" text
 * (raw URLs never appear as text anywhere). Prefers sources actually cited by
 * supported claims; falls back to the whole brief. */
export function sourcesSection(brief: ResearchBrief, usedIds?: Set<string>): string {
  const picked =
    usedIds && usedIds.size > 0 ? brief.sources.filter((s) => usedIds.has(s.id)) : brief.sources
  const items = picked.map(
    (s) => `<li><a href="${escapeHtml(s.url)}">${escapeHtml(s.title)}</a> — ${escapeHtml(s.outlet)}</li>`,
  )
  return `<p><strong>Sources</strong></p>\n<ul>\n${items.join("\n")}\n</ul>`
}
