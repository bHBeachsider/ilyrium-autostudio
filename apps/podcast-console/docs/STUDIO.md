# The Agentic Podcast Studio

`apps/podcast-console` is an agentic podcast studio: autonomous agents propose episode ideas
from content sources, a human approves them in the in-app review queue (optionally mirrored to
Telegram), the console produces the episode (ElevenLabs audio + ffmpeg video, persisted to
Cloudflare R2), and distributes it across Transistor (RSS), the site-box website, YouTube, and
social clips.

```
 content sources ──sync──▶ content items ──▶ IDEA AGENT ──▶ proposed ideas
 (rss / permithub / local)                                       │
                                                     ┌───────────▼───────────┐
                                                     │   /review  (HITL)     │◀── Telegram mirror
                                                     │ approve / reject /    │    (optional)
                                                     │ request changes       │
                                                     └───────────┬───────────┘
                                                        approved │ (+ approved script in two-gate)
                                                                 ▼
                                       PRODUCTION JOB  script → audio → images → video → finalize
                                                                 │  (artifacts on R2)
                                                                 ▼
                                                        podcast_episodes (produced)
                                                                 │  distribute (per-channel opt-in)
                                          ┌──────────┬───────────┼─────────────┐
                                          ▼          ▼           ▼             ▼
                                      Transistor  site-box    YouTube      social clips
                                      (RSS live)  (via RSS)   (manual)     (assets+copy)
```

## The two invariants

1. **Approval is mandatory, enforced in code.** Nothing is produced without an `approved`
   idea (`lib/jobs.ts:createProductionJob`), and nothing distributes without a produced episode
   with durable media plus a per-channel enable (`lib/publish/index.ts`). The continuous loop
   stops at `proposed` by construction (`lib/loop.ts` never imports the job or publish modules).
2. **Idempotency everywhere.** Episodes upsert by `guid`; content items are unique per
   (source, external_id); distributions are unique per (episode, channel) and re-runs update in
   place; re-running `produce` resumes the active job instead of duplicating.

## Setup

Copy `.env.example` → `.env.local` and fill in what you use. Feature availability degrades
gracefully: no `DATABASE_URL` → DB routes 503 with a clear banner; no R2 → imports keep remote
URLs and production refuses to start; no Telegram/Transistor keys → those features are silently
off.

| Concern | Vars |
| --- | --- |
| Persistence | `DATABASE_URL` (Neon) |
| Media storage | `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_HOST` |
| Generation | `AI_GATEWAY_API_KEY`, `ELEVENLABS_API_KEY` (+ voices), `PERPLEXITY_API_KEY` |
| Ingest | `PBC_PODCAST_DIR`, `PERMITHUB_BASE_URL` + `PERMITHUB_ADMIN_TOKEN` (JWT), `PODCAST_RSS_URL` |
| Approval | `STUDIO_TWO_GATE` (`true` = idea **and** script gates) |
| Telegram mirror | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET` |
| Distribution | `PUBLISH_{TRANSISTOR,SITEBOX,YOUTUBE,CLIPS}_ENABLED`, `TRANSISTOR_API_KEY`, `TRANSISTOR_SHOW_ID`, `TRANSISTOR_PUBLISH` |
| Loop | `STUDIO_LOOP_ENABLED` (kill switch), `LOOP_SECRET`, `LOOP_MAX_IDEAS_PER_RUN`, `LOOP_MAX_ITEMS_SCANNED` |

## Workflow, end to end

### 1. Ingest episodes (Phase 1)

Three sources behind one interface (`lib/ingest/`): **local** producer files
(`PBC_PODCAST_DIR` week folders), the **PermitHub admin API** (best-effort; its backing table
is manually seeded), and any **RSS** feed. Producer scripts are normalized (`host_a` → `Host A`).

```bash
curl -X POST localhost:3000/api/episodes/import -H 'Content-Type: application/json' \
  -d '{"source":"local"}'                       # or permithub_api / rss (+ optional url, weekOf, limit)
# → {"scanned":1,"imported":1,"updated":0,"skipped":0,"errors":[]}   re-run → skipped, no dupes
```

Episodes appear in **/episode-archive** with a source badge and working players (audio copied
to R2). The archive's **Import** button does the same from the UI.

### 2. Ideas + approval (Phase 2)

```bash
curl -X POST localhost:3000/api/ideas/generate -d '{"count":5}'   # agent files 'proposed' ideas
```

Review them at **/review**: approve / request changes / reject, with an optional note. With
`STUDIO_TWO_GATE=true`, approving an idea drafts a script that needs its own approval. If
Telegram is configured, each proposal is mirrored with inline ✅/❌ buttons (webhook:
`/api/telegram/webhook`, register via `setWebhook` with `TELEGRAM_WEBHOOK_SECRET`); the app
stays authoritative on conflicts.

### 3. Produce (Phase 3) — with research + fact-check gates

On an approved idea, click **Produce** in /review (or drive it by API):

```bash
curl -X POST localhost:3000/api/ideas/<id>/produce        # 201 {job} — 409 unless approved
curl -X POST localhost:3000/api/jobs/<jobId>/step         # repeat until step=done
curl localhost:3000/api/jobs/<jobId>                      # poll status/artifacts
```

Each step call runs one bounded stage — **research → script → verify → audio → images →
video → finalize** — with artifacts persisted between steps, so serverless time limits
can't kill a production and failed steps retry without redoing earlier work.

**Verified content:** the `research` step retrieves real sources (Perplexity Search API,
domain-pinned to trusted local outlets + .gov via `RESEARCH_TRUSTED_DOMAINS`, full article
text via Jina Reader where not paywalled) and fails hard if nothing citable is found. The
script is written under strict sourcing rules (assert only what sources state, attribute
on air by outlet). The `verify` step then extracts every factual claim and judges it
against the actual source texts; unsupported claims trigger one automatic rewrite, and if
any survive, the job **fails at the gate** with a claim-by-claim report in /review (each
retry grants one more rewrite). Finalize appends a **Sources** section to the show notes,
which flows to Transistor descriptions and site-box. Provenance (brief + verdicts) lives
in the job's artifacts.

### 4. Distribute (Phase 4)

```bash
curl -X POST localhost:3000/api/episodes/<id>/distribute            # all enabled channels
curl -X POST ... -d '{"channels":["transistor"]}'                    # or a subset
```

- **Transistor** uploads audio and creates/updates the episode. It stays a **draft** unless
  `TRANSISTOR_PUBLISH=true` — flip that only when you mean to go live on the public feed.
- **site-box** consumes the Transistor RSS: set `PODCAST_RSS_URL=<feed url>` (reported in the
  distribution detail) in the site-box deployment; its `/podcast` page revalidates hourly.
- **YouTube** records a manual-export package (MP4 URL + drafted metadata) until OAuth is wired.
- **Clips** cuts 2–3 agent-picked highlights to R2 with drafted post copy.

Outcomes land in `podcast_distributions` and show as chips in the archive; failures are
recorded per channel, never silent.

### 5. The loop (Phase 5)

Register sources, then schedule ticks:

```bash
curl -X POST localhost:3000/api/sources -d '{"kind":"rss","name":"PBC news","config":{"url":"…"}}'
STUDIO_LOOP_ENABLED=true                                  # the kill switch, default OFF
curl -X POST localhost:3000/api/loop/tick -H "Authorization: Bearer $LOOP_SECRET"
```

A tick syncs enabled sources into `podcast_content_items` (cursor + unique-key dedup), runs the
idea agent under the per-run budgets, and logs a `podcast_agent_runs` row. Schedule it with
Vercel cron (GET `/api/loop/tick`, set `LOOP_SECRET`) or locally:

```bash
STUDIO_URL=http://localhost:3000 LOOP_INTERVAL_SECONDS=900 node scripts/loop.mjs
```

The loop fills the review queue and stops there — production and distribution always wait for
a human.

## Tests

```bash
pnpm test   # vitest: normalization, decision transitions, dedup, clip windows
```
