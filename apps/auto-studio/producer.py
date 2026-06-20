"""
Production orchestrator for Ilyrium Auto-Studio, backed by the non-destructive
project store (see project_store.py).

Three entry points:

  - render_shot(...)       render ONE shot -> append a Take (non-destructive)
  - assemble_cut(...)      stitch the SELECTED take of each shot -> a Cut + R2
  - produce_campaign(...)  full run: new project -> render every shot -> cut

Regenerating a shot never touches its siblings, so a run can be revised shot
by shot instead of re-rendered from scratch.
"""

import os
import json
from datetime import datetime

import project_store as ps


def _aspect_from_format(output_format: str) -> str:
    if output_format and output_format.strip().startswith("16:9"):
        return "16:9"
    return "9:16"


def _logger(progress_cb):
    def log(msg: str):
        print(msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass
    return log


_GROK_ALIASES = {"grok", "grok-imagine", "xai"}

# Adapter-bus fallback: if a premium engine errors (provider outage / rejection),
# fall through to the next, ending on the cheap/reliable draft engine. Override the
# whole map with ILYRIUM_FALLBACK_CHAINS (JSON: {"veo3":["veo3","kling","grok-imagine"]}).
_FALLBACK_CHAINS = {
    "veo3": ["veo3", "kling", "grok-imagine"],
    "veo3.1": ["veo3.1", "kling", "grok-imagine"],
    "kling": ["kling", "veo3.1", "grok-imagine"],
    "runway": ["runway", "kling", "grok-imagine"],
    "runway:veo3.1": ["runway:veo3.1", "veo3.1", "grok-imagine"],
    "keyframe": ["keyframe", "grok-imagine"],
    "comfyui": ["comfyui", "grok-imagine"],
}


def _fallback_chain(model: str) -> list:
    import json as _json
    try:
        override = _json.loads(os.getenv("ILYRIUM_FALLBACK_CHAINS", "{}"))
    except Exception:
        override = {}
    return override.get(model) or _FALLBACK_CHAINS.get(model, [model])


def _render_video(model, visual_prompt, scene_number, output_dir, aspect_ratio, output_name, kernel=None, cref=None):
    """Dispatch a single shot's video render to the right backend by model name,
    applying the Style Kernel per-engine. Engines: grok-imagine (xAI), veo3 /
    veo3.1 / kling / 'fal:<endpoint>' (fal.ai), comfyui (self-hosted), ue (Unreal),
    keyframe[:i2v] (Midjourney still -> image-to-video)."""
    from style_kernel import compose_prompt
    m = (model or "").lower()

    if not model or m in _GROK_ALIASES:
        from media.video_renderer import render_scene_video
        p = compose_prompt(visual_prompt, kernel, engine="grok-imagine") if kernel else visual_prompt
        return render_scene_video(p, scene_number, output_dir=output_dir,
                                  aspect_ratio=aspect_ratio, output_name=output_name)
    if m == "comfyui":
        from media.comfyui_renderer import render_scene_comfyui
        p = compose_prompt(visual_prompt, kernel, engine="comfyui") if kernel else visual_prompt
        return render_scene_comfyui(p, scene_number, output_dir=output_dir, output_name=output_name)
    if m == "ue":
        # UE renders a level sequence (visual_prompt = sequence path) — no composition.
        from media.ue_renderer import render_scene_ue
        return render_scene_ue(visual_prompt, scene_number, output_dir=output_dir,
                               output_name=output_name)
    if m.startswith("keyframe"):
        from media.keyframe import render_scene_keyframe
        i2v = m.split(":", 1)[1] if ":" in m else "kling"
        return render_scene_keyframe(visual_prompt, scene_number, output_dir=output_dir,
                                     output_name=output_name, kernel=kernel,
                                     aspect_ratio=aspect_ratio, i2v_model=i2v, cref=cref)
    if m.startswith("tensorart"):
        # TensorArt (TAMS). 'tensorart:<model_id>' renders i2v if a first-frame (cref/keyframe)
        # is available, else a txt2img still. Result is downloaded locally by the renderer.
        from media.tensorart_renderer import render_txt2img, render_i2v
        ta_model = model.split(":", 1)[1] if ":" in model else os.getenv("TENSORART_MODEL", "")
        p = compose_prompt(visual_prompt, kernel, engine="kling") if kernel else visual_prompt
        out = os.path.join(output_dir, output_name)
        ff = cref if cref and os.path.exists(str(cref)) else None
        if ff:
            return render_i2v(ff, p, out, model=ta_model)
        still = out.rsplit(".", 1)[0] + ".png"
        return render_txt2img(p, still, model=ta_model,
                              width=1080 if aspect_ratio == "9:16" else 1024,
                              height=1920 if aspect_ratio == "9:16" else 1024)
    if m.startswith("astria"):
        # Astria. 'astria:<base_tune_id>' -> still; 'astria:<base_tune_id>:<video_model>'
        # -> video (first frame rendered from the prompt, then animated). Character
        # likeness via FaceID tokens in the prompt, e.g. '<faceid:5055589:1.0> man'
        # (Robert, millan). Result downloaded locally by the renderer.
        from media.astria_renderer import render_txt2img as astria_txt2img, render_video as astria_video
        parts = model.split(":")
        base_tune = parts[1] if len(parts) > 1 and parts[1] else os.getenv("ASTRIA_BASE_TUNE", "")
        video_model = parts[2] if len(parts) > 2 else None
        p = compose_prompt(visual_prompt, kernel, engine="kling") if kernel else visual_prompt
        out = os.path.join(output_dir, output_name)
        if video_model:
            dur = int(os.getenv("ASTRIA_VIDEO_DURATION", "8" if video_model.startswith("veo") else "5"))
            return astria_video(p, p, out, model=base_tune, video_model=video_model,
                                duration=dur, aspect_ratio=aspect_ratio or "16:9")
        still = out.rsplit(".", 1)[0] + ".jpg"
        return astria_txt2img(p, still, model=base_tune, aspect_ratio=aspect_ratio or "1:1")
    if m.startswith("runway"):
        # Runway image/text-to-video (gen4.5 default; runway:veo3.1 / runway:gen4_turbo).
        from media.runway_renderer import render_image_to_video
        rmodel = m.split(":", 1)[1] if ":" in m else "gen4.5"
        p = compose_prompt(visual_prompt, kernel, engine="kling") if kernel else visual_prompt
        first_frame = cref if cref and (str(cref).startswith(("http", "data:")) or os.path.exists(str(cref))) else None
        return render_image_to_video(p, output_path=os.path.join(output_dir, output_name),
                                     image_ref=first_frame, model=rmodel, aspect_ratio=aspect_ratio)

    # fal text-to-video (veo3 / veo3.1 / kling / fal:<endpoint>)
    from media.fal_renderer import render_scene_video_fal
    p = compose_prompt(visual_prompt, kernel, engine=m) if kernel else visual_prompt
    return render_scene_video_fal(p, scene_number, output_dir=output_dir,
                                  aspect_ratio=aspect_ratio, output_name=output_name, model=model)


# --------------------------------------------------------------------------- #
# Render a single shot -> new take
# --------------------------------------------------------------------------- #
def render_shot(project: dict, project_dir: str, scene_number: int,
                model: str = "grok-imagine", regen_audio: bool = False,
                progress_cb=None) -> str | None:
    """Render one shot and append it as a new Take. Returns the take id (or
    None if the video render failed — a failed take is still recorded)."""
    from media.audio_generator import render_voiceover

    log = _logger(progress_cb)
    shot = ps.get_shot(project, scene_number)
    if shot is None:
        raise ValueError(f"No shot {scene_number} in project")

    take_index = len(shot["takes"]) + 1
    video_name = f"shot{scene_number}_take{take_index}.mp4"
    audio_name = f"shot{scene_number}.mp3"  # voiceover is per-shot, reused across takes
    aspect = _aspect_from_format(project.get("format", ""))

    # The project's Style Kernel (production look) is applied per-engine inside
    # _render_video. No kernel set -> prompts are unchanged (ad flow).
    try:
        from style_kernel import get_kernel
        _kernel = get_kernel(project)
    except Exception:
        _kernel = None

    # 1. Video (the part that changes between takes)
    import time as _time
    _t0 = _time.time()
    video_path = None
    video_err = None
    src_clip = shot.get("source_clip")
    src_image = shot.get("source_image")
    # Per-project continuity anchor: a locked reference still that keyframe shots
    # --cref against so faces/world stay consistent across shots. Auto-captured
    # from the first keyframe still if not explicitly set (see below).
    anchor = project.get("anchor_image")
    try:
        if src_clip and os.path.exists(src_clip):
            # Ingest an uploaded clip directly as this take (no generation).
            import shutil
            video_path = os.path.join(project_dir, video_name)
            shutil.copyfile(src_clip, video_path)
            log(f"📥 Shot {scene_number}: ingested uploaded clip as take {take_index}.")
        elif src_image and os.path.exists(src_image):
            # Animate an uploaded still as the first frame (continuity from upload).
            from media.keyframe import animate_still
            i2v = model.split(":", 1)[1] if model.startswith("keyframe:") else "kling"
            log(f"🖼️ Shot {scene_number}: animating uploaded image via {i2v}…")
            video_path = animate_still(src_image, shot["visual_prompt"], scene_number,
                                       output_dir=project_dir, output_name=video_name,
                                       kernel=_kernel, i2v_model=i2v)
        else:
            chain = _fallback_chain(model)
            last_err = None
            for eng in chain:
                try:
                    log(f"🎥 Shot {scene_number}: take {take_index} via {eng}"
                        + (f" (fallback from {model})" if eng != model else "…"))
                    video_path = _render_video(
                        eng, shot["visual_prompt"], scene_number,
                        output_dir=project_dir, aspect_ratio=aspect, output_name=video_name,
                        kernel=_kernel, cref=anchor,
                    )
                    model = eng  # record the engine that actually produced the take
                    break
                except Exception as fe:
                    last_err = fe
                    log(f"⚠️ {eng} failed ({type(fe).__name__}: {fe}); trying next in chain…")
            if video_path is None and last_err is not None:
                raise last_err
            # Auto-capture the first keyframe still as the project anchor so later
            # keyframe shots lock to it (cross-shot face consistency).
            if (model or "").lower().startswith("keyframe") and not anchor:
                still = os.path.join(project_dir, video_name.rsplit(".", 1)[0] + "_keyframe.png")
                if os.path.exists(still):
                    project["anchor_image"] = still
                    log(f"🔒 Anchor set from shot {scene_number} keyframe for cross-shot continuity.")
    except Exception as e:
        video_err = f"{type(e).__name__}: {e}"
        log(f"❌ Shot {scene_number} VIDEO error -> {video_err}")

    # 2. Voiceover (render once per shot, reuse for later takes)
    audio_path = os.path.join(project_dir, audio_name)
    if regen_audio or not os.path.exists(audio_path):
        log(f"🎙️ Shot {scene_number}: generating voiceover…")
        try:
            _cast = project.get("voice_casting") or {}
            _v = _cast.get(shot.get("speaker") or "narrator") or _cast.get("default") or {}
            audio_path = render_voiceover(
                shot["voiceover"], scene_number,
                output_dir=project_dir, output_name=audio_name,
                voice_id=_v.get("voice_id"), stability=_v.get("stability", 0.75),
                similarity=_v.get("similarity", 0.85), style=_v.get("style", 0.0),
            )
        except Exception as e:
            log(f"❌ Shot {scene_number} AUDIO error -> {type(e).__name__}: {e}")
            audio_path = None

    take_id = ps.add_take(
        project, scene_number,
        video=video_path, audio=audio_path, model=model,
        status="done" if video_path else "failed", error=video_err,
    )
    ps.save_project(project_dir, project)

    # Best-effort: record this take's video as an Asset + ProvenanceRecord in the graph.
    if video_path:
        try:
            from graph_sync import sync_asset, file_checksum
            sync_asset(external_id=project.get("campaign_id"), uri=video_path,
                       checksum=file_checksum(video_path), provider=model, model=model,
                       prompt=shot.get("visual_prompt"), scene_number=scene_number,
                       asset_type="video", storage_provider="local")
        except Exception:
            pass

    # Render-time trace + cost row (matrix P1): real latency + estimated cost per engine.
    try:
        from graph_sync import record_run, estimate_cost_cents
        _dur = float(os.getenv("ILYRIUM_SHOT_DURATION_SEC", "8"))
        record_run(project.get("campaign_id"), "render", entity_id=video_name,
                   agent_name=model, model=model, provider=model,
                   status="SUCCEEDED" if video_path else "FAILED",
                   latency_ms=int((_time.time() - _t0) * 1000),
                   cost_cents=estimate_cost_cents(model, _dur), duration_sec=_dur,
                   outputs={"scene": scene_number, "take": take_id})
    except Exception:
        pass

    return take_id if video_path else None


# --------------------------------------------------------------------------- #
# Edit a shot's selected take in place (Gen-4 Aleph) -> new take (non-destructive)
# --------------------------------------------------------------------------- #
def edit_shot(project: dict, project_dir: str, scene_number: int, edit_prompt: str,
              progress_cb=None) -> str | None:
    """Edit the SELECTED take of a shot with Runway Gen-4 Aleph (relight, change camera
    angle, add/remove/replace objects, restyle, VFX) and append the result as a NEW take.
    Non-destructive: the original take is preserved. Returns the new take id."""
    from media.runway_renderer import aleph_edit
    import time as _time
    log = _logger(progress_cb)
    shot = ps.get_shot(project, scene_number)
    if shot is None:
        raise ValueError(f"No shot {scene_number} in project")
    sel = shot.get("selected_take")
    take = ps.get_take(shot, sel) if sel else None
    src = take.get("video") if take else None
    if not src or not os.path.exists(src):
        log(f"❌ Shot {scene_number}: no usable selected take to edit.")
        return None

    aspect = _aspect_from_format(project.get("format", ""))
    take_index = len(shot["takes"]) + 1
    out = os.path.join(project_dir, f"shot{scene_number}_take{take_index}.mp4")
    video_ref = take.get("public_url") or src   # prefer a URL (e.g. R2) for large clips
    log(f"✂️ Shot {scene_number}: Aleph edit — {edit_prompt[:70]}")
    t0 = _time.time()
    try:
        aleph_edit(video_ref, edit_prompt, out, aspect_ratio=aspect)
    except Exception as e:
        log(f"❌ Aleph edit failed: {type(e).__name__}: {e}")
        return None

    take_id = ps.add_take(project, scene_number, video=out, audio=(take.get("audio") if take else None),
                          model="runway:aleph", status="done")
    ps.save_project(project_dir, project)
    try:
        from graph_sync import sync_asset, file_checksum, record_run, estimate_cost_cents
        sync_asset(external_id=project.get("campaign_id"), uri=out, checksum=file_checksum(out),
                   provider="runway", model="gen4_aleph", prompt=edit_prompt,
                   scene_number=scene_number, asset_type="video", storage_provider="local")
        record_run(project.get("campaign_id"), "edit", entity_id=os.path.basename(out),
                   agent_name="runway:aleph", model="gen4_aleph", provider="runway", status="SUCCEEDED",
                   latency_ms=int((_time.time() - t0) * 1000), cost_cents=estimate_cost_cents("gen4_aleph", 5),
                   outputs={"scene": scene_number, "edit": edit_prompt[:120]})
    except Exception:
        pass
    log(f"✅ Shot {scene_number} edited → {take_id} (original take preserved).")
    return take_id


# --------------------------------------------------------------------------- #
# Assemble a cut from the selected take of each shot
# --------------------------------------------------------------------------- #
def assemble_cut(project: dict, project_dir: str, upload_to_r2: bool = True,
                 progress_cb=None) -> dict:
    """Stitch the selected take of every shot into a new Cut. Non-destructive:
    each call produces a new versioned cut file."""
    from media.post_production import compile_final_video
    from utils.storage_manager import finalize_and_upload_campaign

    log = _logger(progress_cb)
    import time as _time
    _at0 = _time.time()

    # Mirror the project's scene/shot structure into the asset graph (best-effort)
    # so the console's Scripting/Generation/Assembly domains populate — not just the
    # per-asset provenance. Idempotent on externalId.
    try:
        from graph_sync import sync_autostudio_project
        sync_autostudio_project(project)
    except Exception:
        pass

    media = ps.selected_media(project)
    if not media:
        log("❌ No selected takes with video — nothing to assemble.")
        return {"cut_id": None, "final_video": None, "public_url": None}

    campaign_id = project["campaign_id"]
    cut_index = len(project["cuts"]) + 1
    output = os.path.join(project_dir, f"{campaign_id}_cut_{cut_index}.mp4")

    log(f"🎬 Assembling cut {cut_index} from {len(media)} shot(s)…")
    final_video = compile_final_video(
        media, output_filename=output, duck=project.get("audio_duck"),
        music_path=project.get("music"), music_gain=project.get("music_gain", 0.15),
    )
    if not final_video:
        log("❌ Assembly produced no file.")
        return {"cut_id": None, "final_video": None, "public_url": None}

    # --- Enforced release gate (Phase A step 5) ---
    # Register the master in the graph FIRST (local URI) so its RightsRecord
    # exists, run the automated QA checklist, then ask the gate BEFORE any
    # publish. The gate is fail-closed: if it can't be evaluated, we don't ship.
    checksum = None
    release_allowed = True
    blockers = []
    qa = None
    enforce = True
    try:
        from graph_sync import sync_asset, file_checksum
        from release_gate import run_release_qa, record_qa, check_release_gate, gate_enforced
        enforce = gate_enforced()
        checksum = file_checksum(final_video)
        # Master cut -> Asset + ProvenanceRecord + RightsRecord(approvedForRelease=false)
        sync_asset(external_id=campaign_id, uri=final_video, checksum=checksum,
                   provider="ffmpeg", model="moviepy-assembly", asset_type="master",
                   storage_provider="local")
        qa = run_release_qa(project, project_dir)
        record_qa(campaign_id, checksum, qa)
        log(f"🧪 Release QA: {qa['summary']}")
        gate = check_release_gate(campaign_id, checksum)
        release_allowed = bool(gate.get("allowed"))
        blockers = gate.get("blockers", []) or []
    except Exception as e:
        release_allowed = False
        blockers = [f"Release gate error ({type(e).__name__}: {e}) — publication blocked."]

    public_url = None
    published = False
    may_publish = release_allowed or (not enforce)
    if upload_to_r2 and not may_publish:
        log("⛔ Publication BLOCKED by the release gate:")
        for b in blockers:
            log(f"   • {b}")
        log("   Approve via approve_release (MCP) / the console once rights + QA pass.")
    elif upload_to_r2 and may_publish:
        if not release_allowed and not enforce:
            log("⚠️ Gate not satisfied but ILYRIUM_ENFORCE_RELEASE_GATE=0 — publishing anyway (logged).")
        log("☁️ Uploading cut to Cloudflare R2…")
        metadata = {
            "business_name": project.get("business_name"),
            "vibe": project.get("vibe"),
            "format": project.get("format"),
            "cut_index": cut_index,
            "take_map": {str(s["scene_number"]): s.get("selected_take") for s in project["shots"]},
        }
        try:
            public_url = finalize_and_upload_campaign(project_dir, campaign_id, metadata, final_video)
            published = bool(public_url)
        except Exception as e:
            log(f"❌ R2 upload failed: {e}")

        # C2PA content credentials on export (Phase A step 6). Master is approved
        # for release here, so attach + record the manifest (sidecar by default;
        # signed embed when a cert + c2patool are configured).
        try:
            from c2pa_sign import attach_c2pa
            from graph_sync import file_checksum
            upstream = []
            for m in media:
                if m.get("video") and os.path.exists(m["video"]):
                    try:
                        upstream.append(file_checksum(m["video"]))
                    except Exception:
                        pass
            cc = attach_c2pa(project, final_video, checksum=checksum,
                             upstream_checksums=upstream, public_url=public_url)
            log(f"🔏 C2PA {cc['mode']} credentials attached"
                + (" + recorded on provenance." if cc.get("recorded") else " (record best-effort)."))
        except Exception as e:
            log(f"⚠️ C2PA attach skipped: {e}")

    cut_id = ps.add_cut(project, output=final_video, public_url=public_url)
    # Annotate the cut with its release/publish status for the UI + audit trail.
    try:
        project["cuts"][-1]["release"] = {
            "published": published, "allowed": release_allowed, "enforced": enforce,
            "blockers": blockers, "checksum": checksum,
            "qa_passed": bool(qa and qa.get("passed")),
        }
    except Exception:
        pass
    ps.save_project(project_dir, project)
    log(f"✅ {cut_id} ready{' (published)' if published else ' (local only — not published)'}.")

    # Render-time trace row for the assembly step (matrix P1).
    try:
        from graph_sync import record_run
        record_run(campaign_id, "assemble", entity_id=cut_id, agent_name="ffmpeg",
                   model="moviepy-assembly", status="SUCCEEDED" if final_video else "FAILED",
                   latency_ms=int((_time.time() - _at0) * 1000), cost_cents=0,
                   outputs={"published": published, "shots": len(media)})
    except Exception:
        pass

    return {"cut_id": cut_id, "final_video": final_video, "public_url": public_url,
            "published": published, "release_allowed": release_allowed,
            "blockers": blockers, "qa": qa}


# --------------------------------------------------------------------------- #
# Full campaign run (first take of every shot, then a cut)
# --------------------------------------------------------------------------- #
def produce_campaign(business_name: str, vibe: str, output_format: str,
                     scenes: list, upload_to_r2: bool = True,
                     progress_cb=None) -> dict:
    """Create a project, render the first take of every shot, assemble a cut.
    Returns a result dict the Streamlit UI renders (kept backward-compatible)."""
    from utils.storage_manager import setup_campaign_directory

    log = _logger(progress_cb)
    project_dir, campaign_id = setup_campaign_directory(business_name)
    log(f"📁 Project: {project_dir}")

    project = ps.new_project(campaign_id, business_name, vibe, output_format, scenes)
    ps.save_project(project_dir, project)

    scene_results = []
    for shot in project["shots"]:
        n = shot["scene_number"]
        render_shot(project, project_dir, n, progress_cb=progress_cb)
        shot = ps.get_shot(project, n)
        sel = shot.get("selected_take")
        take = ps.get_take(shot, sel) if sel else (shot["takes"][-1] if shot["takes"] else None)
        scene_results.append({
            "scene_number": n,
            "video_ok": bool(take and take.get("video")),
            "video_error": take.get("error") if take else None,
        })

    cut = assemble_cut(project, project_dir, upload_to_r2=upload_to_r2, progress_cb=progress_cb)

    # Best-effort: mirror the project into the canonical asset graph (no-op if control-panel is down).
    try:
        from graph_sync import sync_autostudio_project
        sync_autostudio_project(project, scaffold_path=project_dir)
    except Exception:
        pass

    return {
        "campaign_id": campaign_id,
        "local_dir": project_dir,
        "project_dir": project_dir,
        "project": project,
        "final_video": cut.get("final_video"),
        "public_url": cut.get("public_url"),
        "scene_results": scene_results,
    }


# --------------------------------------------------------------------------- #
# Stage-4 HITL refinement via a character LoRA on Astria (SDXL / Flux).
# Spec: docs/ASTRIA_REFINE_OP.md. POSTs to /tunes/{tune_id}/prompts, polls,
# downloads the still(s), appends each as an IMAGE take (non-destructive).
# --------------------------------------------------------------------------- #
_FAMILY_BASE = {"sdxl": "sdxl1", "flux": "flux1"}

# body field -> Astria prompt[...] field. None/'' skipped; bools coerced to true/false.
_REFINE_PASSTHROUGH = {
    "text": "prompt[text]", "negative_prompt": "prompt[negative_prompt]",
    "controlnet": "prompt[controlnet]", "controlnet_txt2img": "prompt[controlnet_txt2img]",
    "controlnet_conditioning_scale": "prompt[controlnet_conditioning_scale]",
    "denoising_strength": "prompt[denoising_strength]",
    "input_image_url": "prompt[input_image_url]", "mask_image_url": "prompt[mask_image_url]",
    "garment_image_url": "prompt[garment_image_url]", "preset": "prompt[preset]",
    "lora_scale": "prompt[lora_scale]", "style": "prompt[style]",
    "aspect_ratio": "prompt[aspect_ratio]", "cfg_scale": "prompt[cfg_scale]",
    "steps": "prompt[steps]", "seed": "prompt[seed]",
    "face_correct": "prompt[face_correct]", "face_swap": "prompt[face_swap]",
    "super_resolution": "prompt[super_resolution]", "inpaint_faces": "prompt[inpaint_faces]",
    "hires_fix": "prompt[hires_fix]", "film_grain": "prompt[film_grain]",
}
_FLUX_ONLY = ("prompt[garment_image_url]", "prompt[preset]", "prompt[lora_scale]")


def _find_lora_library(project_dir: str) -> str:
    override = os.getenv("ILYRIUM_LORA_LIBRARY")
    if override and os.path.exists(override):
        return override
    cand = os.path.join(project_dir, "03_design", "characters", "loras", "lora_library.json")
    if os.path.exists(cand):
        return cand
    raise FileNotFoundError(
        f"lora_library.json not found under {project_dir}/03_design/characters/loras/. "
        "astria_refine needs a scaffolded film project with a trained character tune "
        "(or set ILYRIUM_LORA_LIBRARY).")


def _resolve_tune(project_dir: str, model_family, character):
    family = (model_family or "").lower()
    base_model = _FAMILY_BASE.get(family)
    if not base_model:
        raise ValueError(f"model_family must be one of {sorted(_FAMILY_BASE)}, got {model_family!r}")
    lib_path = _find_lora_library(project_dir)
    with open(lib_path, encoding="utf-8") as f:
        lib = json.load(f)
    matches = [l for l in lib.get("loras", [])
               if l.get("base_model") == base_model and (not character or l.get("name") == character)]
    if not matches:
        raise ValueError(f"no {family} ({base_model}) LoRA in {lib_path}"
                         + (f" for character {character!r}" if character else ""))
    if len(matches) > 1:
        names = ", ".join(l.get("name", "?") for l in matches)
        raise ValueError(f"multiple {family} LoRAs ({names}); pass body['character'] to disambiguate")
    entry = matches[0]
    if entry.get("status") != "trained":
        raise RuntimeError(
            f"LoRA {entry.get('name')!r} status is {entry.get('status')!r}, not 'trained'. "
            "Register the finished Astria tune first "
            "(python lora_gen.py --register-local <sdxl|flux> <file>, or re-poll the tune), "
            "then set astria_tune_id + status='trained' in lora_library.json.")
    tune_id = entry.get("astria_tune_id")
    if not tune_id:
        raise RuntimeError(f"LoRA {entry.get('name')!r} has no astria_tune_id in {lib_path}.")
    return entry, tune_id


def refine_shot_astria(project: dict, project_dir: str, scene_number: int, body: dict):
    """Generate refined still(s) for one shot via a character LoRA on Astria and append each
    as an IMAGE take. Returns {'take_ids', 'tune_id', 'files'}. See docs/ASTRIA_REFINE_OP.md."""
    from media import astria_renderer as ar

    entry, tune_id = _resolve_tune(project_dir, body.get("model_family"), body.get("character"))
    family = (body.get("model_family") or "").lower()

    fields = {}
    for k, dest in _REFINE_PASSTHROUGH.items():
        v = body.get(k)
        if v is None or v == "":
            continue
        fields[dest] = ("true" if v else "false") if isinstance(v, bool) else v
    if family == "sdxl":
        for fk in _FLUX_ONLY:
            fields.pop(fk, None)
    fields.setdefault("prompt[text]", entry.get("trigger_word", ""))
    num_images = max(1, int(body.get("num_images") or 1))
    fields["prompt[num_images]"] = num_images

    base_name = f"refine_s{scene_number}_{family}_{int(datetime.now().timestamp())}"
    paths = ar.render_refine(tune_id, fields, project_dir, base_name, num_images=num_images)

    model_label = f"astria_refine:{family}:{tune_id}"
    take_ids = []
    for p in paths:
        take_ids.append(ps.add_take(project, scene_number, video=None, audio=None,
                                    model=model_label, status="done", image=p,
                                    make_selected=False))
    ps.save_project(project_dir, project)
    return {"take_ids": take_ids, "tune_id": tune_id, "files": [os.path.basename(p) for p in paths]}
