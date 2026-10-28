# FilmCraft — agent-readable manual (headless CLI, cut-as-code)

*From `source/agents.md` (SRC-FILMCRAFT-AGENTS, upstream `docs/agents.md`), `source/control-protocol.md`
(SRC-FILMCRAFT-CTRL) and `source/commands.json` (SRC-FILMCRAFT-CMDS, `filmcraft-cli commands --json`,
700 commands), all at pin `0541d4d` (0.7.0), plus the studio's Phase 0 measurements
(`docs/research/2026-10-12-filmcraft-bakeoff-results.md`, cited as BAKEOFF). Not the full 16-artifact
bundle; like the other packages here, the agent-readable manual only. Not approved for unsupervised use.*

## What it's for (in the pipeline)
Stage 9 **Edit**: the second edit engine behind `producer.assemble_cut` (`ILYRIUM_EDIT_ENGINE=filmcraft`;
default stays `moviepy`). A cut is a generated JSONL script → `.fcproj` → `inspect sequence` JSON → NVENC
master + QA frames + FCP7 XML for Resolve. Code: `apps/auto-studio/media/filmcraft_assembler.py`.

## Setup (the agent's preconditions)
- Binary from `FILMCRAFT_CLI` (absolute path, root `.env`); pin in `FILMCRAFT_PIN`. Never resolve it from
  `PATH`. The Windows MSI installs to `C:\Program Files\FilmCraft\filmcraft-cli.exe`, not on PATH
  (agents.md §1 "From an installed release").
- **Every call goes through `harness/run.py`** (`filmcraft_run`, `filmcraft_export`, `filmcraft_render`,
  `filmcraft_probe`, `filmcraft_inspect`). `harness/lint_no_raw_sdk.py` fails any other file that spawns it.

## The interface the studio uses
- `run <script.jsonl>`: one `{"id","params"}` per line → one `{"line","id","ok","result"|"error"}` per line;
  **stops at the first failure** unless `--keep-going` (agents.md §2b). Nothing is saved unless the
  script ends in `file.saveAs`, so treat a partial run as a failed cut (BAKEOFF §4).
- Exit status: 0 success, 1 a command failed, 2 usage error (agents.md §2b).
- Time is ticks, **254 016 000 000 per second**; commands also take `seconds`, `frame`, `timecode`
  (agents.md §2 Notes).
- Tracks are named `"V1"`/`"A2"` or by id; a missing track is an error, never another track. In
  `timeline.place`, `track` takes the picture, `audioTrack` the sound; **clip start and end snap to the
  nearest frame** (agents.md §2 Notes). `markers.add` times do **not** snap; quantise them yourself (BAKEOFF §4).
- Commands that act on the selection need their targets named (`clips`/`clip`, `items`/`item`), or
  they're disabled (agents.md §2 Notes). Always pass `clips` explicitly; never rely on selection.
- Offline media renders a placeholder; `export`/`render` name it on stderr and **exit 1**, and the
  export result lists it as `offlineMedia` (agents.md §2b). The harness rejects a non-empty `offlineMedia`.

## Procedures (the studio's cut recipe; command ids from commands.json)
1. `file.newProject` → `file.import {paths}` (item ids 1..N in path order) → `file.newSequence {name,
   width, height, fps, sampleRate}`. **Always pass `fps`**: the default is 23.976 (commands.json).
2. `file.newColorMatte {color, seconds}` → place it on **V1** (the pillarbox; `delivery.pillarbox` from the kernel).
3. `timeline.place` each selected take on **V2** (+ `audioTrack:"A1"` if it has sound), VO on A2, bed on A3.
   Clips land at **native pixel size**: follow with `clip.fitToFrame {clips}` (BAKEOFF §4).
4. Levels, applied once each: `clip.audioGain` (native audio; bed trim), `essentialSound.setType`
   dialogue/music, `essentialSound.set {clips, values:{ducking.enabled, ducking.reduceDb, ducking.fadeS}}`,
   `essentialSound.generateDucking {clips}` on the bed (it takes **only** `clips`; BAKEOFF §4).
5. `markers.add {target:"program", time, name, comment}` per scene, then `file.saveAs {path}`.
6. Learn clip ids with a dry run of steps 1–3 and bake them into the static script (sequence id =
   7 + items, matte = sequence + 1; clip ids skip; BAKEOFF §4). Persist them in `ids.json`.
7. Export: `file.exportMedia {path, format:"h264", hardwareEncoding:"auto", bitrateMode, bitrateKbps,
   loudnessLufs, wait:true}`, **always with an explicit bitrate** (NVENC's default was ~1 Mbps; BAKEOFF
   §4) and in the script, never as `--settings` JSON on a PowerShell line (assessment §2).
8. QA frames: `render --seconds S --out f.png` (0.26–0.40 s per frame on real media, BAKEOFF §2 A6).
   Hand-off: `file.exportFcp7Xml {path}` (Resolve 20.3.3 import verified, BAKEOFF §8) or `file.exportOtio`.

## Agent action boundaries
- **may**: generate and run cut scripts headless on project copies the producer owns; probe/inspect;
  export masters; render QA frames; write FCP7 XML/OTIO.
- **must not**: start the GUI's control channel (`filmcraft --control`, `FILMCRAFT_CONTROL_PORT`) or use
  bridge mode / `ui_*` tools. The port is loopback-only but **"has no authentication, so only enable it
  while you use it"** (control-protocol.md §Desktop control channel), and studio policy forbids it
  (Brad, 2026-10-12). Don't register an MCP server with write access outside a reviewed lane: the MCP
  server **has no folder confinement** and "can read and write wherever the user can" (agents.md §1).
  Don't open a `.fcproj` with a second writer while a script runs. Don't modify `filmcraft/` (pinned
  upstream clone).
- **escalate when**: a dry run's ids differ from the real run (id allocation changed: re-pin and
  re-baseline the golden test); `offlineMedia` is non-empty; `--version` or `FILMCRAFT_PIN` differs from
  the pinned 0.7.0 / `0541d4d`.

## Open questions
- FILMCRAFT-OQ-001: image sequences import at 29.97 fps with no CLI frame-rate override (BAKEOFF §4).
  The studio pre-wraps them to `.mov` with ffmpeg; the upstream fix is unknown.
- FILMCRAFT-OQ-002: export throughput on the laptop varies 6× run to run (ProRes 50–324 s, BAKEOFF §3).
  The cause is unmeasured (thermal? hybrid GPU?).
- FILMCRAFT-OQ-003: `music_mode: master` (song drives the cut) is not implemented in the adapter; it
  raises and the moviepy engine handles it.
