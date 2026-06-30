# ilyrium AutoStudio — Content Creation & Distribution Plan

**Date:** 2026-06-30
**Evidence base:** [`docs/research/2026-06-30-sandy-lee-claude-playbook.md`](../research/2026-06-30-sandy-lee-claude-playbook.md)
(media-intelligence analysis of YouTube `DnZ53NQXfuA`, *"The Mom Who Mastered Claude"*)
**Scope decisions:** focus = **ilyrium's own audience**; distribution = **design adapters (no build this pass)**;
channels = **YouTube, TikTok, Instagram, X** + **owned site (site-box)**.

---

## Context

The video is a step-by-step playbook for converting a personal brand into a *buying* audience
with Claude Code: 200→12k subscribers in a month, $5.5k/mo retainer + $3.5k brand deal, by
collapsing 24-48h/video of manual work into ~1h/day of agentic work *without* producing "AI
slop." This plan operationalizes that playbook for **ilyrium AutoStudio** — applying its method
to ilyrium's own audience growth, mapped onto the studio ilyrium already has (8-stage pipeline,
8+ render backends, `delivery.py` repurposing, C2PA provenance) and the owned-site surface
**site-box** (`sitebox.build`). It also reviews the current distribution infrastructure and
*designs* (does not build) the publishing layer needed to close the gap.

The single most important insight for ilyrium: the video's thesis is **"authentic, not
original" — copy proven formats, inject your own story/provenance.** ilyrium is structurally the
best possible embodiment of that thesis, because its differentiators (C2PA content credentials
via `c2pa_sign.py`, on-model bespoke characters via the `bespoke-character-pipeline`) are
*verifiable authenticity* — the literal antidote to "AI slop."

---

## 1. Strategic thesis (what the video proves, applied to ilyrium)

| Playbook principle (source) | ilyrium translation |
|---|---|
| **Positioning before production** (Ikigai blueprint) `[19:00]` | A brand "bible" fixes avatar, voice, pillars **before** any render — reuse `bible_scaffold.py` Stage-1 dimensions. |
| **Authentic, not original** `[30:31]` | Copy proven *formats*; inject ilyrium's story + **provable provenance** (C2PA) + bespoke characters. This is the brand's wedge. |
| **Packaging is the gate** (thumbnail+title+hook) `[1:02:55]` | Add a first-class **packaging step** (Nano-Banana-class thumbnail + title + 7-step hook) before publish. |
| **Repurpose to monetize** `[1:08:00]` | One master → many channel-native cuts + a B2B lead surface. ilyrium already owns the repurposing half (`delivery.py`). |
| **Memory + cadence beat bursts** `[1:14:21]` | Durable, updatable brand memory (`.md`/kernels) + a "do-it-then-change-it" weekly cadence. |

---

## 2. Positioning & audience

**Who ilyrium is (brand promise):** *an autonomous AI film & cartoon studio that proves it works
by shipping in public, with verifiable provenance.* Proof-by-output is the positioning.

**Two audience tracks (one studio, two avatars):**
- **Avatar A — Builders & creator-operators** (founders, marketers, creators evaluating AI
  video production). Reached by **build-in-public** content across YouTube/X/LinkedIn. This is
  the brand-awareness + studio-as-a-service demand track.
- **Avatar B — site-box's niche (Florida construction / PermitHub market)** — county-level SMB
  owners, contractors, decision-makers. Reached by **news-to-video** explainer content published
  on the **owned site (sitebox.build)** and syndicated to social. This is the SEO + qualified-lead track.

**Brand blueprint as a studio bible.** Run the Ikigai blueprint once per avatar and persist it as
a Stage-1 bible (`bible_scaffold.py`: Narrative/Character/World/Story/Production/Decision-Bank).
This is ilyrium's version of the video's `.md` "personal brand file" — versionable and re-trainable `[1:14:21]`.

---

## 3. Content pillars (each mapped to a real production path)

| # | Pillar | What it is | Studio path (reuse) |
|---|---|---|---|
| P1 | **Build-in-public / teardowns** | "How we made this film/cartoon"; the autonomous studio itself | `films/woods_of_west/render_film.py` + screen-share overlays |
| P2 | **Anti-slop provenance POV** | C2PA-signed shorts; bespoke-character on-model demos; "authentic, not original" | `c2pa_sign.py`, `bespoke-character-pipeline`, `media/astria_renderer.py` |
| P3 | **The work itself** | Films + satirist cartoons as native content | `films/…/render_film.py`, `apps/satirist/` creative loop |
| P4 | **News-to-video** (the outlier/signal engine, O1) | site-box daily clusters → 45-90s explainer + 9:16 Short | `studio_pipeline_service.py` brief→script→render → `delivery.py` |
| P5 | **Applied AI-content tutorials** | The Sandy-Lee method, demonstrated | screen-share capture → `delivery.py` cutdowns |
| P6 | **Case studies / monetization proof** | Client recaps, brand-deal results | edited recap via pipeline → `ai_cutdown` |

≥5 pillars, each tied to an existing path. P4 is the concrete realization of the video's
"find what's working → produce in your style" loop, with **site-box clusters as the signal source**
(ilyrium's analog to VidIQ outliers).

---

## 4. Production mapping (reuse, don't reinvent)

| Need | Existing asset | Call / entrypoint |
|---|---|---|
| Long-form 16:9 | film pipeline | `python -m films.woods_of_west.render_film --phase final --style <style>` |
| Short/ad pieces | studio service | `POST /pipeline/start {prompt, mode: auto_draft\|assisted}` → `producer.render_shot` / `assemble_cut` |
| Format variants | `delivery.py` | `export_preset(master, out, target)` for `9:16` / `1:1` / `16:9` |
| Short-form cutdowns | `delivery.py` | `ai_cutdown(project, out, seconds)` (LLM scene-select) / `make_cutdown(...)` |
| Captions | `delivery.py` | `build_captions(project, out)` → SRT/VTT |
| Packaging (P-stage) | `media/` renderers | thumbnail via `keyframe.py`/`apiframe.py`; title+hook from script stage |
| Brand memory | kernels / `project.json` | persist blueprint; "update bible" loop |
| Provenance + gate | `c2pa_sign.py`, `release_gate.py` | C2PA manifest + non-delegable HITL approval |
| Publish source-of-truth | `utils/storage_manager.py` | R2 upload → public URL (`finalize_and_upload_campaign`) |

---

## 5. Per-channel distribution matrix

Five surfaces. Everything below the master is produced by **existing** `delivery.py`.

| Surface | Format(s) | Cadence | Length | Produced via | Role |
|---|---|---|---|---|---|
| **Owned site — site-box** (`sitebox.build`) | 16:9 embed + 9:16 | per cluster (1-3/day target) | 45-90s | `export_preset 16:9` + `ai_cutdown 9:16` | **SEO / Google News / lead capture / content source** |
| **YouTube** | long-form 16:9 + Shorts 9:16 | 1 long/wk + 3-5 Shorts/wk | 8-20m / <60s | film master + `ai_cutdown` | Authority + watch-time |
| **TikTok** | 9:16 | 5-7/wk | 15-60s | `ai_cutdown`/native vertical | Reach / top-of-funnel |
| **Instagram** | Reels 9:16 + 1:1 feed | 4-6 Reels/wk | 15-60s | `export_preset 9:16` + `1:1` stills | Reach + brand |
| **X / Twitter** | native clip 16:9/1:1 + thread | 3-5/wk | <2:20 | `make_cutdown` + still frames | Build-in-public / B2B |

**Repurposing flow — one production → ~8-12 assets** (exact `delivery.py` sequence):
1. `assemble_cut(project)` → master MP4 + R2 URL (`producer.py`)
2. `export_preset(master, out, "16:9")` → YouTube / site-box embed
3. `ai_cutdown(project, out, 45)` then `export_preset(..., "9:16")` → Shorts / Reels / TikTok
4. `export_preset(master, out, "1:1")` → IG feed / X
5. `build_captions(project, out)` → SRT/VTT (accessibility + silent-scroll retention)
6. still-frame grabs → quote cards (LinkedIn/IG/X)

**LinkedIn (inbound/outbound, Avatar B)** `[1:08:00]`: from each YouTube piece, generate 6 post
angles; engage → outreach. (Posting interim via Buffer per site-box plan; see §7-C.)

---

## 6. Cadence & 30/60/90 calendar

Principles from the video: **hook-first / CTA-last**, **"do it and change it"** (publish fast,
refine later), **tight targeting** (one avatar per piece).

| Window | Creation | Distribution |
|---|---|---|
| **0-30 days** | Stand up Avatar A+B bibles; produce P1/P2/P4 (1 film teardown + 4 news-to-video) | Manual posting from R2; site-box: manually link studio video on 2-3 article pages/wk |
| **30-60 days** | Add P5/P6; weekly film + daily short cadence; packaging step live | Per-channel matrix at half cadence; LinkedIn 6-angle repurpose |
| **60-90 days** | Full pillar rotation; first client case study | Full cadence; begin monetization motions (inbound triage + outbound) |

---

## 7. Distribution infrastructure review (current state)

Three surfaces exist today; only one publishes, and the social layer is absent.

### A. Studio delivery (ilyrium-autostudio) — **works, stops at R2**
- Format presets + captions + cutdowns: `apps/auto-studio/delivery.py`
  (`export_preset` L70, `ai_cutdown` L105, `make_cutdown` L130, `build_captions` L34).
- Cloud publish: `apps/auto-studio/utils/storage_manager.py` → Cloudflare R2 public URL.
- Provenance + gate: `c2pa_sign.py`, `release_gate.py` (HITL, fail-closed); asset graph `graph_sync.py`.
- **Gap:** output ends at an R2 URL + format variants. No platform reaches an audience by itself.

### B. Owned site — **site-box (`sitebox.build`) — working MVP, not yet wired to the studio**
- Next.js 15 + Supabase; daily RSS (18 feeds) → Claude Haiku classify (8 topics × 6 FL counties)
  → dedup → Supabase → SEO article pages (NewsArticle JSON-LD, Google News sitemap, `/local/[county]/[topic]`),
  OAuth + comments/signals. Cron: `vercel.json` daily ingest (`/api/cron/ingest`).
- **Already designed for ilyrium:** `site-box/docs/superpowers/research/2026-06-27-sitebox-marketing-plan.md`
  describes a "1 article → N assets" flow (ilyrium video from a cluster → YouTube auto-upload via
  Vercel Resumable Upload, LinkedIn via Buffer, X later).
- **Gap (code, not concept):** no `video_url`/`video_thumbnail` field on `articles`; no ilyrium
  ingest endpoint; no code bridge in either repo. It is also the **content source** for pillar P4.

### C. Social platforms (YouTube / TikTok / Instagram / X) — **not wired**
- `.env` holds X tokens but there is **no publishing code**, no scheduler, no analytics.
- Intent is on record: satirist spec `docs/specs/2026-06-11-ilyrium-satirist-studio-program.md`
  **§6 Distribution** — "platform adapters (X API; Instagram Graph API [business acct]; optional
  TikTok/YouTube via Ilyrium's video pipeline) → schedule/post. Reuses Ilyrium's final-publication
  HITL gate." Current reality (spec line 146): **"save file for manual posting — no auto-distribution."**

**Gap summary**

| Capability | Studio (A) | site-box (B) | Social (C) |
|---|---|---|---|
| Produce + format + caption | ✅ | n/a | n/a |
| Provenance + HITL gate | ✅ | partial (signals/auth) | planned |
| Publish to an audience | ❌ (R2 only) | ✅ (own site) | ❌ |
| Studio→surface bridge | — | ❌ no code | ❌ no code |
| Scheduling / analytics | ❌ | cron ingest only / GA4 UTM | ❌ |

---

## 8. Designed target architecture (DESIGN ONLY — not built this pass)

### 8.1 Publishing-adapter layer (new `apps/auto-studio/distribution/`)
A uniform adapter interface, one file per platform, plus a scheduler — **reusing**, not replacing,
the existing gate/storage/graph:

```
apps/auto-studio/distribution/
  base.py            # Adapter protocol: publish(asset, metadata) -> {post_url, platform_id}
  youtube_adapter.py # YouTube Data API (resumable upload)   — long-form + Shorts
  tiktok_adapter.py  # TikTok Content Posting API            — 9:16
  instagram_adapter.py # Meta Graph API (IG Business)        — Reels + feed
  x_adapter.py       # X API (tokens already in .env)        — native clip + thread
  scheduler.py       # queue/cron over approved cuts; reads project.json / graph
```
- **Inputs are already produced:** each adapter consumes `delivery.py` per-format renders +
  `build_captions` output + R2 URL from `storage_manager.py`.
- **Gate is reused:** publishing sits **behind `release_gate.py`** — nothing auto-publishes; every
  piece carries the AI-disclosure label + retained C2PA (per satirist spec safety section).
- **Telemetry reused:** record publish events + post URLs via `graph_sync.py`.

### 8.2 ilyrium ↔ site-box bridge (the highest-leverage near-term wiring — design only)
Aligns with site-box's existing marketing plan; **do not duplicate that doc** — implement its gap.
- **site-box side:** migration `articles += video_url, video_thumbnail, video_duration`; endpoint
  `POST /api/articles/ingest-video` (R2 URL + cluster id, `CRON_SECRET`-class auth); extend article
  JSON-LD with `VideoObject`; render a player/embed on `/article/[slug]`.
- **ilyrium side:** a small `site_box_client` that, given a cluster JSON, runs `brief→…→deliver`
  and POSTs the resulting R2 URL + thumbnail back to site-box.
- **Flow:** Option A (manual: pick cluster → run studio → paste link) ships first; Option B
  (webhook auto-embed) follows. Cost ≈ $0.36/cluster; high ROI (every video lands on an
  SEO page that drives watch-time + newsletter + signals).

### 8.3 Auth / keys gap table
| Channel | Have | Need |
|---|---|---|
| X | tokens in `.env` | confirm tier/cost (spec L154) |
| YouTube | — | Data API OAuth (site-box plan uses Vercel Resumable Upload) |
| Instagram | — | Meta Graph API + **Business account review** (spec L154) |
| TikTok | — | Content Posting API access |
| LinkedIn | — | Buffer (interim) → LinkedIn API (later) |
| site-box bridge | R2 creds (studio) | `video_*` schema + `ingest-video` endpoint |

---

## 9. Monetization ladder (from the video, applied)

`[1:06:31][1:07:00]` audience → inbound → first clients (retainer) → brand deals; the studio's
output is the proof-of-capability.

1. **Grow** via P1-P6 across the 5 surfaces (tight per-avatar targeting).
2. **Inbound** lands in email/DMs (sponsorship + "can you do this for us"). Triage weekly.
3. **Outbound** (Avatar B): LinkedIn 6-angle repurpose → engage → offer studio-as-a-service
   (news-to-video for construction SMBs, powered by site-box clusters).
4. **Convert** to retainers (recurring video production) + brand deals; publish case studies (P6),
   which feed the top of the funnel again.

---

## 10. Verification (how to prove this plan executed)

- **Media-intel:** `C:\Users\bradu\Downloads\Media_Intelligence_The_Mom_Who_Mastered_Claude.docx`
  exists (4 tables) + grounding note with timestamped citations.
- **Playbook completeness:** positioning (Avatar A/B), 6 pillars each mapped to a real path,
  5-surface matrix, repurposing flow citing `delivery.py` functions, 30/60/90 calendar, 3-surface
  infra review + adapter design, monetization ladder. ✅
- **No premise drift:** every cited file/function verified to exist (delivery.py L34/70/105/130;
  `release_gate.py`, `storage_manager.py`, `c2pa_sign.py`, `graph_sync.py`,
  `films/woods_of_west/render_film.py`, satirist spec §6).
- **Design-only:** no files created under `apps/auto-studio/distribution/`; site-box changes are
  specified, not applied.

---

## Appendix — reference index

- Studio: `apps/auto-studio/{delivery,producer,studio_pipeline_service,release_gate,c2pa_sign,graph_sync}.py`,
  `apps/auto-studio/utils/storage_manager.py`, `apps/auto-studio/bible_scaffold.py`,
  `apps/auto-studio/films/woods_of_west/render_film.py`, `apps/satirist/`
- Owned site: `C:\Users\bradu\Documents\site-box\` (`sitebox.build`),
  `site-box/docs/superpowers/research/2026-06-27-sitebox-marketing-plan.md`
- Spec: `docs/specs/2026-06-11-ilyrium-satirist-studio-program.md` §6 (distribution intent)
- Evidence: `docs/research/2026-06-30-sandy-lee-claude-playbook.md` (+ `.transcript.txt`)
