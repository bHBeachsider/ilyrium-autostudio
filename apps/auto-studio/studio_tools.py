"""
Studio tools for the conversational Ad Studio agent.

Defines the Anthropic tool schemas the director agent can call, and a
dispatcher that executes each one against the non-destructive project store
(project_store.py) + orchestrator (producer.py). The agent is stateless: the
caller owns the active `project_dir`; tools that create a project return the
new dir so the UI can persist it.

execute_tool(name, tool_input, project_dir, progress_cb) -> {
    "content": <short text result for the model>,
    "project_dir": <current/new project dir or None>,
}
"""

import os
import json

import project_store as ps

# --------------------------------------------------------------------------- #
# Tool schemas (Anthropic Messages API "tools" format)
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "name": "scaffold_project",
        "description": "Create a new film-project folder tree under projects/ using the canonical "
                       "scaffold (core + genre packs). Use to start a new production. Lays down the "
                       "governed stage folders, PROJECT.yaml, style_kernel.json, QA checklist, and "
                       "the rights/admin + delivery structure. Develop each stage afterward with the "
                       "stage agents (stage_ideate).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project title, e.g. 'New Harnomy, USA'."},
                "type": {"type": "string", "enum": ["AD", "SHORT", "PILOT", "TRAILER", "SCENE",
                                                    "MUSIC_VIDEO", "PITCH", "EXPLAINER"],
                         "description": "Project type (maps to the asset-graph ProjectType). Default SHORT."},
                "genre_packs": {"type": "array", "items": {"type": "string"},
                                "description": "Add-on packs stacked onto core: opera/musical, narrative "
                                               "(drama/pilot/short/film), comedy, documentary, music_video, "
                                               "ad/short_form, trailer/promo."},
                "kernel": {"type": "string", "description": "Style-kernel name under kernels/ (default 'new_harnomy') or 'default'."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_project_state",
        "description": "Read the current project: business, vibe, format, audio duck, "
                       "every shot with its takes and which take is selected, and any "
                       "rendered cuts. Call this before deciding what to change.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_script",
        "description": "Create or update the campaign script. Provide the full ordered "
                       "list of scenes. Existing shots with the same scene_number keep "
                       "their takes; their prompt/voiceover are updated. New scene_numbers "
                       "are added. Call this once the brief is clear and the user approves "
                       "the script.",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_name": {"type": "string"},
                "vibe": {"type": "string", "description": "e.g. 'High-Energy & Loud', 'Chill & Relaxed'"},
                "format": {"type": "string", "description": "'9:16 (Instagram Reels/TikTok)' or '16:9 (YouTube)'"},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer"},
                            "visual_prompt": {"type": "string"},
                            "voiceover": {"type": "string"},
                            "source_image": {"type": "string",
                                "description": "Optional path to a reference image (e.g. one the user "
                                               "attached, saved under outputs/_director_refs/) to use as "
                                               "this shot's locked first frame — the strongest continuity "
                                               "lock. The shot is then rendered by animating that image."},
                        },
                        "required": ["scene_number", "visual_prompt", "voiceover"],
                    },
                },
            },
            "required": ["scenes"],
        },
    },
    {
        "name": "generate_first_cut",
        "description": "Render the first take of every shot that doesn't already have a "
                       "usable take, then assemble a cut. Use after set_script for the "
                       "initial production. Slow (calls paid video/audio APIs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "enum": ["grok-imagine", "veo3", "veo3.1", "kling", "comfyui",
                                                     "comfyui:zimage", "comfyui:flux2",
                                                     "comfyui:flux2-klein-9b-uncensored",
                                                     "ue", "keyframe", "runway", "runway:veo3.1"],
                          "description": "Video model for all shots in this pass. Default 'grok-imagine' "
                                         "(fast/cheap). Use veo3/veo3.1/kling for premium quality or dialogue. "
                                         "'comfyui:<id>' runs any registry model on the self-hosted box (stills)."},
            },
        },
    },
    {
        "name": "regenerate_shot",
        "description": "Regenerate ONE shot as a new take (never overwrites siblings). "
                       "Optionally rewrite that shot's visual prompt and/or voiceover first "
                       "to match the user's note, and optionally pick a model. The new take "
                       "becomes selected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_number": {"type": "integer"},
                "new_visual_prompt": {"type": "string", "description": "Optional rewritten visual prompt."},
                "new_voiceover": {"type": "string", "description": "Optional rewritten voiceover line."},
                "regen_audio": {"type": "boolean", "description": "Re-render the voiceover too (set true if you changed the voiceover)."},
                "model": {"type": "string", "enum": ["grok-imagine", "veo3", "veo3.1", "kling", "comfyui",
                                                     "comfyui:zimage", "comfyui:flux2",
                                                     "comfyui:flux2-klein-9b-uncensored",
                                                     "ue", "keyframe", "runway", "runway:veo3.1"],
                          "description": "Video model. 'grok-imagine' = fast/cheap draft (default). "
                                         "'veo3'/'veo3.1' = premium with native dialogue. 'kling' = "
                                         "premium with lip-synced dialogue. Use a premium model when "
                                         "the user wants higher quality or on-camera character dialogue. "
                                         "'comfyui:<id>' = any self-hosted registry model (stills)."},
            },
            "required": ["scene_number"],
        },
    },
    {
        "name": "select_take",
        "description": "Choose which existing take of a shot is in the cut (e.g. revert to "
                       "an earlier take the user preferred).",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_number": {"type": "integer"},
                "take_id": {"type": "string", "description": "e.g. 'take_1'"},
            },
            "required": ["scene_number", "take_id"],
        },
    },
    {
        "name": "set_audio_duck",
        "description": "Set how loud the clip's native audio (ambient/music/SFX) sits under "
                       "the narrator, 0.0 (silent) to 1.0 (full). Re-assemble the cut to hear it.",
        "input_schema": {
            "type": "object",
            "properties": {"level": {"type": "number"}},
            "required": ["level"],
        },
    },
    {
        "name": "reassemble_cut",
        "description": "Stitch the selected take of every shot into a new cut and upload to "
                       "R2. Fast (no generation). Use after changing takes, prompts that were "
                       "regenerated, or the audio duck.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_music_bed",
        "description": "Generate a background music track with Suno (via APIFrame) and set it as "
                       "the campaign's music bed. Instrumental by default. After this, call "
                       "reassemble_cut to mix it under the ad (ducked low).",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Describe the music: mood, genre, tempo, instruments."},
                "instrumental": {"type": "boolean", "description": "Default true; set false to allow vocals."},
                "tags": {"type": "string", "description": "Optional style tags, e.g. 'upbeat acoustic pop'."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "run_release_qa",
        "description": "Run the automated QA / continuity / governance checklist on the current "
                       "project (no-likeness legal gate + negative-prompt scan, grounded in the "
                       "style kernel). Returns a per-item PASS/FAIL/WARN report. Does NOT release "
                       "anything — it informs the human approval step.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "edit_shot",
        "description": "EDIT a shot's current take in place with Runway Gen-4 Aleph — relight, "
                       "change camera angle, add/remove/replace an object, restyle, or add a VFX — "
                       "instead of regenerating from scratch. Non-destructive: appends a new take. "
                       "Use for 'make scene 2 golden hour', 'orbit the camera left', 'remove the sign'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_number": {"type": "integer"},
                "edit_prompt": {"type": "string", "description": "The edit instruction applied to the existing clip."},
            },
            "required": ["scene_number", "edit_prompt"],
        },
    },
    {
        "name": "run_style_validation",
        "description": "Run the Style-Bible Validator (Phase B eval harness): per-shot scoring "
                       "against the kernel — no-likeness, negatives, casting-canon continuity, "
                       "palette/motif, performance register, kernel-look. Returns scores + flags so "
                       "you can fix weak shots before release.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_release_gate",
        "description": "Show whether the current project's master cut is cleared to publish, and "
                       "if not, the exact outstanding blockers (rights/consent/QA/no-likeness).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_approval_queue",
        "description": "Studio-wide risk-scored approval queue (Phase B): master cuts awaiting the "
                       "non-delegable A4 release decision, highest risk first, with the reasons each "
                       "is risky (likeness/consent/QA gaps).",
        "input_schema": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["pending", "all"],
                       "description": "pending (default) hides already-released masters."}}},
    },
    {
        "name": "approve_release",
        "description": "Non-delegable human release approval for the current master cut. Records "
                       "the QA result + rights states and flips approvedForRelease ONLY if the gate "
                       "is satisfied — or via an explicit, logged override. Publication (R2) stays "
                       "blocked until this passes. You MUST confirm the no-likeness legal gate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reviewer": {"type": "string", "description": "Who is approving (e.g. 'brad')."},
                "no_likeness_confirmed": {"type": "boolean",
                    "description": "Human confirmation that no shot resembles a real public figure (LEGAL GATE)."},
                "source_material_state": {"type": "string", "enum": ["CLEARED", "NOT_APPLICABLE", "PENDING", "BLOCKED"]},
                "likeness_state": {"type": "string", "enum": ["CLEARED", "NOT_APPLICABLE", "PENDING", "BLOCKED"]},
                "voice_state": {"type": "string", "enum": ["CLEARED", "NOT_APPLICABLE", "PENDING", "BLOCKED"]},
                "music_license_state": {"type": "string", "enum": ["CLEARED", "NOT_APPLICABLE", "PENDING", "BLOCKED"]},
                "vendor_terms_state": {"type": "string", "enum": ["CLEARED", "NOT_APPLICABLE", "PENDING", "BLOCKED"]},
                "override": {"type": "boolean", "description": "Explicit human override of remaining blockers (logged)."},
                "override_reason": {"type": "string", "description": "Required when override=true."},
            },
            "required": ["reviewer"],
        },
    },
    {
        "name": "edit_image",
        "description": "EDIT a still image with the self-hosted ComfyUI box (img2img): restyle, "
                       "recolor, relight, or nudge an existing produced image toward a text change "
                       "while keeping its composition. Works on a take's image (scene_number) or any "
                       "image path. Non-destructive: writes a NEW file (and appends an image take when "
                       "a scene is targeted). Needs the box + tunnel up (cli/box.ps1 start + tunnel).",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to the image to edit. Omit to use the selected take's image of scene_number."},
                "scene_number": {"type": "integer", "description": "Shot whose selected take's image to edit (alternative to image_path)."},
                "change": {"type": "string", "description": "The change to apply, described visually, e.g. 'make it golden hour'."},
                "model": {"type": "string", "enum": ["zimage", "flux2", "flux2-klein-9b-uncensored"],
                          "description": "On-box registry model (default zimage)."},
                "denoise": {"type": "number", "description": "Edit strength 0-1 (default 0.65; lower keeps more of the original)."},
                "seed": {"type": "integer"},
            },
            "required": ["change"],
        },
    },
    {
        "name": "inpaint_image",
        "description": "INPAINT part of a still image with the self-hosted ComfyUI box: only the "
                       "masked area changes, the rest is preserved pixel-for-pixel. Give either a "
                       "rectangular region 'x1,y1,x2,y2' (fractions 0-1 or pixels) or a mask image "
                       "(white=change, black=keep). Works on a take's image (scene_number) or any "
                       "image path; writes a NEW file. Needs the box + tunnel up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to the image to inpaint. Omit to use the selected take's image of scene_number."},
                "scene_number": {"type": "integer", "description": "Shot whose selected take's image to inpaint (alternative to image_path)."},
                "change": {"type": "string", "description": "What the masked area should become, e.g. 'a red umbrella'."},
                "region": {"type": "string", "description": "Rectangular mask 'x1,y1,x2,y2' — fractions 0-1 or pixels."},
                "mask": {"type": "string", "description": "Path to a mask image (white=change). Alternative to region."},
                "model": {"type": "string", "enum": ["zimage", "flux2", "flux2-klein-9b-uncensored"],
                          "description": "On-box registry model (default zimage)."},
                "seed": {"type": "integer"},
            },
            "required": ["change"],
        },
    },
    {
        "name": "get_tool_manual",
        "description": "Load the agent-readable manual for a tool/engine (TensorArt, Runway, "
                       "ComfyUI, Unreal, DaVinci Resolve, FFmpeg, ElevenLabs, Blender, Igniter) before "
                       "operating it — so your API calls are grounded in real docs (not hallucinated) "
                       "and you respect its action boundaries (credentials, payments, consent). Pass "
                       "the engine/tool name, e.g. 'runway' or 'tensorart'.",
        "input_schema": {"type": "object", "properties": {
            "tool": {"type": "string", "description": "engine/tool name, e.g. runway, tensorart, comfyui, resolve, ffmpeg, elevenlabs, ue, blender, igniter"}},
            "required": ["tool"]},
    },
    {
        "name": "list_models",
        "description": "List the studio's curated, capability-tagged model/engine catalog "
                       "(modality, provider, base, strengths, cost, recommended_for). TensorArt has "
                       "no list-all API, so this is the vetted registry the agent chooses from.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_models",
        "description": "Recommend the best generation models for a project, ranked, with a rationale "
                       "per model. Scores the catalog against the project's Style Kernel (look / "
                       "register / genre / aspect) and the modality the stage needs. Use this to pick "
                       "which model to render a shot with — e.g. recommend_models(project='new_harnomy_usa', "
                       "need='i2v'). Returns a shortlist; you make the final creative choice.",
        "input_schema": {"type": "object", "properties": {
            "project": {"type": "string", "description": "Project folder name under projects/ (reads its style_kernel.json). Omit to use the active project."},
            "need": {"type": "string", "enum": ["txt2img", "img2img", "keyframe", "t2v", "i2v", "v2v", "3d"],
                     "description": "The modality the stage requires. Omit to compare all modalities."},
            "type": {"type": "string", "description": "Optional project type hint (AD/SHORT/PILOT/...)."},
            "top_k": {"type": "integer", "description": "How many to return (default 5)."}}},
    },
]


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def _require_project(project_dir):
    if not project_dir:
        return None, "No active project yet. Call set_script first."
    project = ps.load_project(project_dir)
    if project is None:
        return None, f"No project.json found in {project_dir}. Call set_script first."
    return project, None


def _state_summary(project: dict) -> dict:
    shots = []
    for s in sorted(project["shots"], key=lambda x: x["scene_number"]):
        shots.append({
            "scene_number": s["scene_number"],
            "visual_prompt": (s.get("visual_prompt") or "")[:200],
            "voiceover": s.get("voiceover", ""),
            "selected_take": s.get("selected_take"),
            "takes": [{"take_id": t["take_id"], "model": t.get("model"), "ok": bool(t.get("video"))}
                      for t in s.get("takes", [])],
        })
    return {
        "business_name": project.get("business_name"),
        "vibe": project.get("vibe"),
        "format": project.get("format"),
        "audio_duck": project.get("audio_duck", 0.35),
        "shots": shots,
        "cuts": [{"cut_id": c["cut_id"], "output": c.get("output"), "public_url": c.get("public_url")}
                 for c in project.get("cuts", [])],
    }


def _release_line(cut: dict) -> str:
    """One-line publish/gate status for tool results."""
    if cut.get("published"):
        return f"Published to R2: {cut.get('public_url')}"
    blockers = cut.get("blockers") or []
    if blockers:
        return ("NOT published — release gate blocked: " + "; ".join(blockers)
                + " Use approve_release once rights + QA pass.")
    return "Assembled locally (not published)."


def _comfyui_still_edit(tool_input: dict, project_dir: str | None, inpaint: bool) -> str:
    """Shared body of the edit_image / inpaint_image tools: img2img or inpaint an
    existing still on the ComfyUI box via media/comfyui_engine.py. Returns the
    result text. Raises nothing silently — engine failures surface as the raise."""
    import time
    import tempfile
    from media import comfyui_engine as ce
    from ec2_session import COMFYUI_URL

    # Resolve the source image: explicit path, or the targeted shot's selected take.
    src = tool_input.get("image_path")
    project = ps.load_project(project_dir) if project_dir else None
    scene = tool_input.get("scene_number")
    if not src and project and scene is not None:
        shot = ps.get_shot(project, int(scene))
        take = ps.get_take(shot, shot.get("selected_take")) if shot else None
        src = (take or {}).get("image")
        if not src:
            return (f"Shot {scene}'s selected take has no still image to edit — "
                    f"pass image_path instead (video takes can't be inpainted here).")
    if not src:
        return "Pass image_path (or scene_number of a shot whose selected take has an image)."
    if not os.path.exists(src):
        return f"Image not found: {src}"

    base = COMFYUI_URL.rstrip("/")
    if not ce.is_up(base):
        return (f"ComfyUI is not reachable at {base}. Start the box + tunnel first "
                f"(cli/box.ps1 start, then cli/box.ps1 tunnel).")

    from PIL import Image
    w, h = Image.open(src).size

    mask_name = None
    if inpaint:
        region = tool_input.get("region")
        mask_path = tool_input.get("mask")
        if region:
            local_mask = ce.make_region_mask(region, w, h, save_dir=tempfile.gettempdir())
            mask_name = ce.upload_image(local_mask, base)
        elif mask_path and os.path.exists(mask_path):
            mask_name = ce.upload_image(mask_path, base)
        else:
            return "inpaint_image needs region='x1,y1,x2,y2' or mask=<image path>."

    img_name = ce.upload_image(src, base)
    model = tool_input.get("model") or ce.DEFAULT_MODEL
    seed = tool_input.get("seed")
    denoise = float(tool_input.get("denoise") or 0.65)
    graph = ce.build_graph(model, tool_input["change"], seed=seed, width=w, height=h,
                           img=img_name, mask=mask_name, denoise=denoise,
                           prefix="studio/edit")

    out_dir = project_dir or os.path.join("outputs", "_edits")
    stem = (os.path.splitext(os.path.basename(src))[0]
            + ("_inpaint" if inpaint else "_edit") + f"_{int(time.time())}")
    out_path = ce.submit_and_wait(graph, base, timeout=600,
                                  output_dir=out_dir, output_name=stem)

    note = ""
    if project and scene is not None and ps.get_shot(project, int(scene)) is not None:
        take_id = ps.add_take(project, int(scene), video=None, audio=None,
                              model=f"comfyui:{model}", status="done",
                              image=out_path, make_selected=False)
        ps.save_project(project_dir, project)
        note = f" Appended to shot {scene} as image take {take_id} (not selected)."
    verb = "Inpainted" if inpaint else "Edited"
    return f"{verb} via comfyui:{model} -> {out_path}.{note} Original untouched."


def execute_tool(name: str, tool_input: dict, project_dir: str | None, progress_cb=None) -> dict:
    def out(content, pdir=project_dir):
        return {"content": content if isinstance(content, str) else json.dumps(content), "project_dir": pdir}

    # ---- scaffold_project (creates a film-project folder tree under projects/) ----
    if name == "scaffold_project":
        import scaffold
        pname = tool_input.get("name") or "Untitled Project"
        root = scaffold.scaffold_project(
            pname,
            kernel=tool_input.get("kernel") or "new_harnomy",
            genre_packs=tool_input.get("genre_packs") or [],
            ptype=tool_input.get("type") or "SHORT",
        )
        packs = scaffold.resolve_packs(tool_input.get("genre_packs") or [])
        # Scaffold projects live under projects/ and are driven by the stage agents
        # (stage_ideate), not the ad project.json — so don't switch the active ad dir.
        return out(f"Scaffolded '{pname}' at {root}  (type={tool_input.get('type') or 'SHORT'}, "
                   f"packs={packs or 'core only'}). Develop stages via stage_ideate(project="
                   f"'{os.path.basename(root)}', stage='00_bible', message='…').")

    # ---- get_approval_queue (studio-wide; no active project required) ----
    if name == "get_approval_queue":
        from release_gate import get_approval_queue
        q = get_approval_queue(status=tool_input.get("status") or "pending")
        if q.get("error"):
            return out(f"Approval queue unavailable: {q['error']}")
        items = q.get("queue", [])
        if not items:
            return out("Approval queue empty — no masters awaiting a release decision.")
        hi = q.get("summary", {}).get("high", 0)
        lines = [f"{len(items)} master(s) awaiting the A4 release decision ({hi} high-risk):"]
        for i in items:
            why = "; ".join(i.get("factors", [])) or "ready (confirm + approve)"
            lines.append(f"  [{i['severity'].upper()} · risk {i['risk']} · {i['tier']}] "
                         f"{i.get('project')} — {why}")
        return out("\n".join(lines))

    # ---- edit_image / inpaint_image (ComfyUI still edits; project optional) ----
    if name in ("edit_image", "inpaint_image"):
        if not tool_input.get("change"):
            return out(f"{name} needs 'change' — the visual change to apply.")
        return out(_comfyui_still_edit(tool_input, project_dir, inpaint=(name == "inpaint_image")))

    # ---- get_tool_manual (load a tool's agent-readable manual into context) ----
    if name == "get_tool_manual":
        import tool_knowledge
        return out(tool_knowledge.get(tool_input.get("tool", "")))

    # ---- list_models (studio-wide catalog the agent chooses from) ----
    if name == "list_models":
        import model_select
        reg = model_select.load_registry()
        return out({"modalities": reg.get("modalities", {}), "models": reg.get("models", [])})

    # ---- recommend_models (kernel-matched shortlist; the deterministic half of model choice) ----
    if name == "recommend_models":
        import model_select
        kernel = {}
        proj = tool_input.get("project")
        if proj:
            from project_paths import resolve_project
            pdir = resolve_project(proj)
            kernel = model_select._load_kernel(pdir)
        elif project_dir:
            kernel = model_select._load_kernel(project_dir)
        ranked = model_select.recommend(kernel, need=tool_input.get("need"),
                                        project_type=tool_input.get("type"),
                                        top_k=int(tool_input.get("top_k", 5)))
        if not ranked:
            return out(f"No models match modality '{tool_input.get('need')}'. Use list_models for the full catalog.")
        head = "Recommended models (best first)" + (f" for need={tool_input['need']}" if tool_input.get("need") else "") + ":"
        lines = [head]
        for r in ranked:
            tag = "" if r["available"] else "  ⚠ unavailable"
            lines.append(f"  {r['score']:>5} · {r['id']} ({r['modality']}/{r['provider']}/{r['cost_tier']}){tag} — {r['why']}")
        return out("\n".join(lines))

    # ---- set_script (may create the project + its dir) ----
    if name == "set_script":
        scenes = tool_input.get("scenes", [])
        biz = tool_input.get("business_name") or "Ilyrium Campaign"
        vibe = tool_input.get("vibe") or "High-Energy & Loud"
        fmt = tool_input.get("format") or "9:16 (Instagram Reels/TikTok)"

        project = ps.load_project(project_dir) if project_dir else None
        if project is None:
            from utils.storage_manager import setup_campaign_directory
            project_dir, campaign_id = setup_campaign_directory(biz)
            project = ps.new_project(campaign_id, biz, vibe, fmt, scenes)
        else:
            # Update meta + merge scenes, preserving existing takes by scene_number.
            project["business_name"], project["vibe"], project["format"] = biz, vibe, fmt
            existing = {s["scene_number"]: s for s in project["shots"]}
            for sc in scenes:
                n = sc["scene_number"]
                if n in existing:
                    existing[n]["visual_prompt"] = sc.get("visual_prompt", existing[n].get("visual_prompt"))
                    existing[n]["voiceover"] = sc.get("voiceover", existing[n].get("voiceover"))
                    # Let the director attach/replace a per-shot input source.
                    if sc.get("source_image") is not None:
                        existing[n]["source_image"] = sc.get("source_image")
                    if sc.get("source_clip") is not None:
                        existing[n]["source_clip"] = sc.get("source_clip")
                else:
                    project["shots"].append({
                        "scene_number": n,
                        "visual_prompt": sc.get("visual_prompt", ""),
                        "voiceover": sc.get("voiceover", ""),
                        "source_image": sc.get("source_image"),
                        "source_clip": sc.get("source_clip"),
                        "takes": [], "selected_take": None, "audio_elements": [],
                    })
        # WRITE GATE (#3): authored scenes from the MCP must be conformant to persist.
        try:
            import conformance as cf
            cf.commit_guard("01_script", project["shots"])
        except Exception as e:
            errs = getattr(e, "errors", None)
            return out("Script REJECTED at the conformance gate — fix and resend: "
                       + ("; ".join(errs) if errs else str(e)), project_dir)
        ps.save_project(project_dir, project)
        return out(f"Script set: {len(project['shots'])} shot(s) for '{biz}' ({vibe}, {fmt}).", project_dir)

    # ---- read-only state ----
    if name == "get_project_state":
        project, err = _require_project(project_dir)
        if err:
            return out(err)
        return out(_state_summary(project))

    # everything below needs a project
    project, err = _require_project(project_dir)
    if err:
        return out(err)

    if name == "set_audio_duck":
        level = float(tool_input.get("level", 0.35))
        project["audio_duck"] = max(0.0, min(1.0, level))
        ps.save_project(project_dir, project)
        return out(f"Audio duck set to {project['audio_duck']:.2f}. Re-assemble the cut to hear it.")

    if name == "select_take":
        try:
            ps.set_selected_take(project, int(tool_input["scene_number"]), tool_input["take_id"])
            ps.save_project(project_dir, project)
            return out(f"Shot {tool_input['scene_number']} now uses {tool_input['take_id']}.")
        except Exception as e:
            return out(f"Could not select take: {e}")

    if name == "regenerate_shot":
        from producer import render_shot
        n = int(tool_input["scene_number"])
        shot = ps.get_shot(project, n)
        if shot is None:
            return out(f"No shot {n} exists.")
        if tool_input.get("new_visual_prompt"):
            shot["visual_prompt"] = tool_input["new_visual_prompt"]
        if tool_input.get("new_voiceover"):
            shot["voiceover"] = tool_input["new_voiceover"]
        ps.save_project(project_dir, project)
        take_id = render_shot(project, project_dir, n,
                              model=tool_input.get("model") or "grok-imagine",
                              regen_audio=bool(tool_input.get("regen_audio")),
                              progress_cb=progress_cb)
        project = ps.load_project(project_dir)  # refresh
        if take_id:
            return out(f"Shot {n} regenerated as {take_id} (now selected). Re-assemble the cut to see it in context.")
        return out(f"Shot {n} regeneration failed (no video produced) — check the log.")

    if name == "generate_first_cut":
        from producer import render_shot, assemble_cut
        gen_model = tool_input.get("model") or "grok-imagine"
        rendered = []
        for shot in sorted(project["shots"], key=lambda s: s["scene_number"]):
            sel = shot.get("selected_take")
            has_usable = sel and ps.get_take(shot, sel) and ps.get_take(shot, sel).get("video")
            if not has_usable:
                render_shot(project, project_dir, shot["scene_number"], model=gen_model, progress_cb=progress_cb)
                rendered.append(shot["scene_number"])
        project = ps.load_project(project_dir)
        cut = assemble_cut(project, project_dir, upload_to_r2=True, progress_cb=progress_cb)
        if cut.get("final_video"):
            return out(f"Generated shots {rendered} and assembled {cut['cut_id']}. {_release_line(cut)}")
        return out(f"Rendered shots {rendered} but assembly produced no cut — some shots may have failed.")

    if name == "reassemble_cut":
        from producer import assemble_cut
        cut = assemble_cut(project, project_dir, upload_to_r2=True, progress_cb=progress_cb)
        if cut.get("final_video"):
            return out(f"Assembled {cut['cut_id']}. {_release_line(cut)}")
        return out("No cut produced — make sure shots have selected takes.")

    if name == "run_release_qa":
        from release_gate import run_release_qa
        qa = run_release_qa(project, project_dir)
        lines = [qa["summary"]]
        for it in qa["items"]:
            lines.append(f"  [{it['status']}] {it['check']}: {it['detail']}")
        return out("\n".join(lines))

    if name == "edit_shot":
        from producer import edit_shot
        n = int(tool_input["scene_number"])
        if ps.get_shot(project, n) is None:
            return out(f"No shot {n} exists.")
        take_id = edit_shot(project, project_dir, n, tool_input.get("edit_prompt", ""),
                            progress_cb=progress_cb)
        project = ps.load_project(project_dir)
        if take_id:
            return out(f"Shot {n} edited via Gen-4 Aleph as {take_id} (now selected; original preserved). "
                       f"Re-assemble the cut to see it in context.")
        return out(f"Shot {n} edit failed — needs a selected take with video, and RUNWAYML_API_SECRET set.")

    if name == "run_eval":
        import evals
        rep = evals.run_project_eval(project, project_dir)
        pd = "; ".join(f"{k} avg {v['avg']}" + (f" ({v['fails']}✗)" if v['fails'] else "")
                       for k, v in (rep.get("per_dimension") or {}).items())
        return out(f"Style-Bible eval — overall {rep['overall_score']} / threshold {rep['threshold']} "
                   f"over {rep['n_shots']} shots; passed={rep['passed']}"
                   f"{' · HARD FAIL' if rep.get('hard_fail') else ''}. Recorded as an eval Run.\n  {pd}")

    if name == "run_style_validation":
        import style_validator
        r = style_validator.validate_project(project)
        lines = [r["summary"], f"overall {r['overall_score']} | hard_fail={r['hard_fail']}"]
        for s in r["shots"]:
            flags = [f"{c['dim']}({c['status']})" for c in s["checks"] if c["status"] in ("FAIL", "WARN")]
            lines.append(f"  scene {s['scene']}: {s['score']}" + (f" — {', '.join(flags)}" if flags else ""))
        return out("\n".join(lines))

    if name == "get_release_gate":
        from release_gate import check_release_gate
        gate = check_release_gate(project.get("campaign_id"))
        if gate.get("allowed"):
            return out("✅ Release gate: ALLOWED — this master is cleared to publish.")
        bl = gate.get("blockers", []) or ["(no master recorded yet — assemble a cut first)"]
        return out("⛔ Release gate: BLOCKED.\n" + "\n".join(f"  • {b}" for b in bl))

    if name == "approve_release":
        from release_gate import approve_release, run_release_qa
        reviewer = tool_input.get("reviewer") or "brad"
        if not tool_input.get("no_likeness_confirmed") and not tool_input.get("override"):
            return out("Refused: you must confirm the no-likeness legal gate "
                       "(no_likeness_confirmed=true) or pass override=true with override_reason.")
        qa = run_release_qa(project, project_dir)
        res = approve_release(
            project.get("campaign_id"), reviewer,
            qa_passed=qa.get("passed"), qa_report=qa,
            no_likeness_confirmed=bool(tool_input.get("no_likeness_confirmed")),
            source_material_state=tool_input.get("source_material_state"),
            likeness_state=tool_input.get("likeness_state"),
            voice_state=tool_input.get("voice_state"),
            music_license_state=tool_input.get("music_license_state"),
            vendor_terms_state=tool_input.get("vendor_terms_state"),
            override=bool(tool_input.get("override")),
            override_reason=tool_input.get("override_reason"),
        )
        if res.get("ok"):
            if res.get("approvedForRelease"):
                return out("✅ Approved for release. Call reassemble_cut to publish to R2.")
            return out("Recorded, but NOT released — remaining blockers:\n"
                       + "\n".join(f"  • {b}" for b in res.get("blockers", [])))
        return out(f"Approval failed: {res.get('error')}")

    if name == "generate_music_bed":
        from media.apiframe import generate_music
        out_path = os.path.join(project_dir, "music_bed.mp3")
        if progress_cb:
            progress_cb("🎵 Generating music via Suno (APIFrame)…")
        try:
            generate_music(tool_input["prompt"], out_path,
                           instrumental=tool_input.get("instrumental", True),
                           tags=tool_input.get("tags"))
        except Exception as e:
            return out(f"Music generation failed: {e}")
        project["music"] = out_path
        ps.save_project(project_dir, project)
        return out("Music bed generated and set. Call reassemble_cut to mix it under the ad.")

    return out(f"Unknown tool: {name}")
