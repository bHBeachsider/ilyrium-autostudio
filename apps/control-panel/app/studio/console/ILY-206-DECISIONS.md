# ILY-206 Phase 1, slice 1 (tasks 11 and 13): decisions

Spec: `docs/specs/2026-11-10-ilyrium-console-resolve-style.md`. This slice adds routed pages
under `/studio/console/[page]` with a shared layout that keeps Run alive, and a scoped key
registry that replaces the document and window key listeners.

## 1. No react-hotkeys-hook, no zustand

The spec's stack table names both. Neither is added; `package.json` and `pnpm-lock.yaml` are
unchanged.

- react-hotkeys-hook only binds keys. The cheat sheet and the palette would still need our
  own table, so it adds nothing for the "cheat sheet equals the registry" requirement.
- Its modifier and key-name semantics for Ctrl+K, `?` and backslash could not be verified
  offline, and the bug being fixed (a bare `k` firing on Ctrl+K) is exactly a modifier
  semantics question. Here it is a pure function with unit tests.
- vitest runs in plain node with no jsdom. The dispatch logic (`keys/match.ts`,
  `keys/store.ts`) is pure so the guards are covered by unit tests; `KeysProvider.tsx` is a
  thin shell around one `window` listener.
- zustand is not needed: the only shared state is the key store, held in a context. The API
  mirrors `scopes`, so swapping the library in later is cheap.

## 2. Keeping Run alive: React `Activity` (shipped, not the fallback)

`Workspace` lives in `console/layout.tsx`, above `[page]`, and renders Run itself inside
`RunSurface`, which wraps `<Activity mode="visible|hidden">`. `[page]/page.tsx` returns null
for Run, because a client component rendered by the page unmounts on every navigation.

Spike result (step 2): `import { Activity } from "react"` type-checks (there is no
`@types/react`, so it is `any`), renders under `next dev` without `cacheComponents`, hides
the subtree, cleans up its effects while hidden and re-runs them on reveal. The existing
`contract-smoke.spec.ts` expectation that returning to Pipeline re-fires `GET /pipeline`
passes unchanged. No hydration or Activity console errors in `console-routing.spec.ts`
tests 1 and 4. The documented fallback (CSS `hidden` plus an `active`-driven refetch) was
not needed. `Pipeline` and `ReviewPanel` still take an explicit `active` prop, so review
key ownership is correct under either mechanism.

`RunSurface` pauses every `<video>` and `<audio>` in its subtree when it hides, because
`display:none` does not stop playback.

Known consequence of Activity: on every reveal all effects re-run, so BriefPanel and
ScriptPanel reload from the server and overwrite unsaved local edits (they did the same
on any remount before). Stage, run, run list, prompt, notes and AssetGen state survive.
Pipeline's transient message banner (offline, saved, scaffolded) does not: it is cleared each
time Run becomes the visible page, as a remount used to do.

## 3. Slug map

| slug | kind | rail and palette label | what it is |
|---|---|---|---|
| `run` | run | Pipeline | today's pipeline domain (renamed "Run" is a later decision, the specs match `/^Pipeline/`) |
| `legacy-review` | legacy | Review Room | today's Neon-fed review domain |
| `chat` | legacy | Studio Chat | today's studio domain |
| `script` | legacy | Ideation & Scripting | |
| `legacy-generation` | legacy | Asset Generation | |
| `legacy-assembly` | legacy | Timeline & Assembly | |
| `analytics` | legacy | Studio Control Plane | |
| `floor` | placeholder | Floor | Phase 2 |
| `library`, `review` | placeholder | Library, Review | Phase 3 |
| `sequence` | placeholder | Sequence | Phase 4 |
| `deliver` | placeholder | Deliver | Phase 5 |
| `sound` | placeholder | Sound | Phase 6 |
| `look` | placeholder | Look | Phase 7 |
| `stills`, `graph` | placeholder | Stills, Graph | Phase 8 |

- The `review` collision: the spec's `review` is the Phase 3 page, and task 11 says it
  serves a placeholder. Today's Neon-fed review domain therefore moved to `legacy-review`.
  Task 17 deletes every `legacy-*` row; the rail and the palette are both generated from
  the `PAGES` table, so their entries go with the row.
- The rail is `railPages()` (every non-placeholder page, in table order), labelled with
  `navLabelOf(page)`, the same function that labels the palette's "Go to X". A rename or a
  deleted row moves both. `registry.test.ts` ties each rail page to its `nav.*` palette
  command and label. (The first draft of this note claimed this while the rail was still a
  hard-coded list; that was wrong and is fixed.) The rail keeps today's seven buttons.
  Placeholders are reachable by URL and the palette only.
- An unknown slug calls `notFound()` and renders `console/not-found.tsx` inside the shell.
  A URL that matches no route (for example `/studio/console/run/extra`) is the root 404.

## 4. Redirects, and `app/page.tsx` is now unreachable

`next.config.js` `redirects()` sends `/` and `/studio/console` to `/studio/console/run`
with `permanent: false` (307, so no browser caches a 308 while the page list is moving).
Config redirects run before the filesystem, so the layout's data load does not run for them.

**Question for Brad:** `app/page.tsx` ("Studio OS is Live", has a BOM) is now dead code,
and any liveness probe on `/` starts getting a 307 instead of 200. It was left in place on
purpose (not part of this task). Delete it, or keep `/` as a page and redirect only
`/studio/console`?

`app/studio/console/page.tsx` was deleted; its body is `data.ts` (`loadConsoleData`),
called by `layout.tsx`. The layout keeps `dynamic = "force-dynamic"` so `next build` with
`DATABASE_URL=""` never runs the queries.

## 5. Chat is not kept alive

Only Run is kept alive. The chat transcript lives on the `chat` legacy page and unmounts
when you leave it; BoxPanel and QueueRail also unmount, and must refetch per visit
(`contract-smoke.spec.ts` requires it). The "Run's state (stage, chat) survives" half of the
spec's verify target is deferred to task 17, which puts chat in Run as a side panel.

## 6. Visible behaviour changes (intended)

Routing
- The page is in the URL. A reload stays on the same page; before, it always reset to Pipeline.
- Back and forward walk through pages.
- The stage stepper is hidden on placeholder pages (it showed on every page but Run and chat).
- `projId` resets to the first project if the selected one disappears after a refresh.

Keys (one dispatcher, one table)
- Bare shortcuts never fire with Ctrl, Meta or Alt held. This fixes Ctrl+K pausing the
  review video, Ctrl+A approving, Ctrl+R opening the reject dialog and blocking reload, and
  Alt+Arrow history being swallowed. Ctrl+K also no longer matches with Shift or Alt held.
- Shortcuts are off while focus is in a SELECT (the project picker and the B-take select
  used to leak keys). Checkbox focus (the auto-advance toggle) no longer suppresses them.
- Space and Enter are no longer swallowed on a focused button or link, so keyboard
  activation works. (Arrow keys and letters still act when a button has focus.)
- Caps Lock no longer breaks the letter shortcuts. Held keys do not re-fire their handler,
  except the frame-step arrows. A held key that matches a bound chord still has its default
  prevented (a held Space does not scroll the page); the repeat check runs after the focus
  and modal guards and swallows the default only.
- AltGr: on layouts that type backslash (or any printable non-letter) with AltGr, Windows
  reports Ctrl+Alt (or `getModifierState("AltGraph")`). A bare chord for a printable
  non-letter still matches then, so A/B cycling works on German and Nordic layouts. A letter
  with Ctrl+Alt never matches a bare letter chord.
- Shift+Left and Shift+Right still step a frame (they did before this change): the frame-step
  bindings list `shift+left` and `shift+right` as well. Other named-key chords stay exact,
  and Alt+Arrow is still left to the browser.
- Palette search keywords for the navigation commands are kept ("cost", "render", "cut",
  "takes", "llm", "stages"), carried by `keywords` on the page rows, plus the slug.
- While the reject dialog, palette or cheat sheet is open, review keys do not fire.
- Review keys only act when the review stage is the visible surface. Before, `a`, `r`, `n`,
  `p` and the rest acted on any Run stage and on any page that mounted a ReviewRoom, and `a`
  could append to the ledger from the wrong stage.
- There is one cheat sheet. The review room's inline copy is gone; its "? keys" button
  opens the shared one. The sheet lists every binding from the registry.
- The cheat sheet drops "1-8 jump to stage" and "Space plays the waveform" (neither was
  implemented), and the J/L "previous / next take" row (wrong: N and P do that). J is
  labelled "Play at half speed" (it was "slow reverse"; the code plays forward at 0.5x).
  Nothing was implemented to make a row true.
- The palette gains "Go to Ideation & Scripting" and "Go to Analytics / Queue" is now
  "Go to Studio Control Plane", matching the rail. Placeholder pages are in the palette as
  "Go to Floor", "Go to Library" and so on.
- The ⌘K button calls the palette directly (keyboard activation works; it no longer sends
  a synthetic keydown that reached the review key handler).

## 7. The 404 status finding

`/studio/console/bogus` returns **200** with `<meta name="robots" content="noindex">` and
the not-found UI in the shell, not 404. This is the documented `loading.tsx` behaviour:
the fallback starts the stream, which fixes the status. `/studio/console/run/extra`
returns a real 404 (root not-found). `generateStaticParams` and `dynamicParams` were not
added (their behaviour under a `force-dynamic` layout is undocumented), and `loading.tsx`
was kept because the task asks for it. `console-routing.spec.ts` test 3 asserts the
not-found UI, and the noindex tag when the status is not 404.

## 8. Notes for whoever touches this next

- `next dev` runs StrictMode, so Run's mount effects (and the effects it re-runs on reveal)
  run twice: a mount shows two `POST /pipeline/adopt`. That is not new (the session-restore
  effect has always done it). The specs therefore assert "no additional adopt after leaving
  and returning", not a literal count of one.
- The stepper hand-off: Workspace sets `pipeTarget`, pushes the Run URL, and clears the
  target in an effect once Run is the visible page. Pipeline's reveal effect runs in the same
  commit with the old target and adopts; the next render sees a null target and returns
  early. Without the clear, every reveal would adopt again. Because the target is gone by
  then, Pipeline keeps the "Opening <project> ..." hint (and the offline advice) in its own
  `opening` state, set when it adopts and cleared when adopt succeeds.
- A hand-off to a different project than the one Run holds clears the held run, state and
  gate config before adopting, so the old project's workspace is never shown or actionable
  under the new project's name. A hand-off to the project Run already holds keeps its state.
- `window.__ilyriumKeys` is the key store, exposed outside production only, so Playwright
  can check that every cheat-sheet row has a live handler.
- `router.refresh()` (after approve) re-renders the layout; Workspace uses the new props
  directly and never copies them into state.
- Stale generated types: `.next/types` and `.next/dev/types` from before this change
  referenced the deleted `console/page.tsx` and fail `tsc` until regenerated. They are
  git-ignored build output; delete them if `pnpm typecheck` complains on an old checkout.

## 9. Spec conformance (what this slice does and does not meet)

- **Task 11 (routed pages): partly met.** Routes, the shared layout, redirects, placeholders
  for the nine spec slugs that have no page yet, and keeping Run alive are done. The spec's
  "run is the only real page; every other slug serves a placeholder" is NOT met: `chat`,
  `script`, `analytics` and the three `legacy-*` slugs serve the live legacy pages instead.
  Reason: those pages hold working functions (review, chat and box control, analytics) that
  have no replacement until task 17; replacing them with placeholders would remove them.
  Task 17 deletes the `legacy-*` rows and turns the rest into the spec's pages.
- **Task 13 (key registry): met.** One dispatcher, one table, scopes, the cheat sheet
  generated from the table, no bare shortcut firing with Ctrl, Meta or Alt. The test that
  every cheat-sheet row has a live handler works at binding-id level (`__ilyriumKeys.has`),
  not by pressing each key.
- **Task 19 verify target "Run's state, chat included, survives": NOT met in this slice.**
  Run's stage, run and form state survive; the chat transcript does not (section 5). It is
  deferred to task 17.
- **Unknown slug:** HTTP 200 with a noindex tag and the not-found UI, not 404 (section 7).
- **Error boundaries** (`error.tsx` in `console/` and `studio/`) are not covered by a test.
