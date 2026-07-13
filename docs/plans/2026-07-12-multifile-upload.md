# Spec: Multi-file, all-media persistent uploads in the pipeline Bible stage (for Fable 5)

**Target executor:** Fable 5. **Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`.
**Two apps touched:** the Next.js console `apps/control-panel/` (frontend) and the Python pipeline
service `apps/auto-studio/` (backend). Do NOT touch git. This is a focused bugfix + enhancement.

## Problem (Brad, verbatim intent)
In the pipeline "new project" → Stage 1 (Bible), attaching a file to an element: (1) each new
upload appears to REPLACE the previous one — you can't accumulate multiple files per element; and
(2) only images/video are accepted — must also ingest **text, images, video, audio (mp3), pdf**.
Fix so multiple files of any media type PERSIST per element, are listed, and each can be deleted.

## Ground truth (read first)
- **Frontend:** `apps/control-panel/app/studio/console/Stage1Bible.tsx`
  - `upload(dim, el, file)` (~L46-52): reads ONE `File` as base64, POSTs
    `{dim, key, filename, b64}` to `${pipe}/bible/${project}/media` (`pipe` = the :8800 service).
  - The file input (~L112-118): `<input type="file">` with **no `multiple`**, `accept` hardcoded
    to `video/*` OR `image/*` only, and `onChange` uses `e.target.files?.[0]` (first file only).
  - The checklist comes from `GET ${pipe}/bible/${project}/checklist` → elements have
    `{key,name,inputs,done,detail,value}`. There is NO per-element file list today.
- **Backend (`apps/auto-studio/studio_pipeline_service.py`):**
  - `bible_media` (~L763-782): already saves to `<bible>/<dim>/_media/{key}_{timestamp}{ext}` —
    so the SERVER does not overwrite (timestamped). The "overwrite" is a frontend display issue.
    Route: `POST /bible/{project}/media`.
  - `bible_checklist` (~L719-726) → delegates to `bible_scaffold.status_data(project)`.
- **`apps/auto-studio/bible_scaffold.py`** `status_data` (~L87-121): for a media element it sets
  `done = os.path.isdir(p) and any(os.scandir(p))` (~L110) — only checks non-empty, does NOT list
  files.

## Changes

### A. Backend — list + delete media (studio_pipeline_service.py + bible_scaffold.py)
1. **List files per element in the checklist.** In `bible_scaffold.status_data`, for each media
   element include a `files` array: `[{name, rel, size, kind}]` for every file in the element's
   `_media/` dir (sorted, newest last). `rel` = path relative to the bible dir (so the frontend can
   fetch/delete it). `kind` ∈ {image,video,audio,text,pdf,other} inferred from extension. Keep
   `done = len(files) > 0` for media elements. Don't break non-media elements.
2. **Serve a media file** (for preview/download): add `GET /bible/{project}/media/file?rel=<rel>`
   returning the bytes with a best-effort content-type. (Guard against path traversal: resolve
   under the bible dir and reject anything escaping it.)
3. **Delete a media file:** add `POST /bible/{project}/media/delete` `{rel}` → unlink the file
   under `_media/` (same traversal guard). Return `{ok:true}`.
4. `bible_media` stays as-is (timestamped, accumulates) — just confirm it never overwrites.

### B. Frontend — multiple, all-media, list + delete (Stage1Bible.tsx)
1. **Accept all media + multiple.** The file input:
   - add `multiple`
   - `accept="image/*,video/*,audio/*,.txt,.md,.json,.csv,.pdf,.rtf"` for any element whose
     `inputs` include `image`/`video`/`file`/`audio`/`refs`. (Keep a small type hint in the label
     like "+ attach image/video/audio/text".)
2. **Upload every selected file** (loop), not just `files[0]`. Upload them sequentially or in
   parallel; each hits the existing `/bible/{project}/media` endpoint. After all finish, `load()`
   to refresh the checklist. Show progress/count ("uploading 3…").
3. **Render the file list** for each element from the new checklist `files[]`: one row per file with
   its name, a small kind tag, a thumbnail for images (via the new `/media/file?rel=` endpoint),
   and a **× delete** button that POSTs `/bible/{project}/media/delete` then `load()`s.
4. The element dot/done state already flips via `done` — leave that; just also show the list so
   multiples are visible and persistent.
5. If `el.inputs` includes `audio` as a distinct type anywhere, treat it like the other media types
   (attachable). If the checklist's element `inputs` don't currently include "audio"/"pdf", that's a
   data question — DON'T invent inputs; just make the accept + upload permissive so any element that
   takes files can take these types.

## Guardrails
1. Scope: only `Stage1Bible.tsx`, `studio_pipeline_service.py`, `bible_scaffold.py`. No git.
2. No overwrite regressions: uploading N files to one element must leave N files on disk.
3. Path-traversal safe on the new file/delete endpoints (resolve + verify under the bible dir).
4. Don't break the existing text/prompt/generate controls in Stage1Bible.tsx.
5. Both servers may be running (:8800 uvicorn, :3000 next dev) — a code change to the Python
   service needs a restart to take effect; note that in the report. Next.js hot-reloads.

## Verification
- **Backend, offline (no box needed):** with the :8800 service importable, write a tiny test (or an
  inline python check) that: scaffolds/uses a temp project, POSTs two files to `/bible/.../media`
  for the same element, then GETs `/bible/.../checklist` and asserts the element's `files` has
  **2** entries; POSTs `/media/delete` for one and asserts it drops to **1**. Show the output.
  (You can call the handler functions directly with a fake request, or run uvicorn on a temp port
  and curl it.) Confirm `py_compile studio_pipeline_service.py bible_scaffold.py` is clean.
- **Frontend:** `apps/control-panel> npm run build` (or at least `npx tsc --noEmit`) to prove
  `Stage1Bible.tsx` type-checks. Confirm the input has `multiple` + the widened `accept`, the
  upload loops over all files, and a delete handler exists. (A full browser click-through needs the
  box for renders but NOT for upload/list/delete — those are pure file ops; if you run the stack you
  may smoke-test an upload, but it's optional.)

## Report
1. Files changed + what/why + key line ranges.
2. Backend verification output (2 files persist → checklist shows 2 → delete → 1).
3. Frontend type-check/build result + confirmation of multiple/accept/loop/delete.
4. Anything not wired + reason.
5. One paragraph for Brad: how multi-file upload + delete now works, and the reminder to RESTART
   the :8800 service to pick up the backend change.

Begin by reading Stage1Bible.tsx, then bible_media + bible_checklist in studio_pipeline_service.py,
then bible_scaffold.status_data.
