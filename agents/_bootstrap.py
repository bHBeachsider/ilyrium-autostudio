"""Bootstrap the agents-as-data tree (ILY-203 task 6).

Materialises agents/<name>/<version>/ config dirs — prompt.md, tools.yaml,
routing.yaml, permissions.yaml — for:

  * the 11 stage ideation agents (00_bible … 10_keyart), derived from the
    canonical stage contract in scaffold.CORE_STAGES so the agent prompt stays
    in lockstep with the scaffold (single source of truth), and
  * the two ACTIVE eval-gated agents: shot_spec_generator (the bible->render
    bridge) and shot_renderer (the i2v render submitter).

After writing the config it stamps each dir's manifest.json via
harness.config_hash. Re-running is idempotent: config files are only written if
absent (so hand-edits to a prompt survive), and manifests are always recomputed.

This is the BOOTSTRAP. Once written, the config files are the editable
source-of-truth; edit them directly and re-run `--manifests-only` to restamp.

Run:  python agents/_bootstrap.py
      python agents/_bootstrap.py --manifests-only
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "apps" / "auto-studio"))

import scaffold  # noqa: E402  (apps/auto-studio on path)
from harness import config_hash as ch  # noqa: E402

AGENTS = REPO_ROOT / "agents"
VERSION = "v1"

# stage folder key -> (persona, routing task_type, tier model)
STAGE_PERSONAS = {
    "00_bible": "Story Architect",
    "01_script": "Screenwriter",
    "02_characters": "Casting & Character Director",
    "03_environments": "Art Director",
    "04_keyframes": "Storyboard Artist",
    "05_shots": "Cinematographer",
    "06_voice": "Voice Director",
    "07_music": "Music Supervisor",
    "08_edit": "Editor",
    "09_qa": "QA & Continuity Supervisor",
    "10_keyart": "Key-Art Director",
}

_STAGE_BY_KEY = {s[0]: s for s in scaffold.CORE_STAGES}


def _write_if_absent(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _stage_prompt(key: str, persona: str) -> str:
    s = _STAGE_BY_KEY[key]
    _k, _path, title, purpose, produce, template, gate = s
    return f"""# {persona} — {title}

You are the **{persona}** for an Ilyrium film production: the ideation and
refinement collaborator for the **{title}** stage. You help the human develop
and sharpen THIS stage's content. (Autonomy A1: you draft and propose; the
human accepts.)

## Stage contract
- **Purpose.** {purpose}
- **Produces.** {produce}
- **Template.** {template}
- **Gate (must pass).** {gate}

## How you work
- Ideate and refine in conversation; offer concrete options; ask only the few
  questions that change the output.
- Read the project's style_kernel.json, casting canon, and any upstream stage
  before proposing, so your ideas stay continuous with the production.
- When the human approves a draft, persist it into THIS stage's folder with
  write_stage_file.
- You NEVER delete files, NEVER approve anything for release, and NEVER
  contradict the casting canon, the legal no-likeness rule, or the kernel
  look/register.

The production values (look, register, casting canon, motifs, negatives) are
fixed by the project's Style Kernel and are injected at run time — reference
them, never restate or override them.
"""


STAGE_TOOLS = """# tools.yaml — stage ideation agent (read context, write own-stage drafts)
tools:
  - name: read_project_file
    description: Read any file in the project for context.
  - name: list_project_files
    description: List files that exist in the project.
  - name: write_stage_file
    description: Persist a draft into THIS stage's folder (on human approval only).
"""


def _stage_routing(key: str) -> str:
    return f"""# routing.yaml — {key} stage ideation agent
task_type: stage_ideate        # -> policies/routing.yaml T2_mid
model: claude-sonnet-4-6
stage_key: "{key}"
admission:
  required: false              # L0: prose ideation agent; no deterministic
  reason: >                    # shot-spec golden set yet (signal-volume gate,
    Prose ideation agent. Its outputs are stage drafts, not shot-specs, so the
    NH-S03 chain_ok golden batch and studio_rubric do not score it at L0.
    Deferred per Blueprint B §0.2 until an evaluable golden set exists.
"""


STAGE_PERMISSIONS = """# permissions.yaml — stage ideation agent scope (A1)
read:
  - project_files              # any file in the project, for context
write:
  - own_stage_folder           # drafts into this stage's canonical home only
deny:
  - delete_files
  - approve_for_release
  - modify_style_kernel
  - modify_casting_canon
credentials:
  - ANTHROPIC_API_KEY          # env-var NAME only; injected by the harness
"""


# --------------------------------------------------------------------------- #
# Active eval-gated agents
# --------------------------------------------------------------------------- #
SHOT_SPEC_GENERATOR = {
    "prompt.md": """# Shot-Spec Generator — the bible→render bridge

You convert a project's Stage-2 scene cards into Stage-2 SHOT SPECS that the
ilyrium-shots render engine consumes — each conformant to
ilyrium-shots/shot_spec.schema.json — plus a batch_render-compatible song
manifest.

## Contract
Per scene card you:
- infer camera shot_size / movement / lens from the visual_prompt,
- carry setting, action, mood, and subjects (by casting-canon key),
- build the t2i prompt = the author's visual_prompt + the project's kernel look,
- resolve keyframe.ref_lora against the LoRA library (or forward-reference the
  character key),
- assign deterministic seeds and prev_shot continuity,
- split any scene longer than the per-shot cap into ordered shots.

## Invariants
- NEVER invent identity: characters are carried by their casting-canon keys; the
  prompt is the author's visual_prompt plus the enforced kernel look — nothing
  about real people is added.
- Every emitted spec MUST validate against shot_spec.schema.json.
- The no-likeness legal rule and the kernel negatives are inviolable.
""",
    "tools.yaml": """# tools.yaml — shot-spec generator
tools:
  - name: read_scene_cards
    description: Read 02_script/scenes.json (the Stage-2 scene cards).
  - name: read_style_kernel
    description: Read the project's style_kernel.json (look / register / canon / negatives).
  - name: read_lora_library
    description: Read lora_library.json to resolve keyframe.ref_lora.
  - name: validate_shot_spec
    description: Validate an emitted spec against ilyrium-shots/shot_spec.schema.json (T0 deterministic).
  - name: write_shot_spec
    description: Persist a validated shot spec + song manifest.
""",
    "routing.yaml": """# routing.yaml — shot-spec generator (active, eval-gated)
task_type: bible_to_shotspec   # -> policies/routing.yaml T3_reasoning
model: claude-opus-4-8
admission:
  required: true               # ACTIVE: needs manifest + >=5 golden + rubric
""",
    "permissions.yaml": """# permissions.yaml — shot-spec generator scope
read:
  - project_files
  - lora_library
write:
  - shot_specs                 # ilyrium-shots/shots/ + song manifest
deny:
  - delete_files
  - approve_for_release
  - modify_style_kernel
credentials:
  - ANTHROPIC_API_KEY
""",
}

SHOT_RENDERER = {
    "prompt.md": """# Shot Renderer — i2v render submission

You take one validated shot-spec and submit it to the ComfyUI Wan 2.2 14B I2V
graph through the execution harness, then record the render's provenance.

## Contract
- Submit only through harness.run (comfy_* transports). Never touch the ComfyUI
  API directly — that path is the seeded HTTP-400 / LoadImage failure class.
- Every render attempt writes a full provenance record carrying the
  agent_version_id, so chain verification covers agent identity.
- Dedupe by content_hash: an identical {shot_spec, generation, models, engine}
  that already rendered or was approved is skipped, not re-rendered.

## Invariants
- The keyframe must exist in ComfyUI/input before LoadImage references it
  (upload first).
- A failed render is recorded as status=failed with the error, never silently
  dropped — recurring failures become Findings.
""",
    "tools.yaml": """# tools.yaml — shot renderer (harness transports only)
tools:
  - name: comfy_upload_image
    description: Upload a keyframe into ComfyUI/input (harness.run.comfy_upload_image).
  - name: comfy_submit_prompt
    description: POST a workflow graph to ComfyUI /prompt (harness.run.comfy_submit_prompt).
  - name: comfy_history
    description: Poll ComfyUI /history for outputs (harness.run.comfy_history).
  - name: write_provenance
    description: Append the render's provenance record to the song ledger.
""",
    "routing.yaml": """# routing.yaml — shot renderer (active, eval-gated)
task_type: video_render        # -> policies/routing.yaml T4_specialist
engine: comfyui
model: comfyui/wan2.2-i2v-14b
admission:
  required: true               # ACTIVE: needs manifest + >=5 golden + rubric
""",
    "permissions.yaml": """# permissions.yaml — shot renderer scope
read:
  - shot_specs
  - models_lock
write:
  - provenance_ledger
  - render_outputs
deny:
  - delete_files
  - approve_for_release
credentials:
  - COMFY_URL                  # env-var NAME only; injected by the harness
""",
}


def bootstrap(manifests_only: bool = False) -> list[str]:
    written = []
    # 11 stage ideation agents
    for key, persona in STAGE_PERSONAS.items():
        if key not in _STAGE_BY_KEY:
            continue
        d = AGENTS / f"stage_{key}" / VERSION
        if not manifests_only:
            _write_if_absent(d / "prompt.md", _stage_prompt(key, persona))
            _write_if_absent(d / "tools.yaml", STAGE_TOOLS)
            _write_if_absent(d / "routing.yaml", _stage_routing(key))
            _write_if_absent(d / "permissions.yaml", STAGE_PERMISSIONS)
        ch.write_manifest(d)
        written.append(str(d.relative_to(REPO_ROOT)).replace("\\", "/"))

    # active agents
    for name, files in (("shot_spec_generator", SHOT_SPEC_GENERATOR),
                        ("shot_renderer", SHOT_RENDERER)):
        d = AGENTS / name / VERSION
        if not manifests_only:
            for fn, content in files.items():
                _write_if_absent(d / fn, content)
        ch.write_manifest(d, golden_set=f"evals/golden/{name}")
        written.append(str(d.relative_to(REPO_ROOT)).replace("\\", "/"))

    return written


if __name__ == "__main__":
    mo = "--manifests-only" in sys.argv[1:]
    out = bootstrap(manifests_only=mo)
    print(f"bootstrapped {len(out)} agent version(s):")
    for w in out:
        print(f"  {w}")
