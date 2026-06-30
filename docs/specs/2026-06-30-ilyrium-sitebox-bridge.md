# Spec — ilyrium ↔ site-box Video Bridge

**Date:** 2026-06-30 · **Status:** Design — decisions D1–D7 resolved; one enabling code change landed (`storage_manager` → `R2_PUBLIC_HOST`); bridge code itself unbuilt. · **Owner:** ilyrium AutoStudio
**Related:** [`docs/strategy/2026-06-30-content-distribution-plan.md`](../strategy/2026-06-30-content-distribution-plan.md) §7-B/§8.2 ·
`C:\Users\bradu\Documents\site-box\docs\superpowers\research\2026-06-27-sitebox-marketing-plan.md`

> Every column name, route path, and function signature below is taken from verified source
> files in `C:\Users\bradu\Documents\site-box` and `…\ilyrium-autostudio\apps\auto-studio`.
> This spec **extends** the site-box marketing plan ("1 article → N assets"); it does not
> re-decide what that plan already settled.

---

## 1. Context & purpose

site-box (`sitebox.build`) is a working Next.js 15 + Supabase news platform that publishes
SEO-optimized article pages from a daily RSS→Claude-Haiku ingest. ilyrium AutoStudio produces
finished videos and already delivers them to Cloudflare R2 with C2PA provenance behind a
non-delegable HITL release gate. **The gap is purely the connection**: there is no code path
that attaches an ilyrium video to a site-box article. This spec defines that bridge.

**Atomic unit:** one *cluster* = one site-box `Article`. The bridge **attaches** one master video
(+ optional poster/captions) to an *existing* article. It never creates articles and never
auto-publishes to social.

## 2. Goals / non-goals

**Goals**
- Add optional video fields to site-box `articles` and render a player + `VideoObject` JSON-LD.
- Define an authenticated `POST /api/video/attach` endpoint that attaches a released R2 video to an article.
- Define an ilyrium-side `site_box_client` that POSTs an assembled cut back to site-box.
- Preserve ilyrium's HITL release gate and C2PA / AI-disclosure end-to-end.

**Non-goals (this pass)**
- No implementation. No social auto-publishing (YouTube/X/LinkedIn stay separately, human-fed per the marketing plan).
- No change to the daily RSS ingest pipeline. No multi-cut galleries (last-cut-wins; see D4).

## 3. Data-model changes — site-box `articles`

Five **nullable** columns (video is optional; existing rows and the RSS ingest are unaffected).
Names follow the existing snake_case + `*_url` convention (`origin_url`, `image_url`).

| Column | Type | Null | Default | Purpose |
|---|---|---|---|---|
| `video_url` | `text` | yes | — | R2 public URL of the master MP4 (mirrors ilyrium `public_url`) |
| `video_poster_url` | `text` | yes | — | Poster still (keyframe or reuse `image_url`) |
| `video_duration_sec` | `integer` | yes | — | Runtime; drives `VideoObject.duration` |
| `video_captions_url` | `text` | yes | — | R2 URL of the `.vtt` from `delivery.build_captions()` |
| `video_meta` | `jsonb` | no | `'{}'::jsonb` | Provenance bag: `{campaign_id, cut_id, manifest_url, c2pa_signed, ai_disclosure, checksum, release{}, idempotency_key, generated_at}` + a `cuts[]` history array (D4) |

One `video_meta` jsonb (rather than many scalars) keeps the migration small, mirrors the existing
`sources jsonb` pattern, and absorbs C2PA / disclosure / release provenance without schema churn.

**Migration** (their convention — `db/migrations/YYYY-MM-DD_NNNN_*.sql`, idempotent, applied
manually via Supabase Dashboard → SQL Editor):

```sql
-- db/migrations/2026-07-01_0006_article_video.sql  (design-only; idempotent; all nullable)
alter table articles add column if not exists video_url          text;
alter table articles add column if not exists video_poster_url   text;
alter table articles add column if not exists video_duration_sec integer;
alter table articles add column if not exists video_captions_url  text;
alter table articles add column if not exists video_meta          jsonb not null default '{}'::jsonb;

create index if not exists idx_articles_has_video
  on articles (published_at desc) where video_url is not null;
```

**Type / data-access touch-points** (named, not implemented):
1. `lib/types.ts` — extend `Article` (L13-27) with optional `videoUrl/videoPosterUrl/videoDurationSec/videoCaptionsUrl/videoMeta`.
2. `lib/articles.ts` — add the 5 snake_case cols to `ArticleRow` (L23-39) and map in `rowToArticle()` with `?? null`.
3. `lib/pipeline/map.ts` — add the same fields to `ArticleInsert` (L6-22); the daily RSS ingest sets them `null`/`{}` (RSS has no video).
4. `db/seed-articles.mjs` — default video fields to `null`/`{}`.
5. `lib/pipeline/ingest.ts` upsert (`onConflict:"origin_url"`, ~L70) — **no change** (new columns pass through).

## 4. Ingest API contract — `POST /api/video/attach`

A new endpoint modeled on `app/api/cron/ingest/route.ts`. It **attaches** to an existing article;
it does not insert. (This is site-box's first POST *mutation* route; cron stays GET.)

**Runtime** (copied from the cron route): `runtime="nodejs"`, `dynamic="force-dynamic"`, `maxDuration=300`.

**Auth** — reuse the cron route's exact bearer pattern, fail-closed (500 if secret env unset, 401 on mismatch).
Recommend a **separate** `VIDEO_INGEST_SECRET` (ilyrium is a different host; don't share the cron secret) — see D2.

```ts
const secret = process.env.VIDEO_INGEST_SECRET;
if (!secret) return new Response("Server misconfigured", { status: 500 });
const auth = request.headers.get("authorization");
if (auth !== `Bearer ${secret}`) return new Response("Unauthorized", { status: 401 });
```

**Request JSON**

```jsonc
{
  "articleId": "string",         // REQUIRED (preferred key; matches articles.id)
  "slug": "string",              // OPTIONAL fallback key
  "videoUrl": "string",          // REQUIRED — R2 public URL of master MP4
  "posterUrl": "string|null",    // OPTIONAL
  "durationSec": 31,             // OPTIONAL positive int
  "captionsUrl": "string|null",  // OPTIONAL — .vtt R2 URL
  "meta": {                      // REQUIRED provenance → video_meta
    "campaignId": "biz_20260630_120000", "cutId": "cut_1",
    "manifestUrl": "https://…/campaigns/<id>/manifest.json",
    "checksum": "sha256:…", "c2paSigned": true,
    "aiDisclosure": "AI-generated video produced by ilyrium auto-studio",
    "release": { "published": true, "allowed": true, "enforced": true, "blockers": [], "qa_passed": true },
    "generatedAt": "2026-06-30T12:34:56Z"
  },
  "idempotencyKey": "string"     // REQUIRED — recommend "{campaignId}:{cutId}"
}
```

**Validation** → `400` unless valid; specifically:
- Neither `articleId` nor `slug` present → 400.
- `videoUrl` (and any `posterUrl`/`captionsUrl`) must be `https://` on the allowlisted public host (`R2_PUBLIC_HOST`) — blocks SSRF / arbitrary embeds.
- `durationSec` present and not a positive integer → 400. `idempotencyKey` missing → 400.
- **`meta.release.allowed !== true` → `422` Release-gate not passed** (hard refusal; never attach an unreleased video).
- Resolve row via service-role `select id from articles where id=$articleId` (or `slug` fallback). No row → `404`.

**Response**
```jsonc
{ "articleId":"…","slug":"…","videoUrl":"…","updated":true,"alreadyAttached":false }   // 200
{ "articleId":"…","updated":false,"alreadyAttached":true }                              // 200 idempotent replay
{ "error":"…" }                                                                          // 400/401/404/422/500
```

**Idempotency / write semantics**
- The write is a service-role **`update`** of the single resolved row — **not** an upsert. (Upsert-on-`origin_url` is RSS-only; ilyrium has no `origin_url`, so upsert here would create a phantom row — see contradiction C2.)
- Store `idempotencyKey` in `video_meta.idempotency_key`. If stored key == incoming key and stored `video_url` == incoming `videoUrl`, short-circuit → `alreadyAttached:true`.
- A new cut (different key) overwrites video fields — **last cut wins** (D4), matching ilyrium's `cut_1`→`cut_2` non-destructive cuts.

## 5. ilyrium side — `site_box_client`

**Location:** `apps/auto-studio/delivery/site_box_client.py` (co-located with `delivery.py`). It does
**not** render; rendering is the existing pipeline. Single responsibility: POST a released cut to site-box.

**How a cluster gets rendered (existing pipeline, unchanged):**
- `POST /pipeline/start` (`studio_pipeline_service.py`, ~L193-220) with `{prompt: <cluster brief>, mode: "auto_draft", images: [...]}`.
- `auto_draft` runs stages 1-6 then **pauses at stage 7 (Rights/Release, A4 — non-delegable)** = the HITL gate.
- On human approval, stage 8 runs `producer.assemble_cut(project, project_dir, upload_to_r2=True)` →
  `{cut_id, final_video, public_url, published, release_allowed, blockers, qa}` (`producer.py` ~L328+).
  *(The "nothing-to-assemble" early return at ~L351 yields a 3-key form — the client must treat that as failure.)*
- R2 (`utils/storage_manager.py`, **patched 2026-06-30**): keys `campaigns/{campaign_id}/final_commercial.mp4`
  and `…/manifest.json`; `public_url = {R2_PUBLIC_HOST}/{video_key}` when `R2_PUBLIC_HOST` is set (browser-public
  custom domain), else the legacy non-public `{R2_ENDPOINT}/{bucket}/{video_key}` fallback (D1).
- Variants/captions from `delivery.py`: `export_preset()`→`{base}_9x16.mp4`, `ai_cutdown()`/`make_cutdown()`→15s short, `build_captions()`→`{srt,vtt,cues}`.

**Proposed signature**
```python
def attach_video_to_article(*, article_id: str, cut: dict,
                            captions_url: str | None = None,
                            poster_url: str | None = None,
                            duration_sec: int | None = None) -> dict:
    """POST a released R2 master to site-box /api/video/attach. Refuses if the cut's release
    gate did not pass. Returns the parsed JSON response."""
```
**Behavior**
- **Guard first:** if `cut["release_allowed"] is not True` or not `cut.get("public_url")` → error WITHOUT POSTing (mirrors site-box's 422; defense in depth).
- Build the body (§4) sourcing `meta` from the cut's `release{}` + `campaign_id`/`cut_id`/`manifest_url`; `idempotencyKey=f"{campaign_id}:{cut_id}"`.
- Headers: `Authorization: Bearer {SITE_BOX_INGEST_SECRET}`. New ilyrium env: `SITE_BOX_BASE_URL`, `SITE_BOX_INGEST_SECRET` (== site-box `VIDEO_INGEST_SECRET`), and `R2_PUBLIC_HOST` (browser-public video host, D1).
- If `build_captions()` produced a `.vtt`, upload to R2 (`storage_manager.get_r2_client()`) at `campaigns/{campaign_id}/captions.vtt` and pass its public URL as `captionsUrl`.
- Retry policy per §7.

## 6. End-to-end sequences

**Option A — Manual (default per marketing plan)**
1. Human reviews the day's 15-30 clusters (pre-ranked by `signalCount`) — **cluster selection stays human**.
2. Picks 1-3; copies each article `id` (or `slug`) + title/dek/summary/topic/county.
3. Operator runs `POST /pipeline/start` `mode:"auto_draft"`, prompt built from cluster fields; UTM injected in the copy (`utm_campaign=daily-cluster`, `utm_content={article.id}`).
4. Stages 1-6 run under the cost gate (Veo 3.1 Fast / Kling, never Veo 3.0).
5. **Stage 7 PAUSES** — human reviews QA + release gate and approves.
6. Stage 8: `assemble_cut()` uploads master to R2; returns `public_url`, `release_allowed=true`, `cut_id`.
7. Operator runs `site_box_client.attach_video_to_article(...)` (small CLI). *Degenerate fallback:* `update articles set video_url=… where id=…` via Supabase SQL Editor.
8. site-box ISR (`revalidate=3600`) surfaces the video within the hour.

**Option B — Webhook auto-embed (deferred; "build when proven")**
- Steps 1-5 unchanged (**HITL is never removed**). On stage-8 success, ilyrium auto-invokes `site_box_client` (the *only* added automation — the link-back, not rendering or release).
- `POST /api/video/attach` validates (incl. `release.allowed===true`), resolves by `articleId`, idempotency-checks, `update`s the row. ilyrium records the response in cut graph provenance.
- Webhook failure never blocks the R2 upload — the master is already published and attachable later via Option A.

## 7. Article-page rendering — `app/article/[slug]/page.tsx`

`revalidate=3600` stays as the background refresh, but the **attach endpoint triggers on-demand `revalidatePath('/article/{slug}')` (D6/P2)** so a newly attached video goes live immediately, not within the hour. Render only when `article.videoUrl` is non-null (video-less pages are byte-identical to today).

- **Player:** an `<ArticleVideo>` between `<ArticleHeader>` and `<ArticleBody>`; native
  `<video controls preload="metadata" poster={videoPosterUrl ?? imageUrl}>` + `<source type="video/mp4">` + optional `<track kind="captions" … default>`.
- **AI-disclosure UI (required):** a visible badge near the player from `video_meta.ai_disclosure` ("AI-generated video — ilyrium auto-studio").
- **JSON-LD:** keep the existing `NewsArticle` (`<JsonLd data={newsJsonLd} />`); when `videoUrl` exists, add a `video` property:
  ```jsonc
  "video": { "@type":"VideoObject", "name":article.title, "description":article.dek,
    "thumbnailUrl":article.videoPosterUrl ?? article.imageUrl, "uploadDate":article.publishedAt,
    "contentUrl":article.videoUrl, "duration":isoDuration(video_duration_sec) /* "PT31S" */ }
  ```
  `isoDuration()` converts seconds → ISO-8601. When `videoUrl` is null the JSON-LD equals today's output.
- **`news-sitemap.xml`:** optionally add `<video:video>` for rows with `video_url` (uses `idx_articles_has_video`). Defer to P4 unless Google News video indexing is wanted at launch (D5).

## 8. Security · HITL · C2PA / disclosure

- **Auth/transport:** bearer secret (separate `VIDEO_INGEST_SECRET` recommended), fail-closed; host-allowlist all URLs to `R2_PUBLIC_HOST` (anti-SSRF / stored-XSS). Writes use the Supabase **service-role** client; public reads stay anonymous.
- **HITL — nothing auto-publishes:** stage 7 (A4) is the single release authority; `auto_draft`/`assisted`/`manual` all pause there; the bridge adds no bypass. Double-enforced: ilyrium client refuses unless `release_allowed`; site-box returns 422 unless `meta.release.allowed===true`. "Attach to article" ≠ "publish to social."
- **C2PA / disclosure retention:** `video_meta` stores `c2pa_signed`, `manifest_url`, `checksum` (mirrors the cut `release{}.checksum`); site-box never re-encodes (serves the exact R2 object). `ai_disclosure` is mandatory in the body and rendered visibly. The C2PA manifest stays in R2 (`campaigns/{id}/manifest.json`); site-box stores only the pointer + checksum.

## 9. Error handling · retries · partial failure

- **Idempotency key** `"{campaign_id}:{cut_id}"` stored in `video_meta.idempotency_key`; replay → `alreadyAttached:true`.
- **Retries (ilyrium client):** bounded exponential backoff, **max 3 attempts** (1s/4s/16s + jitter) per CLAUDE.md "after 3 attempts" rule; retry only `408/429/5xx`/network — never `400/401/404/422`. Safe because the server is idempotent.
- **Partial failure:**
  - R2 ok but attach failed → master already in R2 + project store; re-runnable via Option A; cut not rolled back.
  - Captions upload failed but video ok → attach with `captionsUrl:null`; backfill later.
  - 404 → wrong key or article not yet RSS-ingested; no write.
  - 422 → a bug (client should not have POSTed); alert, don't retry.
  - Supabase single-row `update` is atomic — all video columns or none.
  - Option B webhook failure never blocks delivery.
- **Observability:** ilyrium records the attach attempt+response in the cut's graph provenance; site-box logs `{articleId, idempotencyKey, updated|alreadyAttached}` (no secrets).

## 10. Phased rollout (aligned to marketing-plan roadmap)

| Phase | Window | Scope | Effort |
|---|---|---|---|
| **P0 — Schema + types + R2 host** | Days 0-30 wk1 | migration `0006_article_video.sql`; extend `types.ts`, `ArticleRow`/`rowToArticle`, `ArticleInsert`, seed defaults; **bind R2 custom domain + set `R2_PUBLIC_HOST` (D1)** | 2-3 h |
| **P1 — Render (read path)** | Days 0-30 wk1-2 | `<ArticleVideo>` + conditional `VideoObject` + AI-disclosure badge; vitest render test (hand-seeded row) | 3-4 h |
| **P2 — Attach endpoint (write path)** | Days 0-30 wk1-2 | `POST /api/video/attach`: auth, validation, 422 gate, idempotent `update`, **on-demand `revalidatePath` (D6)**; vitest route tests | 4-6 h |
| **P3 — `site_box_client` (Option A)** | Days 0-30 wk2-4 | `delivery/site_box_client.py` + CLI; guard, body build, caption/poster R2 upload, retries; manual E2E | 4-6 h |
| **P4 — Webhook (Option B)** | Days 31-60 | auto-invoke on stage-8; on-demand ISR; `news-sitemap` `<video:video>` | 3-5 h |
| **P5 — Scheduler tie-in** | Days 61-90 | hook the daily scheduler; human cluster-select + release-gate retained | folds into scheduler |

Bridge-specific P0-P4 ≈ **16-24 h**. Per-cluster cost unchanged (~$0.36; Veo 3.1 Fast / Kling).

## 11. Contradictions resolved

- **C1 GET vs POST:** cron is GET (Vercel constraint); attach is an external mutation → **POST** (first POST route in site-box; new test scaffolding).
- **C2 upsert vs update:** RSS ingest upserts on `origin_url`; attach must **`update`** the existing `id`/`slug` row — upsert here would create a phantom row.
- **C3 R2 public URL → fixed:** the S3-endpoint `public_url` 403s in a browser; `storage_manager` now emits `{R2_PUBLIC_HOST}/{key}` (D1).
- **C4 per-cluster vs per-cut → fixed:** last-cut-wins in scalar columns + a `video_meta.cuts[]` history array (D4).
- **C5 cluster shape:** ilyrium example used generic topic/county; the real contract uses site-box's `Topic` enum (8 construction values) + Florida counties.
- **C6 HITL placement:** all inputs agree (human cluster-select + non-delegable stage-7) — confirmed, do not "optimize" away.

## 12. Decisions (resolved 2026-06-30)

- **D1 — R2 public delivery → RESOLVED.** Serve from a **browser-public Cloudflare custom domain**
  (recommended `https://media.ilyrium.io`), not the S3 endpoint. `storage_manager.py` now builds
  `public_url` from `R2_PUBLIC_HOST` (falls back to the S3 form if unset). **Remaining manual infra step:**
  bind the domain to the `ilyrium-assets` bucket in Cloudflare R2 → Settings → Public access → Custom
  domains, then uncomment `R2_PUBLIC_HOST` in `.env`. (`r2.dev` only for the first smoke test — uncached/rate-limited.)
- **D2 — secret → RESOLVED:** mint a **separate `VIDEO_INGEST_SECRET`** (don't share `CRON_SECRET`).
- **D3 — key → RESOLVED:** `id` primary + `slug` fallback; the cluster payload carries **both**. Option A
  (manual) may paste the URL slug; Option B (webhook) must pass `id`.
- **D4 — multiple cuts → RESOLVED:** **last-cut-wins** in the scalar columns **plus** a `video_meta.cuts[]`
  history array, so multi-cut later is a UI change, not a migration.
- **D5 — sitemap video → RESOLVED:** **defer to P4** (the in-article `VideoObject` already gives video rich-result eligibility).
- **D6 — ISR latency → RESOLVED:** add **on-demand `revalidatePath('/article/{slug}')` in P2** (from the attach endpoint) — freshly attached videos go live immediately.
- **D7 — captions → RESOLVED:** host the `.vtt` on **R2, same public host** as the video (`campaigns/{id}/captions.vtt`) to keep `<track>` same-origin.

## 13. Source files (all verified to exist)

- **site-box:** `lib/types.ts`, `lib/articles.ts`, `lib/pipeline/map.ts`, `lib/pipeline/ingest.ts`, `db/migrations/`, `db/seed-articles.mjs`, `app/api/cron/ingest/route.ts`, `app/article/[slug]/page.tsx`, `news-sitemap.xml` route, `vercel.json`, `.env.local`.
- **ilyrium:** `apps/auto-studio/producer.py` (`assemble_cut`), `…/project_store.py` (`add_cut`), `…/utils/storage_manager.py` (`finalize_and_upload_campaign`), `…/delivery.py` (`build_captions`/`export_preset`/`make_cutdown`/`ai_cutdown`), `…/studio_pipeline_service.py` (`POST /pipeline/start`), **proposed** `…/delivery/site_box_client.py`.
