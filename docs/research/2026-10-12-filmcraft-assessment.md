# FilmCraft — assessment and integration plan for Ilyrium AutoStudio

**Date:** 2026-10-12 · **Status:** assessment complete, adoption gated on the Phase 0 bake-off
(spec: `docs/plans/2026-10-12-filmcraft-edit-engine.md`) · **Scope:** stage 9 Edit (stage key
`08_edit`, project home `07_post/`), with spill-over into QA (`08_qa/`) and delivery (`09_delivery/`).

## 0. Verdict

**Adopt FilmCraft as the headless assembly engine for the edit stage — behind an adapter, as
"cut-as-code" — and keep DaVinci Resolve as the finishing room.** Gate the switch on a half-day
bake-off against a cut we have already delivered (Kingsize CH 69 `cut_4`, 45 s). Keep the moviepy
stitch as the fallback engine until the bake-off passes. Do **not** make FilmCraft the delivery
encoder yet, and never put its `ui_*` tools in an automated path.

Why this and not more: the pipeline's weakest artifact today is the cut. `producer.assemble_cut`
→ `media/post_production.compile_final_video` is a fire-and-forget moviepy stitch — it produces an
mp4 and nothing else: no timeline, no frame-exact math, no markers, no inspectable state, and the
`*TEMP_MPY_wvf_snd.mp4` litter in `apps/auto-studio/` is what it leaves behind when it dies.
FilmCraft gives the edit stage what every other stage already has: a spec-like artifact
(`.fcproj` JSON + a JSONL command script) that is diffable, hashable, replayable and inspectable.
That is the whole case. The GUI, the Premiere parity, the copilot tools are side benefits.

Why not more: it is twelve days old.

## 1. What FilmCraft actually is (verified, not the brief)

Checked against the clone at `filmcraft/` (origin `storytold/filmcraft`, HEAD `0541d4d`
"Release prep: 0.7.0", 2026-10-12 05:44 -0400), its docs, and `filmcraft-cli.exe 0.7.0` built in
`filmcraft/target/release/` on Brad's laptop (RTX 3050 Ti Laptop + Intel Iris Xe).

| Claim in the brief | Verified state |
|---|---|
| Open-source Rust clean-room Premiere | Yes. MIT OR Apache-2.0, "no GPL/LGPL". ArtCraft team. 11.0k stars, 4.4k forks, 1,757 commits, **first commit 2026-09-30**, 309 open issues. Self-rated: alpha, "ready for real work ~56%". |
| Native codecs, no FFmpeg | Yes for decode: H.264, HEVC, ProRes, VP8/9, AV1, AAC, Opus, DNx, MJPEG, PCM are their own; MP3/FLAC/ALAC/Vorbis via `symphonia` (MPL-2.0). **Encode:** H.264 (software, or NVENC opt-in), ProRes 422 HQ, DNxHR, MJPEG, PNG/TIFF/EXR/DPX sequences, WAV/AAC/FLAC. **No software HEVC or AV1 export** (HEVC only via NVENC). ffmpeg is used only as their test oracle. |
| 254,016,000,000 ticks/s, no drift | Yes — Premiere's tick rate; `sequence_inspect` reports clip bounds in ticks and frames. |
| ~55 effects, Lumetri, keyframes | Lumetri basic/creative/vignette and 34 effect ids run on the GPU; **Lumetri curves/wheels/HSL, keys, masks, transitions run on the CPU**; no OCIO, LUT import exists. |
| Vulkan/Metal/DX12 | wgpu; Windows defaults Vulkan + DX12. **"Windows and Linux get far less testing than macOS"** (`docs/gaps.md` G4, G9); start-up crash on Intel UHD (#512) — Brad's laptop is a hybrid-GPU machine. |
| Memory safety → no crashes | Overstated: `docs/gaps.md` G4 "Crashes at start-up" is open; the platform/FFI crate allows `unsafe`. |
| Decoupled headless engine | Yes — `filmcraft-cli` runs the engine in-process with no window. The GUI binary is **not built yet** on Brad's machine (`filmcraft.exe` absent; only `filmcraft-cli.exe`). |
| MCP server with the listed tools | Yes — `filmcraft-cli mcp` on stdio. Both modes: `project_inspect`, `sequence_inspect`, `doc_inspect`, `command_list`, `command_run`, `command_batch`, `media_import`, `render_frame`/`render_preview`. **Bridge mode only** (needs the GUI running with `--control 9876`): `ui_inspect`, `ui_elements`, `ui_click`, `ui_drag`, `ui_key`, `ui_type`, `ui_screenshot`, `ui_control`. Tools carry MCP read-only/destructive hints. **No folder confinement: the server reads/writes wherever the user can.** The control port is unauthenticated loopback. |
| Interchange | FCP7 XML, FCPXML 1.9–1.11, **OTIO import + export** (`crates/interchange/src/otio.rs`; round-trips via `metadata.filmcraft`), CMX3600 EDL, AAF, OMF, ALE. |
| Project format | `.fcproj` = compact UTF-8 JSON with a schema version; media by path; atomic saves, auto-save, crash journal. |

Not in the brief but decisive for us:

- **`filmcraft-cli run <script.jsonl | ->`** runs a batch of `{"id","params"}` commands, one per
  line, prints one JSON result per line (`{"id","line","ok","result"|"error"}`), and **stops at the
  first error**. Ids it allocates are deterministic for a fresh project, but only the one-item case
  is easy to predict (first import → item `1`, first sequence → `8`, placed clips `[10, 11]`).
  *Corrected after Phase 0:* sequence id = 7 + number of imported items, and clip ids skip
  (link groups consume ids), so the adapter learns ids with a dry run of the placement steps and
  bakes them into a static script, persisting the learned ids beside `cut.jsonl` (identical in
  12/12 runs). This is the automated interface — no MCP client needed in the producer.
- *Phase 0:* `timeline.place` puts a clip at its **native pixel size** (Premiere behaviour), not
  scaled to the sequence; the adapter must `clip.fitToFrame`. Clip times snap to the frame grid;
  `markers.add` times do not (the adapter quantises them).
- **`filmcraft-cli export`** (synchronous) and `file.exportMedia {…, "wait": true}` (long job with
  MCP progress notifications) — so the 60-s MCP timeout that bites `generate_first_cut` is not a
  structural problem here.
- `file.exportMedia` takes `loudnessLufs`, `captionSidecar srt|vtt`, `burnCaptions`,
  `bitrateMode cbr|vbr1Pass|vbr2Pass|crf`, `crf`, `hardwareEncoding off|auto`, `proresProfile`,
  `range custom` + `startSeconds/endSeconds`, `alpha`.
- `essentialSound.setType dialogue|music|sfx|ambience` + `essentialSound.generateDucking {clips}`,
  BS.1770 / EBU R128 loudness meters. *Corrected after Phase 0:* `generateDucking` takes only
  `clips`; the ducking parameters are Essential Sound settings on the music clip
  (`essentialSound.set key=ducking.reduceDb|…`, stored as `against / reduce_db / fade_s`; defaults
  Dialogue, −15 dB, 0.8 s), and the keyframes land on the **music** clip.
- `markers.add {time|name|comment|color|durationFrames}`, `markers.exportCsv`.
- `file.import {paths, bin, imageSequence}` / `file.importImageSequence` — PNG sequences import as
  clips, **but at 29.97 fps with no CLI way to reinterpret the rate** (Phase 0); the adapter
  pre-wraps a sequence to a `.mov` at the sequence fps with ffmpeg (via the harness) before
  import. `probe <media> [--image-sequence]` gives media info as JSON.
- 700 engine commands on this build (`filmcraft-cli commands`), each with a typed param spec
  (`filmcraft-cli describe <id>`).

## 2. Smoke test on Brad's laptop (2026-10-12)

`_staging/filmcraft_smoke/` — headless, zero cost, synthetic "Dunes" demo clip (360 frames @ 24).

| Step | Result |
|---|---|
| `run smoke.jsonl` (newProject → importDemoFootage → newSequence 1920×1080@24/48k → `timeline.place {item:1, track:"V1", seconds:0}` → `markers.add` → `file.saveAs`) | all `ok:true`; `.fcproj` 5,549 bytes |
| `inspect sequence` | V1/A1 clips 10/11, 3,810,240,000,000 ticks = 360 frames, effects/markers listed |
| `render --seconds 1 --out frame1.png` | **78 ms** render, 178 ms wall, 1920×1080 PNG |
| export H.264 software, 0–2 s (48 frames) | 8.1 s, **6.0 fps**, High profile, 6.3 Mbps, AAC-LC 48 kHz |
| export H.264 `hardwareEncoding:auto` (NVENC) | 5.4 s wall, High profile — **but 1.0 Mbps**: the hardware path's default bitrate is low; the adapter must set `bitrateKbps`/`bitrateMode` explicitly |
| export ProRes 422 HQ | 6.3 s, **7.6 fps**, 128 Mbps, PCM 16-bit |
| ffmpeg strict decode (`-err_detect compliant`) of all three | exit 0, no warnings |

Reading: output is spec-clean, the toolchain is real, and frame renders are fast enough for QA
contact sheets. Export throughput (6–8 fps at 1080p whichever encoder) is bounded by the render
path, not the codec — and the synthetic source is generated per frame, so this number is **not**
the bake-off number. Real Veo/Kling H.264 sources (hardware-decoded through Media Foundation) are
what Phase 0 measures. Until then FilmCraft is an assembly engine, not the delivery encoder.

Two tool rules learned in the smoke (candidates for CLAUDE.md if they recur):
- Never pass `--settings '{json}'` on a PowerShell 5.1 command line — the quotes are stripped
  before the exe sees them ("key must be a string"). Put export settings in the JSONL script as a
  `file.exportMedia` step, or in a saved export preset.
- A `filmcraft-cli` export that outlives the 60-s device-bridge timeout is killed with it. Run
  exports from the producer (subprocess), not from an interactive bridge call.

## 3. Where it fits in the pipeline

Classification (same rule as the Google-tools decision, 2026-05-29): **FilmCraft has a real API
(CLI + JSONL + MCP) → it is an adapter-bus tool.** The GUI is a manual preview surface and nothing
more ("script, don't click" — the `ui_*` tools are exactly the thing that rule forbids in a
pipeline).

| Stage | Today | With FilmCraft |
|---|---|---|
| **9 Edit** (`07_post/`, key `08_edit`) | moviepy stitch (`post_production.compile_final_video`): concat + VO over ducked clip audio + music bed, libx264 re-encode; no artifact | Generated `cut.jsonl` + `.fcproj` per cut; colour matte (black, or kernel `delivery.pillarbox`) on V1, `timeline.place` per selected take on V2/A1 + `clip.fitToFrame`, VO on A2, music on A3; frame-quantised scene markers; Essential Sound ducking of the bed against Dialogue; `sequence_inspect` JSON saved beside the cut |
| take selection / reassembly | `select_take` + `reassemble_cut` re-stitch everything | regenerate the script and rebuild (idempotent) — a take swap is a diff in `cut.jsonl`; previews export only the changed range (`range: custom`) |
| **10 QA** (`08_qa/`) | per-take checks (`qc.py` ffprobe, `run_style_validation`, release gate) | per-take `qc` (incl. freezedetect) unchanged; masters get `qc` cut mode (decode/container/loudness only — freezedetect false-flags downscaled low-motion AI takes, Phase 0); plus `render --seconds` contact sheets at every marker off the **assembled** timeline (0.26–0.40 s/frame on real media) |
| audio (`06_audio/`) | moviepy gain hacks, `CLIP_AUDIO_DUCK`, ffmpeg `loudnorm` after the fact | FilmCraft owns the levels, nothing applied twice: `music_gain` → static bed trim, `duck` → native-audio level, bed ducked against Dialogue by Essential Sound; `loudnessLufs` at export |
| **delivery** (`09_delivery/`) | `delivery.py` ffmpeg presets (9:16, cutdowns, SRT) | **FilmCraft NVENC is the master export** for assembled cuts (explicit bitrate, `loudnessLufs` per delivery target; no ProRes mezzanine — decided after Phase 0). `delivery.py`/ffmpeg keeps platform cutdowns only. FilmCraft also produces the Resolve hand-off (`file.exportFcp7Xml` / `exportOtio`, full timeline with audio + markers; A7 passed) replacing the video-only, 24-fps-assumed `otio_export.py` |
| Resolve finishing | OTIO import of a video-only track; scripted DELETE unreliable | Resolve is no longer needed for assembly at all — only color, Fairlight and the master. The DeleteClips hole stops mattering because we never mutate in Resolve, we rebuild in FilmCraft |
| stages 1–8 (generation) | — | untouched |

## 4. Pipeline-invariant check

| Invariant | How the integration keeps it |
|---|---|
| Specs are the contract; nothing renders without `conformance.py` | The cut script is generated only from selected takes that already passed conformance; the adapter refuses a cut whose `project.json` has unselected shots. `cut.jsonl` becomes the edit-stage spec. |
| Takes are append-only; selection is reversible | FilmCraft never touches take files; `select_take` changes `project.json`, the script is regenerated and the cut rebuilt. Old `.fcproj`/exports stay under `cuts/<cut_id>/`. |
| Ledger is the audit spine, never rewritten | Each export appends one cut record: `script_sha256`, `fcproj_sha256`, `sequence_inspect` hash (the edit decision), export `sha256`, `filmcraft_version`, chained like the shot ledger. **Decision needed:** `provenance_record.schema.json` 1.0.0 is per-shot with `additionalProperties:false`, so cuts need their own record type (`ledger/cuts/<song-id>.jsonl` + `cut_record.schema.json` — recommended) rather than a schema bump. |
| Song IDs are owned | Cuts carry the song-id; no new IDs are minted. |
| The kernel governs the look | Sequence settings (size, fps, sample rate, working space) come from the kernel/profile, not FilmCraft defaults (`file.newSequence` defaults to 23.976 — we must pass `fps` explicitly). Grading stays in Resolve for now; a kernel LUT via `lut.import` is a later experiment, versioned with the kernel. |
| Release is gated; A4 non-delegable | Unchanged. FilmCraft exports are inputs to `run_release_qa`, never a bypass. |
| Harness tracing (FINDINGS F-0004, frequency 13) | Every `filmcraft-cli` call goes through `harness/run.py` (`filmcraft_run`, `filmcraft_export`, `filmcraft_render`) so the trace records the script hash, binary version, exit code, duration and output hashes. `lint_no_raw_sdk.py` gets a rule forbidding direct `subprocess` calls to the binary outside the harness. |

## 5. Risks and limits (the honest column)

1. **Maturity.** Alpha, built in twelve days largely by agents, 309 open issues, Windows least
   tested. Mitigation: pin the commit (`0541d4d`, 0.7.0) in `.env`, vendor the binary path, and
   make the bake-off script the upgrade regression test. Expect breakage between versions; never
   upgrade mid-production.
2. **Throughput on the laptop.** 6–8 fps render at 1080p in the smoke. If real media is no better,
   FilmCraft assembles and exports a ProRes/PNG mezzanine and ffmpeg/NVENC does delivery — that is
   a routing decision, not a kill. The Ubuntu GPU box (Linux NVENC) is a later option for batch
   exports; don't start it for this.
3. **Hybrid GPU / GUI stability.** #512 Intel crash risk applies to the GUI, not the headless CLI.
   Build the GUI only for preview sessions; if it crashes, wait for the 0.7.0 MSI.
4. **NVENC defaults are wrong for us** (1 Mbps). Set `bitrateMode`, `bitrateKbps` or `crf` per
   preset in the adapter; never rely on defaults.
5. **Security of the control surfaces.** No folder confinement; unauthenticated loopback control
   port. Treat like Resolve scripting (full user rights): headless mode from trusted lanes only;
   never leave `filmcraft --control` running unattended; no bridge server in `.mcp.json` at the
   autostudio root.
6. **One writer per `.fcproj`.** The producer owns the project file during an automated run; a
   Claude Code MCP session works on a copy or after. (The studio-MCP zombie-process lesson,
   2026-08-04, applies here too.)
7. **Nested clone.** `filmcraft/` sits untracked inside the autostudio repo (no `.gitmodules`,
   not in `.gitignore`). Decide: gitignore it and pin by commit (recommended), or move it out.
   Do not commit it.
8. **Codec edges irrelevant to us** (10-bit 4:2:2 camera media, RAW, AV1 export) — pipeline media
   is 8-bit 4:2:0 H.264 mp4 + AAC/MP3/WAV + PNG sequences, all covered.
9. **Colour.** rec709 working space, no OCIO. Fine for AI-generated clips; heavy grading stays in
   Resolve.
10. **`run` stops on first error and nothing is saved until `file.saveAs`** — good for atomicity,
    but the adapter must treat a partial run as a failed cut, not a partial one.

## 6. Integration architecture (what the lane builds)

```
apps/auto-studio/
  media/filmcraft_assembler.py      the adapter (new)
    build_cut_script(project, cut, profile) -> cut.jsonl      (deterministic ids, kernel-derived sequence settings)
    assemble(project_dir, cut_id)   -> run cut.jsonl via harness.filmcraft_run; save <campaign>.fcproj; write sequence.json
    export(cut_dir, preset)         -> file.exportMedia (wait) via harness.filmcraft_export; returns path + sha256
    render_frames(cut_dir, times)   -> PNG contact frames via harness.filmcraft_render
    interchange(cut_dir, fmt)       -> file.exportFcp7Xml / exportOtio for Resolve
  producer.assemble_cut(..., engine=ILYRIUM_EDIT_ENGINE)   dispatch: "moviepy" (default until bake-off passes) | "filmcraft"
  outputs/<campaign>/cuts/<cut_id>/ {cut.jsonl, <campaign>.fcproj, sequence.json, master.<ext>, frames/, <campaign>.xml|.otio}
  project.json cuts[]: + engine, fcproj, script_sha256, sequence_sha256, export_sha256, filmcraft_version
harness/run.py: filmcraft_run / filmcraft_export / filmcraft_render (traced); lint rule for raw subprocess use
ilyrium-shots/ledger/cuts/<song-id>.jsonl + cut_record.schema.json        (pending Brad's decision)
manuals/filmcraft/source/ {agents.md, control-protocol.md, commands.json}  -> agent_package via manual-to-agent-transform
.env: FILMCRAFT_CLI=<abs path>, FILMCRAFT_PIN=0541d4d, ILYRIUM_EDIT_ENGINE=moviepy
docs/STAGE_TOOLS.md row 9: FilmCraft moves to "Wired" when Phase 1 lands
```

Interactive use (not in the automated path): register the headless server in Claude Code —
`claude mcp add filmcraft-headless -- <abs>\filmcraft-cli.exe mcp --project <cut>.fcproj` — for
an editor-in-the-loop lane: `sequence_inspect` → `command_batch` → `render_frame` → `edit.undo`.
Read-only tools can be auto-approved by their hints; edits ask.

## 7. Bake-off (Phase 0, half a day, zero cloud cost)

Rebuild **Kingsize CH 69 `cut_4`** (45 s, 16:9, full VO; `projects/kingsize_the_walk`,
`outputs/<campaign>/project.json`) from its selected takes with a hand-generated `cut.jsonl`.

Acceptance (all must pass):
- A1 **Media**: every media type the pipeline emits (Veo/Kling/Seedance/Grok mp4, ElevenLabs mp3,
  Suno mp3/wav, a Blender PNG sequence) imports (`probe` + `file.import`) with no offline media.
- A2 **Assembly**: script runs clean; `sequence_inspect` shows every take in order; total duration
  matches `project.json` within 1 frame; A/V offset at the last cut ≤ 1 frame.
- A3 **Determinism**: two runs → identical `sequence.json` (ids and timestamps stripped) and
  identical `.fcproj` bytes modulo `generator`/`view`.
- A4 **Export**: H.264 (CRF 18, software) and H.264 NVENC with explicit bitrate at 1080p; wall
  time recorded vs the moviepy path; ffmpeg strict decode clean; `qc.py` passes.
- A5 **Audio**: VO over ducked clip audio + music bed via Essential Sound; integrated loudness
  within ±1 LU of the delivery target, measured by ffmpeg `ebur128` as the oracle.
- A6 **QA frames**: `render` at every scene marker, < 0.5 s per frame.
- A7 **Resolve round-trip**: `file.exportFcp7Xml` (and OTIO) imports into Resolve 20.3.3 with all
  clips linked and markers present.

Kill criteria (any one → FilmCraft stays "inspect/preview only", moviepy stays default):
pipeline media that will not import; a crash in more than 1 of 10 headless runs; A/V drift
> 1 frame; non-deterministic sequences; Resolve cannot ingest the interchange.
~~Routing (not kill) criterion: if NVENC export is slower than 3× realtime on real media, FilmCraft
exports a mezzanine and ffmpeg/NVENC delivers.~~ *Superseded after Phase 0 (2026-10-12):* the
bottleneck is FilmCraft's render path, not the encoder, so a mezzanine made it slower (ProRes
189–324 s + ffmpeg 11 s vs FilmCraft NVENC 75 s for 49.7 s; moviepy 328 s). Routing: **FilmCraft
NVENC is the master export for assembled cuts** (explicit bitrate, `loudnessLufs` per delivery
target), no ProRes mezzanine; `delivery.py`/ffmpeg keeps platform cutdowns only.

**Phase 0 outcome (2026-10-12):** all of A1–A7 passed, A1 with partial coverage (no Veo/Seedance
media or Blender sequence on disk) and A4 except `qc.py` freezedetect (a source-content false
positive, see above). No kill criterion fired. The target fell back from `cut_4` to the current
recipe because the VO had been overwritten (FINDINGS F-0006). Details:
`docs/research/2026-10-12-filmcraft-bakeoff-results.md`.

Durable artifacts out of Phase 0: `docs/research/2026-10-12-filmcraft-bakeoff-results.md`,
`tests/test_filmcraft_assembler.py` (skips unless `FILMCRAFT_CLI` is set), and a FINDINGS entry
only if a failure class recurs.

## 8. Phases

| Phase | Scope | Effort | Gate |
|---|---|---|---|
| 0 Bake-off | §7 on Kingsize `cut_4`; results doc | 0.5 day | acceptance A1–A7 |
| 1 Adapter + cut-as-code | `filmcraft_assembler.py`, harness wrappers + lint rule, `assemble_cut(engine=…)`, `project.json` fields, `.env` keys, tests, `manuals/filmcraft` package, STAGE_TOOLS row | 1–2 days | moviepy still default; flip `ILYRIUM_EDIT_ENGINE` only after Phase 0 passes |
| 2 Selection + reassembly | `select_take`/`reassemble_cut` rebuild through the adapter; range-limited preview exports; cut ledger records | 0.5–1 day | ledger `chain_ok` on cut records |
| 3 QA + hand-off | contact sheets into `run_style_validation`; loudness report; FCP7 XML/OTIO export replaces `otio_export.py`; `markers.exportCsv` → `edit_notes.md` | 1 day | one real project finished in Resolve from a FilmCraft hand-off |
| 4 (later) | Editor-agent lane at A2 via headless MCP on a copy; kernel LUT; FilmCraft delivery presets (9:16) replacing ffmpeg cutdowns if they validate; GUI preview sessions | — | each its own decision |

## 9. Decisions needed from Brad before Phase 1

1. Cut provenance: separate `ledger/cuts/<song-id>.jsonl` + `cut_record.schema.json`
   (recommended) vs bumping `provenance_record.schema.json`.
2. The nested clone: gitignore + pin `0541d4d` (recommended) vs move out / install the 0.7.0 MSI
   (`C:\Program Files\FilmCraft\filmcraft-cli.exe`) once published.
3. Build the GUI now for preview (`cargo build --release -p filmcraft`; hybrid-GPU risk) or wait
   for the MSI.
4. Confirm the bake-off target is Kingsize CH 69 `cut_4` (alternative: KING SIZE v3).

## Sources

- Clone: `filmcraft/` (origin https://github.com/storytold/filmcraft, HEAD `0541d4d`) — `README.md`
  (Formats and codecs, Export, Interchange, Status), `docs/agents.md` (MCP tools and modes),
  `docs/control-protocol.md`, `docs/gaps.md` (G3, G4, G5, G9, G10), `docs/hardware-parity.md`
  (hardware encode/decode, GPU rendering), `docs/project-files.md`, `Cargo.toml`,
  `crates/automation/src/long_job.rs`, `crates/interchange/src/lib.rs`, `.mcp.json`.
- `filmcraft-cli.exe 0.7.0` on Brad's laptop: `--help`, `commands` (700), `describe timeline.place`,
  `describe markers.add`, `describe file.import`, and the smoke runs in `_staging/filmcraft_smoke/`.
- Autostudio: `apps/auto-studio/producer.py` (`assemble_cut`), `media/post_production.py`,
  `otio_export.py`, `delivery.py`, `qc.py`, `release_gate.py`, `harness/run.py`,
  `harness/lint_no_raw_sdk.py`, `FINDINGS.md` (F-0004), `agents/stage_08_edit/v1/`,
  `docs/STAGE_TOOLS.md`, `manuals/README.md`, `ilyrium-shots/provenance_record.schema.json`,
  `projects/new_harnomy_usa/` layout.
