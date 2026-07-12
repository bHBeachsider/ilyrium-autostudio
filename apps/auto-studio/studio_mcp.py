"""
Ilyrium Studio MCP server.

Exposes the studio's actions as MCP tools so an external agent (Claude in
Cowork/Code, etc.) can drive productions over the Model Context Protocol —
the agent-automation surface that sits alongside the Streamlit UI.

Run:  python studio_mcp.py
The active project is held in-process; set ILYRIUM_PROJECT_DIR to resume an
existing campaign, or call set_script to start a new one.

Requires:  pip install mcp   (and the rest of the auto-studio venv)
"""

import os
import sys

# MCP clients spawn this with an arbitrary working directory and without the
# app's env loaded. Anchor everything to the auto-studio folder so imports and
# relative outputs/ paths resolve, and load the studio .env so API keys
# (FAL_KEY, XAI_API_KEY, ELEVENLABS_API_KEY, AWS, ...) are available.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
os.chdir(_HERE)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except Exception:
    pass

from mcp.server.fastmcp import FastMCP

import studio_tools

mcp = FastMCP("ilyrium-studio")
_state = {"project_dir": os.getenv("ILYRIUM_PROJECT_DIR")}


def _run(name: str, **kwargs) -> str:
    res = studio_tools.execute_tool(name, kwargs, _state["project_dir"])
    _state["project_dir"] = res.get("project_dir", _state["project_dir"])
    return res["content"]


@mcp.tool()
def scaffold_project(name: str, type: str = "SHORT", genre_packs: list = None,
                     kernel: str = "new_harnomy") -> str:
    """Create a new film-project folder tree under projects/ using the canonical
    scaffold (core + genre packs). type = AD/SHORT/PILOT/TRAILER/SCENE/MUSIC_VIDEO/
    PITCH/EXPLAINER. genre_packs = e.g. ['opera','narrative']. Develop each stage
    afterward with stage_ideate."""
    return _run("scaffold_project", name=name, type=type,
                genre_packs=genre_packs or [], kernel=kernel)


@mcp.tool()
def get_project_state() -> str:
    """Read the current project: shots, takes, selections, cuts, audio settings."""
    return _run("get_project_state")


@mcp.tool()
def get_tool_manual(tool: str) -> str:
    """Load the agent-readable manual for a tool/engine before operating it, so your calls are
    grounded in real docs (not hallucinated) and you respect its action boundaries (credentials,
    payments, consent). tool = engine/tool name, e.g. 'runway', 'tensorart', 'comfyui', 'resolve',
    'ffmpeg', 'elevenlabs', 'ue', 'blender', 'igniter'."""
    return _run("get_tool_manual", tool=tool)


@mcp.tool()
def list_tools(filter: str = "") -> str:
    """List every studio tool available (name + one-line summary) — the studio's help menu.
    Optionally pass a keyword to filter by name/description (e.g. 'edit', 'release', 'model')."""
    return _run("list_tools", filter=filter)


@mcp.tool()
def list_models() -> str:
    """List the studio's curated, capability-tagged model/engine catalog (modality, provider,
    base, strengths, cost, recommended_for). TensorArt has no list-all API, so this registry is
    the vetted set the agent chooses from."""
    return _run("list_models")


@mcp.tool()
def recommend_models(project: str = "", need: str = "", type: str = "", top_k: int = 5) -> str:
    """Recommend the best generation models for a project, ranked, each with a rationale. Scores
    the catalog against the project's Style Kernel (look / register / genre / aspect) and the
    modality the stage needs (`need` = txt2img|img2img|keyframe|t2v|i2v|v2v|3d). Use it to choose
    which model renders a shot — e.g. recommend_models(project='new_harnomy_usa', need='i2v').
    Returns a shortlist; you make the final creative pick."""
    return _run("recommend_models", project=project or None, need=need or None,
                type=type or None, top_k=top_k)


@mcp.tool()
def set_script(scenes: list, business_name: str = "", vibe: str = "", format: str = "") -> str:
    """Create or update the campaign script. `scenes` = list of
    {scene_number, visual_prompt, voiceover}. Creates the project if none active."""
    return _run("set_script", scenes=scenes, business_name=business_name, vibe=vibe, format=format)


@mcp.tool()
def generate_first_cut(model: str = "grok-imagine") -> str:
    """Render the first take of every shot lacking one, then assemble a cut."""
    return _run("generate_first_cut", model=model)


@mcp.tool()
def regenerate_shot(scene_number: int, new_visual_prompt: str = "", new_voiceover: str = "",
                    model: str = "grok-imagine", regen_audio: bool = False) -> str:
    """Regenerate ONE shot as a new take (grok-imagine / veo3 / veo3.1 / kling / ue /
    comfyui / comfyui:<registry id> e.g. comfyui:zimage, comfyui:flux2,
    comfyui:flux2-klein-9b-uncensored — any provider='comfyui' model_registry.json entry)."""
    return _run("regenerate_shot", scene_number=scene_number,
                new_visual_prompt=new_visual_prompt or None,
                new_voiceover=new_voiceover or None, model=model, regen_audio=regen_audio)


@mcp.tool()
def edit_shot(scene_number: int, edit_prompt: str) -> str:
    """Edit a shot's current take IN PLACE with Runway Gen-4 Aleph (relight, change camera
    angle, add/remove/replace objects, restyle, VFX) rather than regenerating. Non-destructive:
    appends a new take. Needs RUNWAYML_API_SECRET. e.g. 'relight to golden hour', 'remove the logo'."""
    return _run("edit_shot", scene_number=scene_number, edit_prompt=edit_prompt)


@mcp.tool()
def edit_image(change: str, image_path: str = "", scene_number: int = None,
               model: str = "zimage", denoise: float = 0.65, seed: int = None) -> str:
    """EDIT a still image on the self-hosted ComfyUI box (img2img): restyle/recolor/
    relight an existing image toward `change` while keeping its composition. Target a
    take (scene_number) or any image_path. model = zimage | flux2 |
    flux2-klein-9b-uncensored (on-box registry models). denoise = edit strength 0-1
    (lower keeps more). Non-destructive: writes a NEW file (and appends an image take
    when a scene is targeted). Needs the box + tunnel up (cli/box.ps1 start + tunnel)."""
    return _run("edit_image", change=change, image_path=image_path or None,
                scene_number=scene_number, model=model, denoise=denoise, seed=seed)


@mcp.tool()
def inpaint_image(change: str, image_path: str = "", scene_number: int = None,
                  region: str = "", mask: str = "", model: str = "zimage",
                  seed: int = None) -> str:
    """INPAINT part of a still on the self-hosted ComfyUI box: ONLY the masked area
    changes; the rest is preserved pixel-for-pixel. Pass region='x1,y1,x2,y2'
    (fractions 0-1 or pixels) or mask=<image path, white=change>. Target a take
    (scene_number) or any image_path. model = zimage | flux2 |
    flux2-klein-9b-uncensored. Writes a NEW file. Needs the box + tunnel up."""
    return _run("inpaint_image", change=change, image_path=image_path or None,
                scene_number=scene_number, region=region or None, mask=mask or None,
                model=model, seed=seed)


@mcp.tool()
def edit_image_text(prompt: str, images: list, output_path: str,
                    resolution: str = "2K", aspect_ratio: str = "auto",
                    seed: int = None, num_images: int = 1) -> str:
    """Maskless text-driven STILL-image edit via fal nano-banana-pro/edit (Gemini 3
    Pro Image). Describe the change in plain text ('add a black horseshoe fringe',
    'swap the background to a newsroom', 'put a gold bracelet on the left wrist') and
    pass one or more reference image paths/URLs. Preserves identity + style far better
    than mask inpainting; great for character-design tweaks and trainset prep. No GPU.
    images = list of paths/URLs; output_path = where to save (index appended if
    num_images>1); resolution = 1K|2K|4K. Returns the saved path(s)."""
    from media.fal_image_edit import edit_image_fal
    saved = edit_image_fal(prompt, images, output_path, resolution=resolution,
                           aspect_ratio=aspect_ratio, seed=seed, num_images=num_images)
    return "Saved:\n" + "\n".join(saved)


@mcp.tool()
def select_take(scene_number: int, take_id: str) -> str:
    """Choose which existing take of a shot is in the cut (e.g. 'take_1')."""
    return _run("select_take", scene_number=scene_number, take_id=take_id)


@mcp.tool()
def set_audio_duck(level: float) -> str:
    """Set how loud the clip's native audio sits under the narrator (0.0-1.0)."""
    return _run("set_audio_duck", level=level)


@mcp.tool()
def reassemble_cut() -> str:
    """Stitch the selected takes into a new cut and upload to R2."""
    return _run("reassemble_cut")


@mcp.tool()
def generate_music_bed(prompt: str, instrumental: bool = True, tags: str = "") -> str:
    """Generate a Suno music bed (via APIFrame) and set it on the project; then reassemble_cut to mix it in."""
    return _run("generate_music_bed", prompt=prompt, instrumental=instrumental, tags=tags or None)


# --- Enforced rights/consent release gate (Phase A step 5) ---
@mcp.tool()
def run_release_qa() -> str:
    """Run the automated QA / governance checklist on the current project
    (no-likeness legal gate + negative-prompt scan, grounded in the style kernel)."""
    return _run("run_release_qa")


@mcp.tool()
def run_style_validation() -> str:
    """Run the Style-Bible Validator (Phase B eval harness): per-shot scoring against the
    kernel (no-likeness, negatives, casting-canon, motif, register, look). Returns scores + flags."""
    return _run("run_style_validation")


@mcp.tool()
def run_eval() -> str:
    """Run the Style-Bible eval across the current project (per-dimension scores) and
    record it as an eval Run for tracking. The self-contained quality eval harness."""
    return _run("run_eval")


@mcp.tool()
def get_release_gate() -> str:
    """Show whether the current project's master cut is cleared to publish, and the outstanding blockers."""
    return _run("get_release_gate")


@mcp.tool()
def get_approval_queue(status: str = "pending") -> str:
    """Studio-wide risk-scored approval queue (Phase B): master cuts awaiting the non-delegable
    A4 release decision, highest risk first, with the reason each is risky. status=pending|all."""
    return _run("get_approval_queue", status=status)


@mcp.tool()
def approve_release(reviewer: str = "brad", no_likeness_confirmed: bool = False,
                    source_material_state: str = "", likeness_state: str = "",
                    voice_state: str = "", music_license_state: str = "",
                    vendor_terms_state: str = "", override: bool = False,
                    override_reason: str = "") -> str:
    """Non-delegable human release approval for the current master cut. Flips
    approvedForRelease only if the gate is satisfied (or via a logged override).
    You MUST set no_likeness_confirmed=true (the legal gate) unless overriding.
    Rights states accept CLEARED / NOT_APPLICABLE / PENDING / BLOCKED."""
    return _run("approve_release", reviewer=reviewer,
                no_likeness_confirmed=no_likeness_confirmed,
                source_material_state=source_material_state or None,
                likeness_state=likeness_state or None,
                voice_state=voice_state or None,
                music_license_state=music_license_state or None,
                vendor_terms_state=vendor_terms_state or None,
                override=override, override_reason=override_reason or None)


# --- Per-stage ideation/refinement agents (scaffold film projects) ---
_STAGE_CONVOS = {}


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ilyrium-autostudio


def _resolve_scaffold_project(project: str) -> str:
    from project_paths import resolve_project
    return resolve_project(project)


@mcp.tool()
def list_stage_agents() -> str:
    """List the per-stage ideation agents available for a scaffolded film project."""
    import stage_agents
    return "\n".join(f"{f} — {persona} ({title})" for f, persona, title in stage_agents.list_stage_agents())


@mcp.tool()
def stage_ideate(project: str, stage: str, message: str) -> str:
    """Talk to the ideation/refinement agent for one scaffold stage.
    project = scaffold project name (under projects/) or an absolute path;
    stage = folder like '00_bible', '01_script', '05_shots'; message = your prompt.
    The agent holds the conversation per (project, stage), reads project context, and
    writes drafts into the stage folder when you approve."""
    import stage_agents
    pdir = _resolve_scaffold_project(project)
    if not os.path.isdir(pdir):
        return f"Project not found: {project} (looked under projects/)."
    key = f"{pdir}::{stage}"
    convo = _STAGE_CONVOS.setdefault(key, [])
    convo.append({"role": "user", "content": message})
    try:
        res = stage_agents.run_stage_agent(stage, pdir, convo)
    except Exception as e:
        return f"Stage agent error: {e}"
    _STAGE_CONVOS[key] = res["messages"]
    return res["assistant_text"]


# --- 8-stage pipeline engine (full build): spin up + drive a project end-to-end ---
def _pl_run(st):
    import studio_pipeline as sp
    import pipeline_exec
    st = sp.run(st, pipeline_exec.get_executors())
    _state["pipeline"] = st
    if st.get("campaign_id"):
        _state["project_dir"] = st.get("project_dir", _state.get("project_dir"))
        pipeline_exec.persist(st)
    return st


@mcp.tool()
def start_project(prompt: str, mode: str = "assisted") -> str:
    """Spin up a complete project from ONE director prompt and run the 8-stage pipeline.
    mode = 'auto_draft' (run to a first cut, pause only at the rights gate),
    'assisted' (confirm before costly stages + pause at the gate), or 'manual' (approve
    every stage). Afterward, fine-tune any stage and use advance_pipeline / confirm_cost /
    approve_stage. State is persisted to Neon (resumable)."""
    import studio_pipeline as sp
    return sp.summary(_pl_run(sp.new_state(prompt, mode)))


@mcp.tool()
def pipeline_status() -> str:
    """Show the current pipeline: per-stage status, current stage, and what it's waiting on."""
    import studio_pipeline as sp
    st = _state.get("pipeline")
    return sp.summary(st) if st else "No active pipeline — call start_project(prompt, mode)."


@mcp.tool()
def advance_pipeline() -> str:
    """Continue running the pipeline from where it paused (after an approval/confirm or a fine-tune)."""
    import studio_pipeline as sp
    st = _state.get("pipeline")
    return sp.summary(_pl_run(st)) if st else "No active pipeline."


@mcp.tool()
def confirm_cost() -> str:
    """Give the go-ahead for a costly stage (asset gen / assembly) awaiting confirmation, then continue."""
    import studio_pipeline as sp
    st = _state.get("pipeline")
    if not st:
        return "No active pipeline."
    return sp.summary(_pl_run(sp.confirm_cost(st)))


@mcp.tool()
def reenter_stage(stage: int) -> str:
    """Re-open a completed stage (1-8) to fine-tune it; resumes from there on the next advance."""
    import studio_pipeline as sp
    st = _state.get("pipeline")
    if not st:
        return "No active pipeline."
    _state["pipeline"] = sp.reenter(st, int(stage))
    return sp.summary(_state["pipeline"])


@mcp.tool()
def approve_stage(reviewer: str = "brad", no_likeness_confirmed: bool = False,
                  override: bool = False, override_reason: str = "") -> str:
    """Approve the current stage and advance. At the rights/release gate (stage 7) this is the
    non-delegable A4 release approval — you MUST set no_likeness_confirmed=true (or override=true
    with override_reason)."""
    import studio_pipeline as sp
    st = _state.get("pipeline")
    if not st:
        return "No active pipeline."
    if st.get("stage") == 7:  # the release gate → real rights approval
        if not no_likeness_confirmed and not override:
            return ("Refused: at the release gate you must confirm the no-likeness legal gate "
                    "(no_likeness_confirmed=true) or pass override=true with override_reason.")
        try:
            from release_gate import approve_release
            res = approve_release(st.get("campaign_id"), reviewer, no_likeness_confirmed=no_likeness_confirmed,
                                  source_material_state="NOT_APPLICABLE", likeness_state="NOT_APPLICABLE",
                                  voice_state="NOT_APPLICABLE", music_license_state="NOT_APPLICABLE",
                                  vendor_terms_state="NOT_APPLICABLE", qa_passed=True,
                                  override=override, override_reason=override_reason or None)
            if not res.get("approvedForRelease") and not override:
                return "Release gate still blocked: " + "; ".join(res.get("blockers", []))
        except Exception as e:
            return f"Release approval failed: {e}"
    return sp.summary(_pl_run(sp.approve(st, reviewer)))


@mcp.tool()
def gather_references(project: str, query: str, sources: str = "met,cleveland,aic,vam",
                      category: str = "wardrobe_refs", per: int = 8, india_only: bool = True,
                      organize: bool = True) -> str:
    """Harvest open-access reference imagery for a film project via the collection-harvester
    (registry_harvest + museums.yaml) and file it into 03_design/props/<category>/. `sources` is
    a comma list of registry keys (met,cleveland,aic,vam,smithsonian,harvard,loc,dpla,nypl,archive
    ...); set india_only=False for non-India subjects. Returns a summary + manifest path."""
    import sys, io, contextlib, argparse
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import registry_harvest as rh
    pdir = _resolve_scaffold_project(project)
    props = os.path.join(pdir, "03_design", "props")
    staging = os.path.join(props, "_harvest_tmp")
    # harvest() is print-free (safe for MCP stdio); organize_refs.run prints -> capture it.
    res = rh.harvest([s.strip() for s in sources.split(",") if s.strip()], query,
                     out=staging, per=per, no_filter=not india_only)
    dl = len([r for r in res["rows"] if r.get("file")])
    lines = [f"gathered {dl}/{len(res['rows'])} references -> {os.path.relpath(staging, pdir)}"]
    if organize and dl:
        import organize_refs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            organize_refs.run(argparse.Namespace(dir=staging,
                              into=os.path.join(props, category), dry_run=False))
        lines.append(f"organized into 03_design/props/{category}/")
    lines.append(f"manifest: {os.path.join(staging, 'manifest.csv')}")
    lines += res["log"]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
