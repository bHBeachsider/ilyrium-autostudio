"""
Project scaffolder — "new film project" (canonical scaffold v2).

Generates the canonical Ilyrium production tree: ONE universal core common to
every project, plus stackable GENRE PACKS layered on top (opera adds libretto +
score; documentary adds source clearances; etc.). See
docs/PROJECT_SCAFFOLD_PROPOSAL.md for the full rationale.

The directory tree IS the three-layer checklist roadmap. The root carries the
enforced production values (style_kernel.json), the QA/legal gate (QA_CHECKLIST.md),
the negative-prompt library, and a PROJECT.yaml manifest (the asset-graph key +
genre packs + kernel). Each stage folder's README states what to produce, the
template, and the gate it must pass.

Governance is structural: 00_admin/ (rights releases, contracts, licenses, policy
pack) and 08_qa/ map 1:1 to the canonical asset graph's RightsRecord + the
enforced release gate; 09_delivery/c2pa_manifests/ maps to
ProvenanceRecord.c2paManifestUri.

Stage agents (stage_agents.py / the MCP `stage_ideate`) keep their STABLE keys
('00_bible' … '10_keyart'); each key resolves to its canonical home via
STAGE_PATHS, so nothing calling the MCP breaks.

Usage:
    python scaffold.py "New Harnomy, USA" --genre opera narrative
    python scaffold.py "Project X" --kernel default --type AD --genre ad
    python scaffold.py "Project X" --base /some/dir
"""

import os
import re
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))                 # apps/auto-studio
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))               # ilyrium-autostudio
_KERNELS_DIR = os.path.join(_HERE, "kernels")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "project"


def _load_kernel(kernel) -> dict:
    if isinstance(kernel, dict):
        return kernel
    path = os.path.join(_KERNELS_DIR, f"{kernel}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"name": kernel or "default", "look": "", "register": "", "negatives": "",
            "palette_motifs": {}, "casting_canon": {},
            "legal_rule": "Specify every person by age / origin / build / wardrobe / affect ONLY; "
                          "never by likeness to a real public figure.",
            "engine_tails": {}, "continuity": {}}


# --------------------------------------------------------------------------- #
# Canonical CORE — every project gets exactly this.
# --------------------------------------------------------------------------- #
# All directories in the core tree (governance + phase spine + library/archive).
CORE_DIRS = [
    "00_admin", "00_admin/rights_releases", "00_admin/contracts", "00_admin/licenses", "00_admin/policy_pack",
    "01_development", "01_development/bible", "01_development/bible/world",
    "01_development/bible/characters", "01_development/research",
    "02_script", "02_script/drafts",
    "03_design", "03_design/characters", "03_design/characters/anchors",
    "03_design/characters/loras",
    "03_design/environments", "03_design/props", "03_design/keyart_refs",
    "04_preproduction", "04_preproduction/keyframes", "04_preproduction/storyboards",
    "04_preproduction/concept_art", "04_preproduction/animatics", "04_preproduction/references",
    "05_production", "05_production/prompts", "05_production/shots", "05_production/scripts",
    "06_audio", "06_audio/voice", "06_audio/dialogue", "06_audio/music", "06_audio/sfx",
    "07_post", "07_post/edit", "07_post/color", "07_post/davinci_projects",
    "08_qa",
    "09_delivery", "09_delivery/masters", "09_delivery/platform_cuts",
    "09_delivery/captions", "09_delivery/c2pa_manifests",
    "10_marketing", "10_marketing/keyart", "10_marketing/trailers",
    "99_archive",
    # RSI L0 (ILY-203): every project is trace/eval-ready from creation.
    "traces",                       # projects/<id>/traces/traces.jsonl (harness)
    "evals", "evals/golden", "evals/rubrics",   # per-project golden cases + rubric refs
]

# Stage agents: (KEY, canonical_path, title, purpose, produce, template, gate).
# KEY is the stable MCP/stage-agent identity; canonical_path is where it lives.
CORE_STAGES = [
    ("00_bible", "01_development/bible", "Stage 1 — Story / World / Character Bible",
     "The canonical record every later stage reads. Define structure, not prose.",
     "logline_treatment.md, world/ overview, characters/<NN_name>/bible.md",
     "Character entry: NAME | ROLE | AGE | ORIGIN | BUILD | WARDROBE SIGNATURE | "
     "AFFECT/PERFORMANCE REGISTER | ARC | VOICE NOTE.\nWorld entry: PLACE | FUNCTION | "
     "VISUAL SIGNATURE | RECURRING MOTIFS.",
     "Every character's ORIGIN/AGE/BUILD matches casting_canon in style_kernel.json. "
     "People described by attribute, never by likeness to a real person."),
    ("01_script", "02_script", "Stage 2 — Screenwriting / Scene cards",
     "Break the story into ordered scene cards — the unit the render pipeline consumes.",
     "scenes.json (array of scene cards)",
     'Scene card: {scene_number, location, characters[], action, visual_prompt, '
     'dialogue:[{speaker,line,delivery}], voiceover, performance, duration_target_s}.',
     "voiceover/dialogue lines contain ONLY spoken words (no stage directions). "
     "Every recurring character's physical description is restated in each scene that needs it."),
    ("02_characters", "03_design/characters", "Stage 3 — Character design + anchors + LoRAs",
     "Lock each character's face/wardrobe. Anchor stills feed --cref; trained character LoRAs feed "
     "the keyframe path's ref_lora (see loras/README.md + lora_library.json).",
     "Per character: a portrait prompt + a locked hero-portrait still in anchors/, and (optional) a "
     "trained LoRA in loras/<character>/lora/ registered in loras/lora_library.json.",
     "Character Portrait Template (docs/PROMPT_PIPELINE_TEMPLATES.md Stage 3): "
     "SUBJECT_BY_ATTRIBUTE + WARDROBE + SETTING + LIGHTING + GAZE + PERFORMANCE + kernel look. "
     "Anchor order: render the hero portraits first, then --cref everywhere.",
     "No resemblance to real public figures. Anchor matches the character bible. Motifs correct."),
    ("03_environments", "03_design/environments", "Stage 4 — Environment & prop plates",
     "The world as its own asset class — establishing shots and hero props, no principals in frame.",
     "Environment plate prompts + prop macros (in ../props/).",
     "Environment Plate Template: WIDE/ESTABLISHING of LOCATION + TIME + SET DRESSING(motifs) "
     "+ LIGHTING + kernel look. Prop macro: HERO PROP + MATERIAL/WEAR + MOTIF SPEC.",
     "Recurring motifs correct (e.g. the mauve spec in style_kernel.json). Kernel look held."),
    ("04_keyframes", "04_preproduction/keyframes", "Stage 5 — Keyframes (the bridge to motion)",
     "One locked still per scene that becomes the first frame of the video shot.",
     "A keyframe still per scene card, --cref'd to the character anchor.",
     "Use the scene card's action + character anchor (--cref) + environment. "
     "In the console/agent, model 'keyframe' generates this and animates it.",
     "Continuity with the character anchor and the prior shot. Kernel look held."),
    ("05_shots", "05_production/shots", "Stage 6 — Shots (render to video)",
     "Animate keyframes / render each scene to a clip. Renders land in the auto-studio project.",
     "One rendered take per shot (engine per shot: grok/veo3/kling/comfyui/ue/keyframe).",
     "Video Master Prompt: SHOT_SIZE + SUBJECT + ACTION + CAMERA + LENS + LIGHTING + DURATION "
     "+ on-camera dialogue(veo3/kling) + ambience + performance + kernel look. Continuity: "
     "first_frame=locked keyframe; restate character description each shot.",
     "Performance register held (no smile-at-camera, no winking). Dialogue native where on-camera."),
    ("06_voice", "06_audio/voice", "Stage 7 — Voice / Dialogue / VO",
     "Lock one voice per character (the audio equivalent of --cref).",
     "voice_casting.md (per-character ElevenLabs voice_id + settings) + line specs.",
     "Voice-casting sheet: NAME: provider, voice_id, stability, similarity, style, accent/age, "
     "baseline delivery. Line: SPEAKER | line | delivery — spoken words only.",
     "One locked voice per character. Delivery matches the character's register."),
    ("07_music", "06_audio/music", "Stage 8 — Music / Sound",
     "Score brief + beds. Generate (Suno/APIFrame) or use a licensed track.",
     "score_brief.md + any music beds (mp3); SFX in ../sfx/.",
     "Score brief: MOOD GENRE INSTRUMENTATION, TEMPO, STRUCTURE, instrumental?, emotional arc, "
     "must not overpower VO (ducked bed). Per-scene SFX/ambience spec.",
     "Music sits under the VO (ducked). For commercial release prefer licensed tracks "
     "(record the license in ../../00_admin/licenses/)."),
    ("08_edit", "07_post/edit", "Stage 9 — Editorial / Assembly",
     "Select takes and order the cut. Encoded as the editor's selection rubric.",
     "edit_notes.md (selection rubric + cut order + runtime target) + OTIO/EDL exports.",
     "Rubric: pick the take that best holds the performance register; cut on stillness for this "
     "show; VO leads, dialogue and ambience under it; target RUNTIME.",
     "Cut honors the rubric and the target runtime."),
    ("09_qa", "08_qa", "Stage 10 — Continuity / QA / Governance",
     "The enforceable gate. Run the checklist on every render before approval.",
     "qa_log.md (per-shot checklist results).",
     "See ../QA_CHECKLIST.md. Fail -> regenerate with the matching fix from the kernel's "
     "failure_fixes (e.g. mauve-reads-lavender, acting-at-camera).",
     "LEGAL GATE: reject any render resembling a real public figure. Casting canon + motifs + "
     "performance register + negatives all pass before approvedForRelease (enforced by the "
     "release gate; releases live in ../00_admin/rights_releases/)."),
    ("10_keyart", "10_marketing/keyart", "Stage 11 — Marketing / Key art",
     "Poster, program, social — portrait-orientation variants of the hero portraits + hero prop.",
     "Key-art prompts (--ar 4:5 / 1:1) reusing character anchors + the hero-prop macro.",
     "Key-Art Template: hero portrait / hero prop, portrait orientation, same kernel look.",
     "Same kernel look as the production. No on-image text unless intentional."),
]

# Back-compat exports for stage_agents.py: STAGES keyed by stable KEY; STAGE_PATHS
# maps each KEY to its canonical home folder.
STAGES = [(k, title, purpose, produce, template, gate)
          for (k, _path, title, purpose, produce, template, gate) in CORE_STAGES]
STAGE_PATHS = {k: path for (k, path, *_rest) in CORE_STAGES}


# --------------------------------------------------------------------------- #
# GENRE PACKS — stacked onto core (never replace it). Each is a delta.
# --------------------------------------------------------------------------- #
# pack -> {"dirs":[...], "files":{relpath: content}, "note": "..."}
GENRE_PACKS = {
    "opera": {
        "note": "Opera/musical: sung text + composed score + répétiteur/vocal coaching.",
        "dirs": ["02_script/libretto", "06_audio/score", "06_audio/score/vocal_scores"],
        "files": {
            "02_script/libretto/libretto.md":
                "# Libretto\n\nThe sung text (acts/scenes/numbers). Spoken/sung words only — "
                "stage directions in [brackets]. Each number ties to a scene_number in "
                "../scenes.json.\n",
            "02_script/libretto/surtitles.md": "# Surtitles\n\nProjected translation/clarification lines, timed to numbers.\n",
            "06_audio/score/song_list.md": "# Song list\n\n| # | Title | Singers | Key/Tempo | Scene |\n|---|-------|---------|-----------|-------|\n",
            "06_audio/score/repetiteur_notes.md":
                "# Répétiteur notes\n\nPiano reduction + rehearsal notes; pitch/rhythm/diction "
                "corrections per singer (the opera-specific music-staff role).\n",
            "06_audio/voice/vocal_coaching.md": "# Vocal coaching\n\nPer-character fach/range, diction, tempo maps.\n",
        },
    },
    "narrative": {
        "note": "Drama/pilot/short/film: pilot treatment, shooting script, sequence/season map.",
        "dirs": ["01_development/bible/pilot", "02_script/shooting_script"],
        "files": {
            "01_development/bible/sequences.md":
                "# Sequences / season map\n\nMulti-scene arcs -> Sequence rows in the asset graph. "
                "| # | Sequence | Scenes | Function |\n|---|----------|--------|----------|\n",
            "01_development/bible/pilot/treatment.md": "# Pilot / episode treatment\n",
        },
    },
    "comedy": {
        "note": "Comedy lives on coverage + timing; many alternate line readings.",
        "dirs": ["05_production/shots/alt_takes"],
        "files": {
            "02_script/punch_up.md": "# Punch-up\n\nAlternate jokes / line variants per scene.\n",
            "07_post/edit/timing_notes.md": "# Comic timing notes\n\nBeats, holds, and cut points for the laugh.\n",
        },
    },
    "documentary": {
        "note": "Governance-heaviest: archival + interviewee clearances; fact-checking.",
        "dirs": ["00_admin/source_clearances", "01_development/research/interviews",
                 "01_development/research/archival", "01_development/research/transcripts"],
        "files": {"08_qa/fact_check.md": "# Fact-check log\n\nClaim | Source | Status | Reviewer.\n"},
    },
    "music_video": {
        "note": "The master track is fixed input; the edit locks to its timecode.",
        "dirs": ["06_audio/track", "04_preproduction/choreography"],
        "files": {"06_audio/track/timecode_map.md": "# Timecode map\n\nSection | TC in | TC out | Shot.\n"},
    },
    "ad": {
        "note": "Short-form (Ad Studio): collapsed development, scene == shot, Project.type=AD.",
        "dirs": ["03_design/product_shots"],
        "files": {"00_admin/brand_brief.md": "# Brand brief\n\nBrand, product, audience, vibe, CTA, platform/format.\n"},
    },
    "trailer": {
        "note": "Promo/trailer: beats sheet + music clearance (the usual blocker).",
        "dirs": ["00_admin/licenses/music"],
        "files": {"02_script/beats_sheet.md": "# Trailer beats\n\nHook | Build | Turn | Button. Music cue per beat.\n"},
    },
}
# Aliases so common synonyms resolve to the same pack.
PACK_ALIASES = {"musical": "opera", "short_form": "ad", "short-form": "ad",
                "promo": "trailer", "doc": "documentary", "film": "narrative",
                "drama": "narrative", "pilot": "narrative", "short": "narrative"}


def resolve_packs(packs):
    seen, out = set(), []
    for p in packs or []:
        key = PACK_ALIASES.get(p.strip().lower(), p.strip().lower())
        if key in GENRE_PACKS and key not in seen:
            seen.add(key); out.append(key)
    return out


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def _readme(stage) -> str:
    key, path, title, purpose, produce, template, gate = stage
    return f"""# {title}

**Canonical home:** `{path}/`  ·  **Stage key:** `{key}`

**Purpose.** {purpose}

**Produce (put your files in this folder):**
{produce}

**Template / how to make it:**
{template}

**Gate (must pass before this stage is done):**
{gate}

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="{key}", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
"""


def _project_yaml(name: str, slug: str, ptype: str, kdict: dict, packs: list) -> str:
    kname = kdict.get("name") or "default"
    packs_line = "[" + ", ".join(packs) + "]" if packs else "[]"
    import datetime
    today = datetime.date.today().isoformat()
    return f"""# Ilyrium project manifest — the one file the scaffolder, graph_sync, the
# console, and the release gate all read. externalId is the canonical asset-graph key.
title: "{name}"
slug: {slug}
externalId: {slug}
type: {ptype}
genre_packs: {packs_line}
kernel: {kname}
status: DRAFT
created: {today}
rights:
  likeness_flags: []   # e.g. {{character: pengold, note: "...", release: 00_admin/rights_releases/<file>}}
"""


def scaffold_project(name: str, base_dir: str = None, kernel="new_harnomy",
                     genre_packs=None, ptype: str = "SHORT") -> str:
    slug = slugify(name)
    base_dir = base_dir or os.path.join(_REPO_ROOT, "projects")
    root = os.path.join(base_dir, slug)
    os.makedirs(root, exist_ok=True)

    kdict = _load_kernel(kernel)
    packs = resolve_packs(genre_packs)

    # Root: enforced production values + manifest.
    with open(os.path.join(root, "style_kernel.json"), "w", encoding="utf-8") as f:
        json.dump(kdict, f, indent=2)
    with open(os.path.join(root, "NEGATIVE_PROMPTS.txt"), "w", encoding="utf-8") as f:
        f.write(kdict.get("negatives", "") + "\n")
    with open(os.path.join(root, "QA_CHECKLIST.md"), "w", encoding="utf-8") as f:
        f.write(_QA_CHECKLIST)
    with open(os.path.join(root, "PROJECT.yaml"), "w", encoding="utf-8") as f:
        f.write(_project_yaml(name, slug, ptype, kdict, packs))
    # RSI L0 (ILY-203): per-project findings registry, so every project is
    # loop-compliant from creation (the repo-root FINDINGS.md holds shared
    # classes; this one holds project-local ones).
    with open(os.path.join(root, "FINDINGS.md"), "w", encoding="utf-8") as f:
        f.write(_FINDINGS_STUB.format(name=name))

    # Core directory tree.
    for d in CORE_DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    # Keep the empty trace/eval dirs in git so the harness can write into them
    # on first run without a missing-dir error.
    for keep in ("traces", "evals/golden", "evals/rubrics"):
        open(os.path.join(root, keep, ".gitkeep"), "w").close()

    # Stage READMEs at their canonical homes.
    for stage in CORE_STAGES:
        d = os.path.join(root, stage[1])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
            f.write(_readme(stage))

    # Casting canon + anchors (design stage).
    canon = kdict.get("casting_canon", {})
    with open(os.path.join(root, "03_design", "characters", "CASTING_CANON.md"), "w", encoding="utf-8") as f:
        f.write("# Casting canon (from style_kernel.json — do not contradict)\n\n")
        for who, desc in canon.items():
            f.write(f"- **{who}**: {desc}\n")
        f.write("\nDrop each character's locked hero portrait in `anchors/<character>.png` — "
                "the keyframe path will --cref against it for cross-shot face consistency.\n")
    # A bible folder per canonical character + its LoRA authoring folder.
    for who in canon:
        cdir = os.path.join(root, "01_development", "bible", "characters", who)
        os.makedirs(os.path.join(cdir, "visual_refs"), exist_ok=True)
        os.makedirs(os.path.join(cdir, "voice_refs"), exist_ok=True)
        bpath = os.path.join(cdir, "bible.md")
        if not os.path.exists(bpath):
            with open(bpath, "w", encoding="utf-8") as f:
                f.write(f"# {who}\n\n{canon[who]}\n\n"
                        "NAME | ROLE | AGE | ORIGIN | BUILD | WARDROBE | REGISTER | ARC | VOICE NOTE\n")
        # Per-character LoRA authoring tree (source refs -> stylized refs -> trained weights).
        ldir = os.path.join(root, "03_design", "characters", "loras", who)
        for sub in ("source", "refs", "lora"):
            os.makedirs(os.path.join(ldir, sub), exist_ok=True)

    # Character LoRA registry + how-to (the bridge into the ilyrium-shots render engine).
    lora_dir = os.path.join(root, "03_design", "characters", "loras")
    with open(os.path.join(lora_dir, "lora_library.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "loras": []}, f, indent=2)
    with open(os.path.join(lora_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(_lora_readme())

    # Starter scene-cards file.
    with open(os.path.join(root, "02_script", "scenes.json"), "w", encoding="utf-8") as f:
        json.dump([{
            "scene_number": 1, "location": "", "characters": [], "action": "",
            "visual_prompt": "", "dialogue": [{"speaker": "", "line": "", "delivery": ""}],
            "voiceover": "", "performance": "", "duration_target_s": 8,
        }], f, indent=2)

    # Policy-pack pointer.
    with open(os.path.join(root, "00_admin", "policy_pack", "README.md"), "w", encoding="utf-8") as f:
        f.write("# Policy pack (this project's instance)\n\nSource-material, likeness/voice consent, "
                "human-authorship, disclosure, music-licensing, vendor intake, retention, red-team. "
                "See docs/STUDIO_FACTORY_ROADMAP.md §6. Releases live in ../rights_releases/.\n")

    # Genre packs (layered after core).
    for pack in packs:
        spec = GENRE_PACKS[pack]
        for d in spec.get("dirs", []):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        for rel, content in spec.get("files", {}).items():
            full = os.path.join(root, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            if not os.path.exists(full):
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)

    # Top-level roadmap README.
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(_root_readme(name, slug, kdict, packs, ptype))

    # Best-effort: register the project node in the canonical asset graph.
    try:
        from graph_sync import sync_scaffold_project
        sync_scaffold_project(slug, name, kdict, root, ptype=ptype)
    except Exception:
        pass

    # Dimensional stage taxonomy: bible 6 dimensions + per-stage element stubs (stage_scaffold).
    try:
        import stage_scaffold
        stage_scaffold.scaffold(slug, root=root)
    except Exception as _e:
        print(f"[scaffold] stage taxonomy skipped: {_e}")
    # Seed this project's copy of the master development prompt.
    _mp = os.path.join(_REPO_ROOT, "docs", "MASTER_DEVELOPMENT_PROMPT.md")
    if os.path.exists(_mp):
        import shutil
        shutil.copy(_mp, os.path.join(root, "01_development", "DEVELOPMENT_PROMPT.md"))

    return root


def _lora_readme() -> str:
    return """# Character LoRAs — authoring home

A character LoRA encodes a character's look (from the bible) as a `.safetensors` the render engine
loads. It is authored here and *registered* in `lora_library.json`, which the ilyrium-shots
keyframe path (`keyframe_to_comfy.py`) reads via each shot spec's `keyframe.ref_lora`.

Per character (folder name = the casting-canon key):
- `<character>/source/` — raw reference images (public-domain portraits, engravings, photos).
- `<character>/refs/`   — style-transferred training set (ComfyUI img2img, denoise 0.60–0.70),
                          15–30 images at 640×640, identity retained + target style applied.
- `<character>/lora/`   — the trained `<name>.safetensors` + `<name>.meta.json` sidecar
                          (trigger_word, tensorart_job_id, base_model, sha256, trained_at).

`lora_library.json` (this folder) is the registry the render engine consumes:
  { "loras": [ { "name", "filename", "trigger_word", "strength" (0.65–0.80), "base_model",
                 "sha256", "tensorart_job_id", "trained_at", "notes" } ] }

Train with the LoRA workflow (Tensor.art training): see `docs/ILYRIUM-LORA-WORKFLOW.md`. After
training, sync the weights to the EC2 ComfyUI `models/loras/` and pin them in
`ilyrium-shots/models.lock.json` (role `lora_character`). The project scaffold is the AUTHORING
home; `models.lock.json` is the RENDER pin — no duplication.
"""


_FINDINGS_STUB = """# FINDINGS — {name} (project-local)

Append-only registry of failure classes specific to THIS project — the Finding
primitive of the RSI loop (see the repo-root `FINDINGS.md` and `README_RSI.md`
for the shared classes and the full contract). Every recurring finding
(frequency >= 3) must terminate in a durable artifact (test / gate / validator /
prompt patch / policy) or an explicit accepted-risk record.

Fields: finding_id, severity, frequency, root_cause, detected_at_layer,
should_have_been_prevented_at_layer, remediation_type, status.

_(no project-local findings yet)_
"""


_QA_CHECKLIST = """# QA / Continuity / Governance checklist

Run on EVERY render before it is approved for release.

- [ ] Casting canon honored (origin / age / build per the character bible)?
- [ ] NO resemblance to a real public figure?  ← LEGAL GATE: reject if yes.
- [ ] Recurring motif correct? (e.g. mauve = brownish 1970s paperback, NOT lavender)
- [ ] Performance register held? (no smile-at-camera, no telegraphed emotion, no winking)
- [ ] Negative-prompt violations absent? (text / chyron / logo / modern devices / over-saturation)
- [ ] Continuity with the locked character anchor / prior shot?
- [ ] Rights/consent releases on file for any recurring face/voice? (00_admin/rights_releases/)

Fail -> regenerate using the matching fix in `style_kernel.json` -> `failure_fixes`.
This checklist is the human rubric behind the enforced release gate (approvedForRelease).
"""


def _root_readme(name: str, slug: str, kdict: dict, packs: list, ptype: str) -> str:
    look = (kdict.get("look") or "(none set)")[:200]
    stage_lines = "\n".join(f"- `{path}/` — {title.split('— ', 1)[-1]}  *(stage `{key}`)*"
                            for (key, path, title, *_r) in CORE_STAGES)
    packs_note = (", ".join(packs) if packs else "none (core only)")
    return f"""# {name}

Master production folder, scaffolded by the Ilyrium studio (canonical scaffold v2).
**Type:** {ptype}  ·  **Genre packs:** {packs_note}

The tree is a **governed, phase-based roadmap** — walk it top to bottom. Each stage folder's
`README.md` states what to produce, the template, and the gate it must pass.

**Production values are fixed and enforced** by:
- `PROJECT.yaml` — manifest: asset-graph key (externalId), type, genre packs, kernel, status.
- `style_kernel.json` — the look/register/casting/motifs/negatives for THIS production.
- `QA_CHECKLIST.md` — the continuity + legal gate every render must pass (the release gate's rubric).
- `NEGATIVE_PROMPTS.txt` — the negative-prompt library.

**Governance is structural:** `00_admin/` (rights releases, contracts, licenses, policy pack) and
`08_qa/` map to the asset graph's RightsRecord + the enforced release gate;
`09_delivery/c2pa_manifests/` maps to ProvenanceRecord.c2paManifestUri.

**Look (from the kernel):** {look}…

**Pipeline stages (canonical homes):**
{stage_lines}

**Wiring into the auto-studio:** set the campaign/project's `style_kernel` to this `style_kernel.json`
(or the kernel name). Generate character anchors in `03_design/characters/anchors/`, then use model
`keyframe` so shots --cref against them.

**Prompting:** each stage's required information categories come from the shared taxonomy
(`apps/auto-studio/prompt_taxonomy.json`). Get a stage's fill-in checklist with
`python prompt_kit.py checklist <stage>` (browsable copies in `apps/auto-studio/prompt_templates/`),
auto-fill the kernel layer with `compose`, and lint a finished prompt for missing categories with
`lint`. See `docs/PROMPT_SYSTEM.md`. References: `docs/PROMPT_PIPELINE_TEMPLATES.md`,
`docs/PROJECT_SCAFFOLD_PROPOSAL.md`.
"""


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print('Usage: python scaffold.py "Project Name" [--kernel name] [--type AD|SHORT|PILOT|...] '
              '[--genre opera narrative ...] [--base dir] [--client name]')
        sys.exit(1)
    name = args[0]
    kernel = "new_harnomy"
    base = None
    ptype = "SHORT"
    genres = []
    if "--kernel" in args:
        kernel = args[args.index("--kernel") + 1]
    if "--base" in args:
        base = args[args.index("--base") + 1]
    if "--client" in args:
        # projects/<client>/<slug> — multi-client nested layout
        base = os.path.join(_REPO_ROOT, "projects", args[args.index("--client") + 1])
    if "--type" in args:
        ptype = args[args.index("--type") + 1]
    if "--genre" in args:
        i = args.index("--genre") + 1
        while i < len(args) and not args[i].startswith("--"):
            genres.appe