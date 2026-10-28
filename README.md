# Ilyrium AutoStudio

An AI-native film studio. Bible → script → characters → environments → keyframes → shots
→ voice → music → edit → QA → key art, run as an agent pipeline with a provenance ledger.
The output is finished film, not clips.

> The previous README described an old Qwen + Stable Diffusion image script and no longer
> matched this repo. It is archived at `docs/README_image_pipeline.archived.md`.

## Start here

- **Working rules and invariants:** [`CLAUDE.md`](CLAUDE.md) — read before changing anything.
- **A specific film:** `projects/<name>/START_HERE.md`.
- **Known failure classes:** [`FINDINGS.md`](FINDINGS.md) and each project's local one.

## Layout

| Path | What it is |
|---|---|
| `apps/auto-studio/` | The pipeline — producer, render dispatch, console, CLI, scaffolder |
| `agents/stage_NN_*/` | Per-stage ideation agents, `00_bible` through `10_keyart` |
| `ilyrium-shots/` | The render box — shot specs, keyframes, `batch_render.py`, the ledger |
| `projects/<name>/` | One film per directory: `00_admin` … `99_archive`, `PROJECT.yaml`, style kernel |
| `manuals/` | Agent-ready tool manuals — Blender, DaVinci, ComfyUI, Unreal, ffmpeg, ElevenLabs |
| `policies/`, `evals/` | Release policy, scoring rubrics, golden sets |
| `skills/` | Packaged studio skills |
| `docs/` | Architecture, plans, research, specs, strategy |

## Two render paths

**Path A — the box.** Spec → keyframe (FLUX + character LoRA) → Wan 2.2 i2v → ledger, on
the EC2 GPU workstation. Cheapest by far, full control, LoRA identity lock. Use it for
drafts, holds and wides.

**Path B — cloud engines** via `producer.py`: Seedance 2.0/2.5, Kling, Veo 3.1, Runway.
Higher fidelity, 21:9, native audio and lip-sync, priced per second. Use it for hero
close-ups, sung beats and anything 21:9-critical.

## Song IDs

Every project claims a prefix in [`ilyrium-shots/SONG_ID_REGISTRY.json`](ilyrium-shots/SONG_ID_REGISTRY.json)
**before** scaffolding. Audit with:

```
python ilyrium-shots/song_id_registry.py check
```

IDs that already have ledger history are permanent — the provenance chain is keyed on them.

## Current productions

| Project | Status |
|---|---|
| `new_harnomy_usa` | Feature. Bible complete, both bookends carded and spec'd. See `00_admin/CCO_ASSESSMENT.md` for the capacity verdict and gate plan |
| `king_size` | Music video (song ID `NH-S05`, legacy claim) |
| `broderick`, `upham`, `bank_associate`, `stripe` | Earlier / ad work |

## Cost discipline

**Stop the GPU box when idle.** A forgotten g6.2xlarge weekend is ~$60; a forgotten month
is ~$650. The AWS G-family quota is 8 vCPU — one g6.2xlarge at a time, so Path A does not
parallelize until that is raised.
