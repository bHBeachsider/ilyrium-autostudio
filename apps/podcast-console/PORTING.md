# Porting the Podcast Console into the Main Stack

This document is a handoff guide for incorporating the **podcast / episode generation console**
(currently living in this repo, mounted at `/sandbox`) onto an existing project spine.

The console is a **Next.js 16 App Router** feature. It is self-contained: a set of API routes
(the generation pipeline) plus a `/sandbox` page and its React components. It currently has **no
database and no auth** — projects, ideas, and the video playlist are session-only React state.

---

## 1. What the console does

A 4-step pipeline turns a topic into a narrated, illustrated video episode:

1. **Script** — `POST /api/generate-episode` → two-host dialogue script (AI Gateway, `openai/gpt-5-mini`).
2. **Scene visuals** — `POST /api/generate-images` → per-scene images anchored to the script
   (AI Gateway, `google/imagen-4.0-fast-generate-001`) + narration weights for timing.
3. **Voices** — `POST /api/synthesize` → narration audio (key-free Google Translate TTS, US/UK voices).
4. **Compose** — `POST /api/render-video` → Ken Burns slideshow synced to narration via `ffmpeg`.

There is also `POST /api/ingest` — pulls source material via Perplexity (`sonar`) and summarizes it.

---

## 2. Files to copy

### API routes (`app/api/`)
| Route | Runtime | maxDuration | External deps |
| --- | --- | --- | --- |
| `generate-episode/route.ts` | node (default) | 60 | `ai`, `zod` |
| `generate-images/route.ts` | `nodejs` | 300 | `ai`, `zod` |
| `synthesize/route.ts` | `nodejs` | 300 | (fetch only) |
| `render-video/route.ts` | `nodejs` | 300 | `ffmpeg-static` |
| `ingest/route.ts` | `nodejs` | — | `ai` + Perplexity fetch |

> The `runtime = "nodejs"` and `maxDuration` exports are **required** — these routes spawn
> ffmpeg and/or run long generation calls and must not run on the Edge runtime.

### Page + components
- `app/sandbox/page.tsx` — the console page (wraps everything in `ProjectsProvider`).
- `components/sandbox/` — `episode-generator.tsx`, `sample-episode.tsx` (player + playlist),
  `idea-board.tsx`, `project-switcher.tsx`, `data-source-pipeline.tsx`, `video-dimension.tsx`.
- `components/dashboard/header.tsx`, `components/dashboard/sidebar.tsx` — only if you reuse the
  existing chrome; otherwise mount the console inside your own layout (see §6).

### Lib
- `lib/projects.tsx` — session-only projects context (source of truth for ideas + playlists).
- `lib/video-playlist.tsx` — thin adapter over the projects context.
- `lib/sandbox-types.ts` — `Idea`, `GeneratedEpisode`, `EpisodeSegment`, `Stage`, seed data.
- `lib/utils.ts` — `cn()` helper (skip if the spine already has one; reuse theirs).

### Asset
- `public/sample-episode.mp4` (~19 MB) — the bundled demo episode. Optional; the player seeds
  each project's playlist with it. Drop it if you don't want a binary in the repo.

### shadcn/ui primitives required
`badge, button, card, dialog, dropdown-menu, field, input, label, progress, separator, switch,
textarea, toggle-group, avatar`

If the spine already uses shadcn/ui, install any missing ones with the shadcn CLI. These
components are built on **Base UI** (`@base-ui/react`), not Radix — make sure the spine's
versions match or re-add them from the spine's own registry.

---

## 3. Dependencies

Runtime:
```
ai@^6  @ai-sdk/react@^3  @ai-sdk/gateway@^3  zod@^4  ffmpeg-static@^5  lucide-react  class-variance-authority  clsx  tailwind-merge
```
UI styling: this repo uses **Tailwind v4** (`@tailwindcss/postcss`, `tw-animate-css`) and
**Base UI**. If the spine is on Tailwind v3, port the tokens from `app/globals.css` into the
spine's theme config and verify the components render.

This repo uses **pnpm** with one override (`hono@4.12.25`). Match the spine's package manager;
keep the override only if a transitive resolution problem appears.

---

## 4. Environment variables

| Var | Used by | Notes |
| --- | --- | --- |
| `AI_GATEWAY_API_KEY` | episode, images, ingest | Auto-present on Vercel. The Gateway routes OpenAI + Imagen with zero extra config. |
| `PERPLEXITY_API_KEY` | `ingest` only | Required only if you keep the data-ingest feature. |

No DB/auth vars today. `synthesize` needs no key (free TTS endpoint).

### Pulling env into a local checkout (Vercel CLI)
```bash
vercel login
# link the directory to the target Vercel project when prompted
vercel link --scope <TEAM_ID>
# pull env + project settings
vercel pull --environment=production --scope <TEAM_ID>
# or just the env file
vercel env pull .env.local --scope <TEAM_ID>
```
This repo's current Vercel scope is team `project-next1` (`team_D83ME2otD4yTngsa4CziJYYI`).
Add the two vars to the **target** project with `vercel env add AI_GATEWAY_API_KEY` etc., or via
the target project's dashboard.

---

## 5. The two things that break on a naive port

1. **ffmpeg** — `/api/render-video` resolves the binary from `ffmpeg-static`, which downloads on
   `postinstall`. Some CI/host setups strip it. If rendering fails with a missing-binary error,
   re-run the package's install script or provide a system `ffmpeg` and point the route at it.
   The route **must** be on the Node.js runtime (already declared).
2. **Edge runtime** — do not let the spine's defaults push these routes to Edge. Keep the
   `export const runtime = "nodejs"` lines. Edge has no child process / filesystem for ffmpeg.

Also confirm the spine's function timeout allows `maxDuration = 300` (Vercel Pro/Enterprise);
on lower tiers, image+render steps may need to be split or queued.

---

## 6. Mounting on the spine

- The console assumes the `@/*` path alias (tsconfig `paths`). Match it or rewrite imports.
- If you don't reuse `components/dashboard/*`, render the console body inside the spine's own
  shell. The minimum is: wrap the page in `ProjectsProvider` (from `lib/projects.tsx`), then
  render `<ProjectSwitcher />`, `<IdeaBoard />`, `<EpisodeGenerator />`, and `<SampleEpisode />`.
- Route it at whatever path the spine wants (e.g. `/console`, `/studio`); nothing is hardcoded to
  `/sandbox` except the file location.

---

## 7. Persistence (deferred — future work)

Projects/ideas/episodes are in-memory today. When you wire the spine's database (Neon is the
default here), persist: project (id, name), ideas (per project), and generated-episode metadata
(script, scene prompts, captions, narration weights). Re-render the MP4 on demand rather than
storing large blobs; uploaded videos can stay session-only or move to Blob storage. Auth/user
scoping is undecided — add it when the spine's account model is settled.
