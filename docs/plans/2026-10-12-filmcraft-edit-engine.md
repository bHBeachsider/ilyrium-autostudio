# Spec: FilmCraft as the headless edit engine — Phase 0 bake-off + Phase 1 adapter (for Fable 5)

**Target executor:** Fable 5 (claude-fable-5) in a Claude Code lane at the repo root.
**Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`
**Working dir:** `apps/auto-studio/` (plus `harness/`, `tests/`, `manuals/`, `docs/`)
**Approach:** ADD a second edit engine behind `producer.assemble_cut`; do NOT remove or alter the
moviepy path; do NOT modify anything under `filmcraft/` (it is a pinned upstream clone, not our
code). Phase 0 is a measurement; Phase 1 is wiring. The default engine stays `moviepy` until Brad
flips it after reading the Phase 0 results.
**Context:** `docs/research/2026-10-12-filmcraft-assessment.md` (read it first — the verified
facts, the smoke numbers and the invariants table are there and are not repeated here).

---

## 0. Goal (one paragraph)

Prove, on real pipeline media, that FilmCraft 0.7.0 (`filmcraft-cli`, headless) can rebuild a cut
we already delivered — Kingsize CH 69 `cut_4`, 45 s, 16:9, full VO — deterministically from the
campaign's `project.json`, export it clean, hand it to Resolve, and render QA frames; then wire that
path into the producer as "cut-as-code" (`cut.jsonl` + `.fcproj` per cut) behind an engine switch,
traced through the harness, with moviepy untouched as the fallback.

---

## 1. Fixed facts (verified 2026-10-12; do not re-verify, do re-check if the binary changes)

- Binary: `C:\Users\bradu\Documents\ilyrium-autostudio\filmcraft\target\release\filmcraft-cli.exe`
  (0.7.0, commit `0541d4d`). `--help`, `commands`, `describe <id>`, `inspect`, `probe`, `render`,
  `export`, `run <script.jsonl | ->`, `mcp`. Global option `--project <p.fcproj>`.
- `run` executes one `{"id": "...", "params": {...}}` per line, prints one JSON line per step
  (`{"id","line","ok","result"}` or `{"id","line","ok":false,"error"}`), **stops at the first
  error**, and saves nothing unless the script ends with `file.saveAs`.
- Ids are deterministic for a fresh project: first `file.import`/`importDemoFootage` item → `1`,
  first `file.newSequence` → `8`, first `timeline.place` → clips `[10, 11]` (video, audio). Generate
  with predicted ids, then **verify with `inspect sequence`** — or drive `run -` over stdin and
  read ids from the result lines (do this in Phase 1 if prediction ever misses).
- Time: 1 s = 254,016,000,000 ticks. `timeline.place` accepts `seconds`; `markers.add` takes
  `time` in ticks.
- `file.newSequence` defaults to 23.976 fps — always pass `fps` (24 for Veo/Kling media; take it
  from the campaign/kernel), `width`, `height`, `sampleRate: 48000`.
- Export settings go in the script as a `file.exportMedia` step with `"wait": true` — never as
  `--settings '{json}'` on a PowerShell command line (quotes get stripped).
- NVENC (`"hardwareEncoding": "auto"`) defaults to ~1 Mbps: always set `bitrateMode`/`bitrateKbps`
  or `crf`.
- Oracle: `C:\Users\bradu\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe` (+ `ffprobe`).
- Smoke artefacts to reuse as templates: `_staging/filmcraft_smoke/smoke.jsonl`,
  `export_hw.jsonl`, `export_prores.jsonl`.

## 2. Guardrails (repo contract + lessons; all binding)

1. Read `CLAUDE.md` and `FINDINGS.md`. Every `filmcraft-cli` call from Python goes through new
   `harness/run.py` wrappers (F-0004). No raw `subprocess` to the binary anywhere else; add the
   lint rule to `harness/lint_no_raw_sdk.py`.
2. Python writes files with `write_text(encoding="utf-8")`; any `.ps1`/`.cmd` you write is
   ASCII-only; JSONL scripts are written by Python, not by PowerShell here-strings (F-0003).
3. `subprocess.run([...], encoding="utf-8", errors="replace")` — the renderer emoji crash
   (2026-08-04) came from cp1252 stdout.
4. Never `git add -A`. Stage files by name. Do not commit `filmcraft/`; add `filmcraft/` to
   `.gitignore` (one line) and record the pin in `.env` (`FILMCRAFT_PIN=0541d4d`).
5. No EC2, no cloud credits, no model calls needed for this spec. If `ec2_session` reports the box
   running, say so and stop it only if Brad says to — it is unrelated to this work.
6. One writer per `.fcproj`: never open the same project in the GUI/bridge while a script runs.
   No GUI build, no `--control` port, no `ui_*` tools anywhere in this spec.
7. Ask, don't assume: if the Kingsize campaign `project.json` or any take media path is missing
   locally (R2-only), stop and ask Brad which cut to use instead. Do not substitute.
8. Record Phase 0 results in `docs/research/2026-10-12-filmcraft-bakeoff-results.md` — not in
   chat. Decisions Brad makes go in the same file under "Decisions".

## 3. Phase 0 — bake-off (no production code changes)

Work in `_staging/filmcraft_bakeoff/`. Locate the campaign: `apps/auto-studio/outputs/` has a
directory starting `kingsize_mattress__channel_69_late-night_spot_` whose `project.json` holds
`cut_4` (selected takes, VO path, music bed path, duck value). Reference, not source of truth,
for the media list: `projects/kingsize_the_walk/`.

Steps:
1. **Inventory media** — for every selected take, the VO file and the music bed: run
   `filmcraft-cli probe <file>` and record codec/fps/sample rate. Add one Blender PNG sequence from
   `projects/` or `ilyrium-shots/keyframes/` if one exists locally (`probe --image-sequence`). A1.
2. **Hand-generate `cut.jsonl`** (a 40-line Python script, `_staging/filmcraft_bakeoff/make_cut.py`,
   is fine) in this order: `file.newProject` → `file.import {paths:[...all media...]}` (one call;
   ids follow path order) → `file.newSequence {name, width:1920, height:1080, fps, sampleRate:48000,
   video:3, audio:3}` → one `timeline.place {item, track:"V1", audioTrack:"A1", seconds}` per take
   in cut order (seconds = running sum of take durations from `probe`) → `timeline.place {item:<VO>,
   track:"A2", seconds:0}` → `timeline.place {item:<music>, track:"A3", seconds:0}` →
   `markers.add {target:"program", time:<ticks>, name:"scene_<n>", comment:<scene title>}` per
   scene → `essentialSound.setType` dialogue on the VO clip, music on the bed, then
   `essentialSound.generateDucking` (check exact params with `describe`; if the names differ from
   the assessment, use what `describe` says and note it) → `file.saveAs {path: cut_4.fcproj}`.
3. **Run and inspect** — `filmcraft-cli run cut.jsonl`; then `--project cut_4.fcproj inspect
   sequence > sequence.json`. Check: every take present in order; total duration vs the moviepy
   master (`ffprobe`) within 1 frame; last clip's `start` equals the sum of prior durations. A2.
4. **Determinism** — run steps 2–3 twice into separate dirs; diff `sequence.json` (strip nothing
   first; if only ids/timestamps differ, strip those and diff again) and the two `.fcproj` files
   minus `generator` and `view`. A3.
5. **Exports** (each a `file.exportMedia` step with `"wait": true`, appended to a copy of the
   script, run with `--project cut_4.fcproj`):
   - `h264_sw`: `format:"h264", bitrateMode:"crf", crf:18, hardwareEncoding:"off", loudnessLufs:-14`
   - `h264_nvenc`: `format:"h264", hardwareEncoding:"auto", bitrateMode:"vbr1Pass", bitrateKbps:12000, loudnessLufs:-14`
   - `prores_hq`: `format:"prores", proresProfile:"hq"`
   Record wall time per export and `render_fps` from the result JSON; compare with the moviepy
   assembly time if a log exists (else time `assemble_cut` once on the same project). For each
   output: `ffmpeg -v error -err_detect compliant -i <f> -f null -` must exit 0; run
   `apps/auto-studio/qc.py` on it. A4.
6. **Audio** — `ffmpeg -i h264_sw.mp4 -af ebur128=peak=true -f null -` → integrated LUFS within
   ±1 LU of −14; listen-check not required, but confirm the VO clip's ducking keyframes exist in
   `sequence.json`. A5.
7. **QA frames** — `filmcraft-cli --project cut_4.fcproj render --seconds <t> --out frames/<n>.png`
   at every marker; record per-frame time. A6.
8. **Resolve hand-off** — append `file.exportFcp7Xml {path}` and `file.exportOtio {path}` steps;
   import the XML into Resolve 20.3.3 **by script** (`manuals/davinci-resolve/agent_package/` has
   the API; `ImportTimelineFromFile`); verify clip count and markers via the API. If the Resolve
   scripting host is not running, write the exact manual import steps in the results doc and mark
   A7 "pending Brad". A7.
9. **Stability** — run the full script 10 times in a loop; count non-zero exits.
10. Write the results doc: a table A1–A7 with pass/fail and numbers, the stability count, the
    routing verdict, the kill verdict, and the open decisions from the assessment §9. Then
    **stop and report** — Phase 1 waits for Brad.

**Routing (decided 2026-10-12 after Phase 0; replaces the 3×-realtime mezzanine criterion):**
FilmCraft NVENC is the master export for assembled cuts — explicit `bitrateMode`/`bitrateKbps`
and `loudnessLufs` per delivery target. No ProRes mezzanine. `delivery.py`/ffmpeg keeps platform
cutdowns only.

## 4. Phase 1 — adapter + cut-as-code (only after Brad okays the Phase 0 results)

Deliverables, smallest version that works:
1. `harness/run.py`: `filmcraft_run(project_path|None, script_path) -> list[dict]`,
   `filmcraft_export(project_path, settings: dict) -> dict`,
   `filmcraft_render(project_path, seconds, out_png) -> Path`. Each emits a trace row with
   `script_sha256`, `filmcraft_version` (`--version`), exit code, wall ms, output sha256 and the
   first error line if any. Binary path from `FILMCRAFT_CLI` via `credential()`-style lookup;
   missing → clear error, never a fallback to PATH.
2. `apps/auto-studio/media/filmcraft_assembler.py` with `build_cut_script`, `assemble`, `export`,
   `render_frames`, `interchange` as sketched in the assessment §6. Sequence settings from the
   campaign/kernel; ducking and loudness from the same fields `post_production` uses today
   (`duck`, music gain) so a cut built either way has the same intent. *Phase 0 decisions (results
   doc, Decisions):* FilmCraft owns levels, nothing applied twice; colour matte on V1 + clips on V2
   + `clip.fitToFrame`; markers frame-quantised; learned ids persisted beside `cut.jsonl`; image
   sequences pre-wrapped to `.mov` via the harness.
3. `producer.assemble_cut(..., engine=os.getenv("ILYRIUM_EDIT_ENGINE", "moviepy"))` — dispatch
   only; the moviepy branch is byte-for-byte unchanged. Cut outputs under
   `outputs/<campaign>/cuts/<cut_id>/`; `project.json` cut entry gains `engine`, `fcproj`,
   `script_sha256`, `sequence_sha256`, `export_sha256`, `filmcraft_version`.
4. `tests/test_filmcraft_assembler.py`: script generation is pure (test it without the binary);
   an integration test that builds a 3-clip cut from `file.importDemoFootage` scenes, skipped
   unless `FILMCRAFT_CLI` is set.
5. `harness/lint_no_raw_sdk.py`: forbid `filmcraft-cli` / `FILMCRAFT_CLI` in `subprocess` calls
   outside `harness/run.py`.
6. `manuals/filmcraft/source/`: copy `filmcraft/docs/agents.md`, `docs/control-protocol.md`, and
   `filmcraft-cli commands --json > commands.json`; add the entry to `manuals/_versions.json`;
   run the `manual-to-agent-transform` skill → `manuals/filmcraft/agent_package/`; add the row to
   `manuals/README.md`.
7. `docs/STAGE_TOOLS.md` row 9: FilmCraft under "Wired" with one line; `.env.example` (if one
   exists) gains `FILMCRAFT_CLI`, `FILMCRAFT_PIN`, `ILYRIUM_EDIT_ENGINE`.
8. Conventional commits, one per deliverable (`feat(edit): …`, `test: …`, `docs: …`). Do not flip
   the default engine.

Out of scope for Phase 1 (later phases, separate specs): `select_take`/`reassemble_cut` through
the adapter, the cut ledger record type, contact sheets into `run_style_validation`, replacing
`otio_export.py`, any GUI/bridge/MCP-interactive work, kernel LUTs, 9:16 presets.

## 5. Acceptance

- Phase 0: results doc exists with A1–A7 filled, numbers not adjectives, and an explicit
  kill/routing verdict; no production file changed; `_staging/filmcraft_bakeoff/` holds the
  scripts and outputs.
- Phase 1: `pytest tests/test_filmcraft_assembler.py` green with and without `FILMCRAFT_CLI`;
  `python harness/lint_no_raw_sdk.py` green; `ILYRIUM_EDIT_ENGINE=filmcraft` assembles the demo
  3-clip cut end to end with a trace row per binary call; `ILYRIUM_EDIT_ENGINE` unset →
  behaviour identical to today (compare the moviepy output hash before/after).

## 6. Report back (end of each phase)

Reply with: the results-doc path; the A1–A7 table; wall times (sw / NVENC / ProRes / moviepy);
the determinism diff summary; the stability count; the routing and kill verdicts; the list of
decisions still open; and anything FilmCraft did that contradicts the assessment (so the
assessment gets corrected, not quietly worked around).
