import Parser from "rss-parser"
import { ensureSchema, requireSql, type ContentSourceRow } from "@/lib/db"
import { generateIdeas } from "@/lib/agents/idea-generator"
import { notifyIdeaProposed, telegramEnabled } from "@/lib/telegram"

// The continuous idea loop's single tick: sync enabled content sources into
// podcast_content_items (cursor = last_synced_at, dedup = UNIQUE(source_id,
// external_id)), then run the idea agent with a bounded budget. It STOPS at
// 'proposed' — production and distribution are never called from here; both
// stay behind the human approval gate. Every tick logs a podcast_agent_runs row.

export type TickSummary = {
  sources: { name: string; kind: string; scanned: number; upserted: number; skipped?: string; error?: string }[]
  itemsUpserted: number
  ideas: { generated: number; proposed: number; deduped: number } | { skipped: string }
  runId: string | null
}

function maxIdeasPerRun(): number {
  const n = Number(process.env.LOOP_MAX_IDEAS_PER_RUN)
  return Number.isFinite(n) && n > 0 ? Math.min(10, Math.round(n)) : 5
}

/** Max feed entries examined per source per tick — the loop's scan budget. */
function maxItemsPerSource(): number {
  const n = Number(process.env.LOOP_MAX_ITEMS_SCANNED)
  return Number.isFinite(n) && n > 0 ? Math.min(200, Math.round(n)) : 50
}

type FeedItem = { guid?: string; link?: string; title?: string; contentSnippet?: string; isoDate?: string }

async function syncRssSource(source: ContentSourceRow, cursor: Date | null): Promise<{ scanned: number; upserted: number }> {
  const sql = requireSql()
  const url = (source.config?.url as string | undefined) ?? process.env.PODCAST_RSS_URL
  if (!url) throw new Error("rss source has no config.url")
  const parser: Parser<Record<string, never>, FeedItem> = new Parser()
  const feed = await parser.parseURL(url)
  const items = (feed.items ?? []).slice(0, maxItemsPerSource())
  let upserted = 0
  for (const item of items) {
    if (!item.title) continue
    // Cursor: skip entries older than the last sync when the feed provides dates.
    if (cursor && item.isoDate && new Date(item.isoDate) <= cursor) continue
    const externalId = item.guid || item.link || item.title
    const rows = await sql`
      INSERT INTO podcast_content_items (source_id, external_id, title, summary, url, payload)
      VALUES (${source.id}, ${externalId}, ${item.title}, ${item.contentSnippet ?? null}, ${item.link ?? null},
              ${JSON.stringify({ isoDate: item.isoDate ?? null })}::jsonb)
      ON CONFLICT (source_id, external_id) DO NOTHING
      RETURNING id`
    if (rows.length > 0) upserted++
  }
  return { scanned: items.length, upserted }
}

type Meeting = { title?: string; body?: string; date?: string; url?: string; jurisdiction?: string }

async function syncPermithubUpcoming(source: ContentSourceRow): Promise<{ scanned: number; upserted: number }> {
  const sql = requireSql()
  const base = (source.config?.baseUrl as string | undefined) ?? process.env.PERMITHUB_BASE_URL
  if (!base) throw new Error("permithub_api source has no config.baseUrl (or PERMITHUB_BASE_URL)")
  // Public, unauthenticated by design; degrades to [] server-side.
  const res = await fetch(`${base.replace(/\/+$/, "")}/api/admin/podcast/upcoming`, { cache: "no-store" })
  if (!res.ok) throw new Error(`PermitHub /upcoming returned ${res.status}.`)
  const body = (await res.json().catch(() => ({}))) as { meetings?: Meeting[] }
  const meetings = (body.meetings ?? []).slice(0, maxItemsPerSource())
  let upserted = 0
  for (const m of meetings) {
    const title = m.title || m.body
    if (!title) continue
    const externalId = `${m.date ?? ""}:${title}`.slice(0, 500)
    const rows = await sql`
      INSERT INTO podcast_content_items (source_id, external_id, title, summary, url, payload)
      VALUES (${source.id}, ${externalId}, ${title},
              ${[m.jurisdiction, m.date].filter(Boolean).join(" — ") || null}, ${m.url ?? null},
              ${JSON.stringify(m)}::jsonb)
      ON CONFLICT (source_id, external_id) DO NOTHING
      RETURNING id`
    if (rows.length > 0) upserted++
  }
  return { scanned: meetings.length, upserted }
}

export async function runLoopTick(): Promise<TickSummary> {
  const sql = requireSql()
  await ensureSchema()
  const startedRows = (await sql`
    INSERT INTO podcast_agent_runs (agent) VALUES ('loop_tick') RETURNING id`) as { id: string }[]
  const runId = startedRows[0]?.id ?? null

  const summary: TickSummary = { sources: [], itemsUpserted: 0, ideas: { skipped: "not run" }, runId }
  try {
    const sources = (await sql`
      SELECT * FROM podcast_content_sources WHERE enabled = true ORDER BY created_at`) as ContentSourceRow[]

    for (const source of sources) {
      const cursor = source.last_synced_at ? new Date(source.last_synced_at) : null
      try {
        let result: { scanned: number; upserted: number }
        if (source.kind === "rss") {
          result = await syncRssSource(source, cursor)
        } else if (source.kind === "permithub_api") {
          result = await syncPermithubUpcoming(source)
        } else {
          summary.sources.push({
            name: source.name,
            kind: source.kind,
            scanned: 0,
            upserted: 0,
            skipped: `${source.kind} sources are not synced by the loop (manual/import-only).`,
          })
          continue
        }
        await sql`UPDATE podcast_content_sources SET last_synced_at = now() WHERE id = ${source.id}`
        summary.sources.push({ name: source.name, kind: source.kind, ...result })
        summary.itemsUpserted += result.upserted
      } catch (err) {
        summary.sources.push({
          name: source.name,
          kind: source.kind,
          scanned: 0,
          upserted: 0,
          error: err instanceof Error ? err.message.slice(0, 200) : "sync failed",
        })
      }
    }

    const result = await generateIdeas({ count: maxIdeasPerRun() })
    summary.ideas = { generated: result.generated, proposed: result.proposed.length, deduped: result.deduped }
    if (telegramEnabled()) {
      await Promise.allSettled(result.proposed.map((idea) => notifyIdeaProposed(idea)))
    }

    if (runId) {
      await sql`
        UPDATE podcast_agent_runs
        SET counts = ${JSON.stringify({
          sources: summary.sources.length,
          itemsUpserted: summary.itemsUpserted,
          ...summary.ideas,
        })}::jsonb, finished_at = now()
        WHERE id = ${runId}`
    }
    console.log("[loop_tick]", JSON.stringify(summary))
    return summary
  } catch (err) {
    if (runId) {
      await sql`
        UPDATE podcast_agent_runs
        SET error = ${err instanceof Error ? err.message.slice(0, 500) : "tick failed"}, finished_at = now()
        WHERE id = ${runId}`
    }
    throw err
  }
}
