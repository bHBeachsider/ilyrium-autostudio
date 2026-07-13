"""
Studio pipeline HTTP service (full build — installment 3): exposes the 8-stage
engine so the Next.js console can spin up a project from one prompt, run/advance it,
ingest per-stage notes/refs, and approve gates. Starlette + uvicorn (both already in
the venv); CORS-open to the console.

Run (on the host, alongside Streamlit + control-panel):
    cd apps/auto-studio
    .\venv\Scripts\python -m uvicorn studio_pipeline_service:app --port 8800

Endpoints (JSON):
  POST /pipeline/start        {prompt, mode}                 -> {run_id, state}
  GET  /pipeline/{run_id}                                    -> {state}
  POST /pipeline/{run_id}/advance                            -> {state}
  POST /pipeline/{run_id}/confirm                            -> {state}     (costly-stage go-ahead)
  POST /pipeline/{run_id}/reenter   {stage}                  -> {state}
  POST /pipeline/{run_id}/note      {stage, note, by}        -> {state}     (text/ref ingestion)
  POST /pipeline/{run_id}/approve   {reviewer, no_likeness_confirmed, override, override_reason}
  GET  /pipeline                                             -> {runs:[...]}

State is kept in-process per run_id and persisted to Neon (resumable) via
pipeline_exec.persist. Long stages (LLM/render) run in a threadpool so the event
loop stays responsive.
"""

import os
import json
import sys
import time
import uuid

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
os.chdir(_HERE)

# Windows default stdout is cp1252, which raises UnicodeEncodeError on emoji
# status glyphs (❌ 🎥 …) that the renderers/producer print — crashing renders on
# their own log lines. Force UTF-8 so any emoji print is safe process-wide.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except Exception:
    pass

try:
    from tracing import init_tracing
    init_tracing()   # no-op unless ILYRIUM_PHOENIX=1 + phoenix installed
except Exception:
    pass

from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

import threading

import studio_pipeline as sp

RUNS: dict = {}        # run_id -> state (mutated in place by the background runner)
_RUNNING: set = set()  # run_ids currently executing, so we don't double-launch


def _exec():
    import pipeline_exec
    return pipeline_exec.get_executors()


def _kick(rid):
    """Run the pipeline for `rid` in a background thread (non-blocking). The run
    mutates RUNS[rid] in place, so GET /pipeline/{rid} reflects live progress."""
    if rid in _RUNNING or rid not in RUNS:
        return
    _RUNNING.add(rid)

    def _job():
        try:
            sp.run(RUNS[rid], _exec())
        except Exception as e:
            st = RUNS.get(rid)
            if st:
                st["status"] = "blocked"
                st.setdefault("log", []).append({"t": "", "msg": f"run error: {type(e).__name__}: {e}"})
        finally:
            _RUNNING.discard(rid)
            _persist(RUNS.get(rid))

    threading.Thread(target=_job, daemon=True).start()


def _persist(state):
    try:
        import pipeline_exec
        pipeline_exec.persist(state)
    except Exception:
        pass


def _get(run_id):
    return RUNS.get(run_id)


def _adopt_film_project(ext):
    """Load a scaffolded FILM project (projects/<ext>) as an adoptable project: read its
    02_script/scenes.json into the project-store shape so the stage workspaces populate.
    Returns (project_dict_or_None, project_dir)."""
    import json
    from project_paths import resolve_project
    base = resolve_project(ext)
    scenes_path = os.path.join(base, "02_script", "scenes.json")
    if not os.path.exists(scenes_path):
        return None, None
    try:
        scenes = json.load(open(scenes_path, encoding="utf-8"))
    except Exception:
        return None, None
    if not isinstance(scenes, list) or not any((s or {}).get("visual_prompt") for s in scenes):
        return None, None
    shots = [{"scene_number": s.get("scene_number", i + 1),
              "visual_prompt": s.get("visual_prompt", ""), "voiceover": s.get("voiceover", ""),
              "dialogue": s.get("dialogue", []), "performance": s.get("performance", ""),
              "takes": [], "selected_take": None, "audio_elements": []}
             for i, s in enumerate(scenes)]
    proj = {"campaign_id": ext, "business_name": ext, "vibe": "film", "format": "16:9",
            "shots": shots, "cuts": [], "is_film_project": True}
    return proj, base


async def adopt(request):
    """Open an EXISTING project in the pipeline workspaces. Resolves an auto-studio campaign
    (outputs/<externalId>/project.json) OR a scaffolded film project
    (projects/<externalId>/02_script/scenes.json). Body: { externalId }. Idempotent."""
    body = await request.json()
    ext = (body.get("externalId") or "").strip()
    if not ext:
        return JSONResponse({"error": "externalId required"}, status_code=400)
    import project_store as ps
    # Resolve BOTH namespaces: an auto-studio campaign (outputs/<ext>/project.json) OR a
    # scaffolded FILM project (projects/<ext>/02_script/scenes.json). Either opens the
    # stage workspaces; without this, film projects 404 and the console shows the bare form.
    pdir = os.path.join("outputs", ext)
    proj = ps.load_project(pdir)
    if not proj:
        proj, pdir = _adopt_film_project(ext)
    if not proj:
        return JSONResponse(
            {"error": f"no project for '{ext}' (looked in outputs/{ext}/project.json and "
                      f"projects/{ext}/02_script/scenes.json)"}, status_code=404)
    for rid, st in RUNS.items():           # reuse an existing adoption
        if st.get("campaign_id") == ext:
            return JSONResponse({"run_id": rid, "state": st})
    import uuid
    st = sp.new_state(proj.get("vibe") or ext, "manual")
    st["campaign_id"] = ext
    st["project_dir"] = pdir
    # Pre-mark completed stages from what's on disk so the rail reflects reality.
    shots = proj.get("shots", [])
    has_video = any(t.get("video") for s in shots for t in s.get("takes", []))
    has_cut = bool(proj.get("cuts"))
    for n, done in [(1, True), (2, bool(shots)), (3, bool(shots)),
                    (4, has_video), (5, has_video), (6, has_cut)]:
        if done:
            st["stages"][str(n)]["status"] = "done"
    st["stage"] = 6 if has_cut else (4 if has_video else 2)
    rid = uuid.uuid4().hex[:12]
    RUNS[rid] = st; _persist(st)
    return JSONResponse({"run_id": rid, "state": st})


async def scaffold_new(request):
    """Create a new FILM project tree from the console's New Project form.
    Body: { name, type?, kernel?, genre_packs? }. Wraps scaffold.scaffold_project.
    A blank kernel named after the project is the default (no New-Harnomy inheritance)."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)
    ptype = (body.get("type") or "SHORT").strip() or "SHORT"
    kernel = (body.get("kernel") or "").strip()
    packs = body.get("genre_packs") or []
    if isinstance(packs, str):
        packs = [p.strip() for p in packs.split(",") if p.strip()]
    import scaffold
    slug = scaffold.slugify(name)
    if not kernel:
        kernel = slug   # per-project blank kernel, not the New-Harnomy default
    try:
        root = await run_in_threadpool(scaffold.scaffold_project, name, None, kernel, packs, ptype)
    except Exception as e:
        return JSONResponse({"error": f"scaffold failed: {e}"}, status_code=500)
    return JSONResponse({"ok": True, "slug": slug, "externalId": slug, "path": root,
                         "type": ptype, "kernel": kernel,
                         "genre_packs": scaffold.resolve_packs(packs)})


async def start(request):
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required."}, status_code=400)
    mode = body.get("mode") or "assisted"
    run_id = uuid.uuid4().hex[:12]
    state = sp.new_state(prompt, mode)
    # Optional reference images attached to the brief — saved + noted for later use.
    refs = []
    for img in (body.get("images") or []):
        try:
            import base64
            rdir = os.path.join("outputs", "_director_refs")
            os.makedirs(rdir, exist_ok=True)
            p = os.path.join(rdir, img["name"])
            with open(p, "wb") as f:
                f.write(base64.b64decode(img["b64"]))
            refs.append(p.replace(os.sep, "/"))
        except Exception:
            pass
    if refs:
        state["brief_refs"] = refs
    state["status"] = "running"   # reflect immediately so the client starts polling
    RUNS[run_id] = state
    _persist(state)
    _kick(run_id)   # run in the background; the client polls GET /pipeline/{run_id}
    return JSONResponse({"run_id": run_id, "state": state})


async def status(request):
    st = _get(request.path_params["run_id"])
    return JSONResponse({"state": st} if st else {"error": "unknown run_id"}, status_code=200 if st else 404)


async def advance(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    st["status"] = "running"
    _kick(rid)   # background; client polls
    return JSONResponse({"state": st})


async def confirm(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    sp.confirm_cost(st)
    st["status"] = "running"
    _kick(rid)
    return JSONResponse({"state": st})


async def reenter(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    body = await request.json()
    st = sp.reenter(st, int(body.get("stage", st["stage"])))
    RUNS[rid] = st; _persist(st)
    return JSONResponse({"state": st})


async def note(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    body = await request.json()
    stage = int(body.get("stage", st["stage"]))
    text = body.get("note", "")
    # Optional visual-object ingestion: base64 image saved as a stage reference.
    if body.get("image_b64") and body.get("image_name"):
        try:
            import base64
            refdir = os.path.join("outputs", "_pipeline_refs", rid)
            os.makedirs(refdir, exist_ok=True)
            path = os.path.join(refdir, body["image_name"])
            with open(path, "wb") as f:
                f.write(base64.b64decode(body["image_b64"]))
            text = (text + f"  [ref image: {path.replace(os.sep, '/')}]").strip()
        except Exception as e:
            text = (text + f"  [image save failed: {e}]").strip()
    st = sp.add_note(st, stage, text, body.get("by", "brad"))
    RUNS[rid] = st; _persist(st)
    return JSONResponse({"state": st})


async def approve(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    body = await request.json()
    reviewer = body.get("reviewer", "brad")
    if st.get("stage") == 7:   # release gate → non-delegable A4 rights approval
        if not body.get("no_likeness_confirmed") and not body.get("override"):
            return JSONResponse({"error": "no_likeness_confirmed (or override+reason) required at the release gate."}, status_code=400)
        try:
            from release_gate import approve_release
            res = approve_release(st.get("campaign_id"), reviewer,
                                  no_likeness_confirmed=bool(body.get("no_likeness_confirmed")),
                                  source_material_state="NOT_APPLICABLE", likeness_state="NOT_APPLICABLE",
                                  voice_state="NOT_APPLICABLE", music_license_state="NOT_APPLICABLE",
                                  vendor_terms_state="NOT_APPLICABLE", qa_passed=True,
                                  override=bool(body.get("override")), override_reason=body.get("override_reason"))
            if not res.get("approvedForRelease") and not body.get("override"):
                return JSONResponse({"error": "Release gate blocked: " + "; ".join(res.get("blockers", [])), "state": st}, status_code=200)
        except Exception as e:
            return JSONResponse({"error": f"approve_release failed: {e}"}, status_code=500)
    sp.approve(st, reviewer)
    if st.get("status") != "complete":
        st["status"] = "running"
    RUNS[rid] = st; _persist(st)
    _kick(rid)
    return JSONResponse({"state": st})


def _load_project(rid):
    st = RUNS.get(rid)
    if not st or not st.get("project_dir"):
        return None, None
    import project_store as ps
    return ps.load_project(st["project_dir"]), st["project_dir"]


def _shots_payload(proj, rid):
    out = []
    for s in sorted(proj.get("shots", []), key=lambda x: x.get("scene_number", 0)):
        out.append({
            "scene_number": s["scene_number"], "visual_prompt": s.get("visual_prompt", ""),
            "voiceover": s.get("voiceover", ""), "selected_take": s.get("selected_take"),
            "takes": [{"take_id": t["take_id"], "model": t.get("model"),
                       "ok": bool(t.get("video") or t.get("image")),
                       "file": (os.path.basename(t["video"]) if t.get("video")
                                else os.path.basename(t["image"]) if t.get("image") else None),
                       "image": (os.path.basename(t["image"]) if t.get("image") else None),
                       "public_url": t.get("public_url")} for t in s.get("takes", [])],
        })
    return {"run_id": rid, "shots": out}


async def shots(request):
    rid = request.path_params["run_id"]
    proj, _ = _load_project(rid)
    return JSONResponse(_shots_payload(proj, rid) if proj else {"run_id": rid, "shots": []})


async def shot_action(request):
    """op = regenerate | edit (Aleph) | select | astria_refine (SDXL/Flux LoRA, see docs/ASTRIA_REFINE_OP.md)."""
    rid = request.path_params["run_id"]; n = int(request.path_params["n"])
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    body = await request.json(); op = body.get("op")
    import project_store as ps
    if op == "select":
        try:
            ps.set_selected_take(proj, n, body["take_id"]); ps.save_project(pdir, proj)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    elif op == "regenerate":
        from producer import render_shot
        shot = ps.get_shot(proj, n)
        if body.get("prompt"):
            shot["visual_prompt"] = body["prompt"]; ps.save_project(pdir, proj)
        await run_in_threadpool(render_shot, proj, pdir, n, body.get("model", "grok-imagine"))
        proj = ps.load_project(pdir)
    elif op == "edit":
        from producer import edit_shot
        await run_in_threadpool(edit_shot, proj, pdir, n, body.get("edit_prompt", ""))
        proj = ps.load_project(pdir)
    elif op == "astria_refine":
        # HITL refinement via the character LoRA (SDXL/Flux on Astria). Controls live in the
        # Stage-4 console (AstriaRefine.tsx); backend = producer.refine_shot_astria. See
        # docs/ASTRIA_REFINE_OP.md. Actionable errors (tune not registered / status != trained)
        # surface as 400 so the console shows them instead of a silent failure.
        from producer import refine_shot_astria
        try:
            await run_in_threadpool(refine_shot_astria, proj, pdir, n, body)
        except Exception as e:
            return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)
        proj = ps.load_project(pdir) or proj
    else:
        return JSONResponse({"error": "unknown op"}, status_code=400)
    return JSONResponse(_shots_payload(proj, rid))


async def media(request):
    rid = request.path_params["run_id"]
    st = RUNS.get(rid)
    if not st or not st.get("project_dir"):
        return JSONResponse({"error": "no run"}, status_code=404)
    from starlette.responses import FileResponse
    path = os.path.join(st["project_dir"], os.path.basename(request.path_params["file"]))
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


def _cut_payload(proj, rid):
    cuts = proj.get("cuts", [])
    last = cuts[-1] if cuts else None
    return {
        "run_id": rid, "audio_duck": proj.get("audio_duck", 0.35), "music": bool(proj.get("music")),
        "voice_casting": proj.get("voice_casting", {}),
        "cut": ({"cut_id": last["cut_id"],
                 "file": (os.path.basename(last["output"]) if last.get("output") else None),
                 "public_url": last.get("public_url"),
                 "release": last.get("release")} if last else None),
        "shots": [{"scene_number": s["scene_number"], "voiceover": (s.get("voiceover") or "")[:80],
                   "has_video": bool(s.get("selected_take"))}
                  for s in sorted(proj.get("shots", []), key=lambda x: x.get("scene_number", 0))],
    }


async def cut(request):
    rid = request.path_params["run_id"]
    proj, _ = _load_project(rid)
    return JSONResponse(_cut_payload(proj, rid) if proj else {"run_id": rid, "cut": None, "shots": []})


async def audio(request):
    """op = set_duck (level) | gen_music (music_prompt, instrumental?) | reassemble."""
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    import project_store as ps
    body = await request.json(); op = body.get("op")
    if op == "set_duck":
        proj["audio_duck"] = max(0.0, min(1.0, float(body.get("level", 0.35))))
        ps.save_project(pdir, proj)
    elif op == "gen_music":
        try:
            from media.apiframe import generate_music
            out = os.path.join(pdir, "music_bed.mp3")
            await run_in_threadpool(generate_music, body.get("music_prompt", ""), out,
                                    bool(body.get("instrumental", True)))
            proj["music"] = out; ps.save_project(pdir, proj)
        except Exception as e:
            return JSONResponse({"error": f"music generation failed: {e}"}, status_code=500)
    elif op == "reassemble":
        from producer import assemble_cut
        await run_in_threadpool(assemble_cut, proj, pdir, False)  # local cut; publish at delivery
        proj = ps.load_project(pdir)
    else:
        return JSONResponse({"error": "unknown op"}, status_code=400)
    return JSONResponse(_cut_payload(proj, rid))


def _ar(proj):
    return "9:16" if (proj.get("format", "") or "").strip().startswith("9:16") else "16:9"


# ---- Stage 2: Script + Style Kernel ----
async def script_get(request):
    rid = request.path_params["run_id"]
    proj, _ = _load_project(rid)
    if not proj:
        return JSONResponse({"run_id": rid, "scenes": [], "kernel": {}})
    scenes = [{"scene_number": s["scene_number"], "visual_prompt": s.get("visual_prompt", ""),
               "voiceover": s.get("voiceover", "")} for s in sorted(proj["shots"], key=lambda x: x["scene_number"])]
    import style_kernel as sk
    kernel = sk.get_kernel(proj) or {}
    return JSONResponse({"run_id": rid, "scenes": scenes, "kernel": kernel})


async def script_save(request):
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    import project_store as ps
    body = await request.json()
    scenes = body.get("scenes", [])
    existing = {s["scene_number"]: s for s in proj["shots"]}
    new_shots = []
    for sc in scenes:
        n = sc.get("scene_number")
        if n in existing:
            existing[n]["visual_prompt"] = sc.get("visual_prompt", existing[n].get("visual_prompt", ""))
            existing[n]["voiceover"] = sc.get("voiceover", existing[n].get("voiceover", ""))
            new_shots.append(existing[n])
        else:
            new_shots.append({"scene_number": n, "visual_prompt": sc.get("visual_prompt", ""),
                              "voiceover": sc.get("voiceover", ""), "source_image": None, "source_clip": None,
                              "takes": [], "selected_take": None, "audio_elements": []})
    proj["shots"] = new_shots  # the edited list is authoritative (reorder/add/remove; takes kept by number)
    if isinstance(body.get("kernel"), dict):
        proj["style_kernel"] = body["kernel"]
    # WRITE GATE (#3): a human/agent scene edit must be conformant to persist.
    import conformance as cf
    try:
        cf.commit_guard("01_script", new_shots)
    except cf.ConformanceError as e:
        return JSONResponse({"error": "conformance gate blocked this edit", "violations": e.errors},
                            status_code=422)
    ps.save_project(pdir, proj)
    return await script_get(request)


# ---- Stage 3: Storyboard / keyframe / anchor ----
async def storyboard_get(request):
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"run_id": rid, "scenes": [], "anchor_file": None})
    scenes = []
    for s in sorted(proj["shots"], key=lambda x: x["scene_number"]):
        kf = f"shot{s['scene_number']}_keyframe.png"
        scenes.append({"scene_number": s["scene_number"], "visual_prompt": s.get("visual_prompt", ""),
                       "keyframe_file": kf if os.path.exists(os.path.join(pdir, kf)) else None})
    anchor = proj.get("anchor_image")
    return JSONResponse({"run_id": rid, "scenes": scenes,
                         "anchor_file": (os.path.basename(anchor) if anchor and os.path.exists(anchor) else None)})


async def keyframe_gen(request):
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project"}, status_code=400)
    body = await request.json(); n = int(body.get("scene_number"))
    import project_store as ps
    import style_kernel as sk
    shot = ps.get_shot(proj, n)
    if not shot:
        return JSONResponse({"error": f"no scene {n}"}, status_code=404)
    try:
        from media.keyframe import generate_keyframe
        still = os.path.join(pdir, f"shot{n}_keyframe.png")
        await run_in_threadpool(generate_keyframe, shot.get("visual_prompt", ""), still,
                                sk.get_kernel(proj), _ar(proj), proj.get("anchor_image"))
    except Exception as e:
        return JSONResponse({"error": f"keyframe generation failed: {e}"}, status_code=500)
    return await storyboard_get(request)


async def anchor_set(request):
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project"}, status_code=400)
    import project_store as ps
    body = await request.json()
    if body.get("image_b64") and body.get("image_name"):
        import base64
        path = os.path.join(pdir, "anchor_" + os.path.basename(body["image_name"]))
        with open(path, "wb") as f:
            f.write(base64.b64decode(body["image_b64"]))
        proj["anchor_image"] = path
    elif body.get("scene_number") is not None:
        proj["anchor_image"] = os.path.join(pdir, f"shot{int(body['scene_number'])}_keyframe.png")
    ps.save_project(pdir, proj)
    return await storyboard_get(request)


# ---- Stage 8: Delivery (captions / platform presets / cutdowns) ----
async def deliver(request):
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    body = await request.json(); op = body.get("op")
    import delivery
    cuts = proj.get("cuts", [])
    master = cuts[-1].get("output") if cuts else None
    if op == "captions":
        res = await run_in_threadpool(delivery.build_captions, proj, pdir)
        try:
            from graph_sync import sync_asset, file_checksum
            sync_asset(external_id=proj.get("campaign_id"), uri=res["srt"], checksum=file_checksum(res["srt"]),
                       asset_type="SUBTITLE", storage_provider="local", provider="ilyrium", model="captions")
        except Exception:
            pass
        return JSONResponse({"ok": True, "captions": {"srt": os.path.basename(res["srt"]), "cues": res["cues"]}})
    if op == "ai_cutdown":   # LLM picks scenes → assemble a variant from existing takes (no master needed)
        try:
            out = await run_in_threadpool(delivery.ai_cutdown, proj, pdir, int(body.get("seconds", 15)))
            return JSONResponse({"ok": True, "file": os.path.basename(out)})
        except Exception as e:
            return JSONResponse({"error": f"ai_cutdown failed: {e}"}, status_code=500)
    if not master or not os.path.exists(master):
        return JSONResponse({"error": "no assembled master yet (assemble a cut first)"}, status_code=400)
    try:
        if op == "preset":
            out = await run_in_threadpool(delivery.export_preset, master, pdir, body.get("target", "9:16"))
        elif op == "cutdown":
            out = await run_in_threadpool(delivery.make_cutdown, master, pdir, int(body.get("seconds", 15)))
        else:
            return JSONResponse({"error": "unknown op"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"{op} failed: {e}"}, status_code=500)
    return JSONResponse({"ok": True, "file": os.path.basename(out)})


async def qc(request):
    """Frame-level QC of each shot's selected take (black/freeze/silence detectors)."""
    rid = request.path_params["run_id"]
    proj, _ = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    import qc as qcmod
    rep = await run_in_threadpool(qcmod.qc_project, proj)
    return JSONResponse({"ok": True, **rep})


async def eval_run(request):
    """Run the Style-Bible eval across the project; records an eval Run + returns the report."""
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    import evals
    report = await run_in_threadpool(evals.run_project_eval, proj, pdir)
    return JSONResponse({"ok": True, "report": report})


async def voices(request):
    """Set per-character voice casting: {casting: {narrator|<char>: {voice_id, stability, similarity, style}}}."""
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    if not proj:
        return JSONResponse({"error": "no project for this run yet"}, status_code=400)
    body = await request.json()
    if isinstance(body.get("casting"), dict):
        import project_store as ps
        proj["voice_casting"] = body["casting"]; ps.save_project(pdir, proj)
    return await cut(request)


# ---- Stage 1: Brief ----
async def brief_save(request):
    rid = request.path_params["run_id"]; st = _get(rid)
    if not st:
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    body = await request.json()
    if isinstance(body.get("fields"), dict):
        st["brief_fields"] = {**(st.get("brief_fields") or {}), **body["fields"]}
    if body.get("prompt"):
        st["prompt"] = body["prompt"]
    RUNS[rid] = st; _persist(st)
    return JSONResponse({"state": st})


async def listruns(request):
    return JSONResponse({"runs": [{"run_id": k, "campaign_id": v.get("campaign_id"),
                                   "stage": v.get("stage"), "status": v.get("status"),
                                   "mode": v.get("mode")} for k, v in RUNS.items()]})


async def conformance_report(request):
    """Phase 5 — surface the split. Returns the MECHANICAL verdict (guaranteed green by the
    gates) + throughput, plus the JUDGMENT checklist (the stochastic items only a human can
    rule on). The console shows mechanical as a badge and routes attention to judgment."""
    rid = request.path_params["run_id"]
    st = _get(rid)
    proj, _ = _load_project(rid)
    mech = {"ok": True, "violations": 0, "by_category": {}}
    if proj is not None:
        try:
            import conformance as cf
            mech = cf.metrics("01_script", proj.get("shots", []))
        except Exception:
            mech = (proj or {}).get("_conformance", mech)
    judgment = [
        {"key": "tone_holds", "label": "Tone holds — sincere, no wink (the irreducible call)"},
        {"key": "dramatic", "label": "Scenes work dramatically / land the beat"},
        {"key": "take_choice", "label": "Best take selected per shot"},
        {"key": "release", "label": "Cleared for release (rights / no-likeness)"},
    ]
    return JSONResponse({
        "run_id": rid,
        "mechanical": mech,                       # deterministic — should always be ok:true
        "throughput": (st or {}).get("throughput"),
        "stage": (st or {}).get("stage"),
        "status": (st or {}).get("status"),
        "judgment": judgment,                     # stochastic — what the human reviews
    })


async def models(request):
    """Kernel-ranked model recommendations for the open run, for the Asset Gen inspector's
    dropdown. need= optional modality filter (i2v default for the render stage)."""
    rid = request.path_params["run_id"]
    proj, pdir = _load_project(rid)
    need = request.query_params.get("need") or None
    try:
        import model_select
        kernel = model_select._load_kernel(pdir) if pdir else {}
        # the kernel can also live inline on the project (ad projects)
        if not kernel and proj and isinstance(proj.get("style_kernel"), dict):
            kernel = proj["style_kernel"]
        ranked = model_select.recommend(kernel, need=need, top_k=12)
        return JSONResponse({"run_id": rid, "need": need, "models": ranked})
    except Exception as e:
        return JSONResponse({"run_id": rid, "models": [], "error": str(e)})


async def health(request):
    return JSONResponse({"ok": True, "stages": [s["name"] for s in sp.STAGES], "active_runs": len(RUNS)})



# --------------------------------------------------------------------------- #
# Stage-1 Bible endpoints (data-driven from bible_checklist.json; see Stage1Bible.tsx + docs/BIBLE_OP.md)
# --------------------------------------------------------------------------- #
def _bible_repo_root():
    here = os.path.dirname(os.path.abspath(__file__))   # apps/auto-studio
    return os.path.dirname(os.path.dirname(here))        # ilyrium-autostudio


def _bible_project_dir(project):
    return os.path.join(_bible_repo_root(), "projects", project)


def _bible_find_element(dim, key):
    import bible_scaffold
    for d in bible_scaffold._load()["dimensions"]:
        if d["key"] == dim:
            for el in d["elements"]:
                if el["key"] == key:
                    return el
    return None


async def bible_checklist(request):
    """GET the 6-dimension checklist + per-element completion for a scaffold project."""
    import bible_scaffold
    project = request.path_params["project"]
    try:
        return JSONResponse(bible_scaffold.status_data(project))
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def bible_element(request):
    """POST {dim, key, text, instance?} -> write a natural-language element to its target
    (.md file, a style_kernel.json field, or casting_canon JSON)."""
    project = request.path_params["project"]
    body = await request.json()
    dim, key, text = body.get("dim"), body.get("key"), body.get("text", "")
    el = _bible_find_element(dim, key)
    if not el:
        return JSONResponse({"error": "unknown element"}, status_code=400)
    pdir = _bible_project_dir(project)
    tgt = el["target"]
    try:
        if "#" in tgt:                                   # style_kernel.json#<field>
            kf = os.path.join(pdir, "style_kernel.json"); field = tgt.split("#")[1]
            k = json.load(open(kf, encoding="utf-8"))
            if field in ("casting_canon", "palette_motifs", "engine_tails", "continuity"):
                try:
                    k[field] = json.loads(text)
                except Exception:
                    return JSONResponse({"error": "casting_canon must be valid JSON"}, status_code=400)
            else:
                k[field] = text
            json.dump(k, open(kf, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        else:
            bible = os.path.join(pdir, "01_development", "bible")
            rel = tgt.replace("<NN_name>", body.get("instance", "01_unnamed")).replace("<location>", body.get("instance", "location"))
            path = os.path.join(bible, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(f"# {el['name']}\n\n{text}\n")
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def bible_media(request):
    """POST {dim, key, filename, b64} -> save an attached image/video/file as element evidence
    (base64 JSON, matching the brief image_b64 convention; no multipart dep)."""
    project = request.path_params["project"]
    body = await request.json()
    dim, key = body.get("dim"), body.get("key")
    b64, filename = body.get("b64", ""), body.get("filename", "upload.bin")
    if not b64:
        return JSONResponse({"error": "no file"}, status_code=400)
    try:
        import base64, time
        raw = b64.split(",", 1)[-1]
        bible = os.path.join(_bible_project_dir(project), "01_development", "bible")
        mdir = os.path.join(bible, dim, "_media"); os.makedirs(mdir, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".bin"
        ts = int(time.time())
        out = os.path.join(mdir, f"{key}_{ts}{ext}")
        n = 1
        while os.path.exists(out):                      # same-second uploads must not overwrite
            out = os.path.join(mdir, f"{key}_{ts}_{n}{ext}"); n += 1
        open(out, "wb").write(base64.b64decode(raw))
        return JSONResponse({"ok": True, "file": os.path.relpath(out, bible)})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


def _bible_media_target(project, rel):
    """Resolve a client-supplied bible-relative path to an absolute path, traversal-guarded.

    Returns the absolute path only if it resolves to somewhere strictly INSIDE the project's
    bible dir; returns None for anything that escapes (.., absolute paths, drive-relative
    tricks, symlink escapes — realpath resolves before the containment check)."""
    bible = os.path.realpath(os.path.join(_bible_project_dir(project), "01_development", "bible"))
    target = os.path.realpath(os.path.join(bible, rel or ""))
    if not os.path.normcase(target).startswith(os.path.normcase(bible) + os.sep):
        return None
    return target


async def bible_media_file(request):
    """GET ?rel=<bible-relative path> -> serve an attached media file's bytes
    (best-effort content-type). rel comes from the checklist's per-element files[]."""
    project = request.path_params["project"]
    rel = request.query_params.get("rel", "")
    target = _bible_media_target(project, rel)
    if not target or not os.path.isfile(target):
        return JSONResponse({"error": "not found"}, status_code=404)
    import mimetypes
    ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
    return FileResponse(target, media_type=ctype)


async def bible_media_delete(request):
    """POST {rel} -> unlink one attached media file. Only files inside a _media/ folder
    under the bible dir may be deleted (authored .md/.json content is off limits)."""
    project = request.path_params["project"]
    body = await request.json()
    rel = body.get("rel", "")
    target = _bible_media_target(project, rel)
    if not target:
        return JSONResponse({"error": "invalid path"}, status_code=400)
    bible = os.path.realpath(os.path.join(_bible_project_dir(project), "01_development", "bible"))
    if "_media" not in os.path.relpath(target, bible).split(os.sep):
        return JSONResponse({"error": "only files under _media/ can be deleted"}, status_code=400)
    if not os.path.isfile(target):
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        os.unlink(target)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def bible_generate(request):
    """POST {dim, key, prompt, model_family?} -> generate an evidence image from a prompt via
    Astria (character elements use the project's character tune; others use the base tune)."""
    project = request.path_params["project"]
    body = await request.json()
    dim, key = body.get("dim"), body.get("key")
    prompt, fam = body.get("prompt", ""), body.get("model_family", "flux")
    if not prompt:
        return JSONResponse({"error": "prompt required"}, status_code=400)
    pdir = _bible_project_dir(project)
    try:
        from media import astria_renderer as ar
        tune = None
        if dim == "character":
            try:
                from producer import _resolve_tune
                _, tune = _resolve_tune(pdir, fam, None)
            except Exception:
                tune = None
        tune = tune or os.getenv("ASTRIA_BASE_TUNE", "")
        if not tune:
            return JSONResponse({"error": "no tune available (register a character LoRA or set ASTRIA_BASE_TUNE)"}, status_code=400)
        import time
        bible = os.path.join(pdir, "01_development", "bible")
        mdir = os.path.join(bible, dim, "_media"); os.makedirs(mdir, exist_ok=True)
        paths = await run_in_threadpool(ar.render_refine, tune, {"prompt[text]": prompt, "prompt[num_images]": 1},
                                        mdir, f"{key}_{int(time.time())}", 1)
        return JSONResponse({"ok": True, "file": os.path.relpath(paths[0], bible)})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)




# --------------------------------------------------------------------------- #
# Generalized stage checklist endpoints (any stage 1-11; reads bible_checklist + stage_checklists)
# --------------------------------------------------------------------------- #
async def stage_checklist(request):
    import stage_scaffold
    project = request.path_params["project"]; n = int(request.path_params["stage"])
    try:
        d = stage_scaffold.status(project, stage=n)
        return JSONResponse(d["stages"][0] if d["stages"] else {"error": "no such stage"})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def stage_element(request):
    import stage_scaffold
    project = request.path_params["project"]; n = int(request.path_params["stage"])
    body = await request.json()
    try:
        rel = stage_scaffold.write_element(project, n, body.get("key"), body.get("text", ""), body.get("instance", ""))
        return JSONResponse({"ok": True, "wrote": rel})
    except json.JSONDecodeError:
        return JSONResponse({"error": "expected valid JSON for this element"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)


async def stage_media(request):
    import stage_scaffold, base64, time
    project = request.path_params["project"]; n = int(request.path_params["stage"])
    body = await request.json()
    if not body.get("b64"):
        return JSONResponse({"error": "no file"}, status_code=400)
    try:
        mdir = stage_scaffold.media_dir(project, n, body.get("key", "el"))
        ext = os.path.splitext(body.get("filename", "x.bin"))[1] or ".bin"
        out = os.path.join(mdir, f"{body.get('key','el')}_{int(time.time())}{ext}")
        open(out, "wb").write(base64.b64decode(body["b64"].split(",", 1)[-1]))
        return JSONResponse({"ok": True, "file": os.path.basename(out)})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def stage_generate(request):
    import stage_scaffold, time
    project = request.path_params["project"]; n = int(request.path_params["stage"])
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        return JSONResponse({"error": "prompt required"}, status_code=400)
    pdir = _bible_project_dir(project)
    try:
        from media import astria_renderer as ar
        tune = None
        try:
            from producer import _resolve_tune
            _, tune = _resolve_tune(pdir, body.get("model_family", "flux"), None)
        except Exception:
            tune = None
        tune = tune or os.getenv("ASTRIA_BASE_TUNE", "")
        if not tune:
            return JSONResponse({"error": "no tune (register a character LoRA or set ASTRIA_BASE_TUNE)"}, status_code=400)
        mdir = stage_scaffold.media_dir(project, n, body.get("key", "gen"))
        paths = await run_in_threadpool(ar.render_refine, tune, {"prompt[text]": prompt, "prompt[num_images]": 1},
                                        mdir, f"{body.get('key','gen')}_{int(time.time())}", 1)
        return JSONResponse({"ok": True, "file": os.path.basename(paths[0])})
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)



# --------------------------------------------------------------------------- #
# Box / tunnel control — EC2 GPU box lifecycle for the console's Box panel
# (BoxPanel.tsx). Mirrors app.py's render_box_panel / console_helpers: AWS
# status cached ~5s so 5s polling doesn't spam describe-instances; every AWS /
# subprocess call is try/except-wrapped so missing creds degrade to a JSON
# error, never a 500. The SSH tunnel itself is opened by cli/box.ps1.
# --------------------------------------------------------------------------- #
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
_BOX_CACHE = {"ts": 0.0, "status": None}   # module-level ~5s cache of ec2_session.status()


def _box_aws_status(force: bool = False) -> dict:
    """ec2_session.status() with a ~5s cache; errors folded in as state='error'."""
    now = time.time()
    if not force and _BOX_CACHE["status"] is not None and now - _BOX_CACHE["ts"] < 5:
        return _BOX_CACHE["status"]
    try:
        import ec2_session
        s = ec2_session.status()
    except Exception as e:
        s = {"state": "error", "error": f"{type(e).__name__}: {e}",
             "instance_id": None, "public_ip": None}
    _BOX_CACHE["status"] = s
    _BOX_CACHE["ts"] = now
    return s


def _comfy_up() -> bool:
    try:
        import ec2_session
        return bool(ec2_session.is_comfyui_up(timeout=2))
    except Exception:
        return False


def _ollama_up() -> bool:
    """ollama :11434 reachable through the tunnel — the tunnel-up signal."""
    try:
        import requests
        r = requests.get(OLLAMA_URL.rstrip("/") + "/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _box_payload(force: bool = False) -> dict:
    s = dict(_box_aws_status(force))
    comfy = _comfy_up()
    s["comfyui_up"] = comfy
    # Tunnel inferred: ollama reachable, OR ComfyUI reachable while the box runs.
    s["tunnel_up"] = _ollama_up() or (comfy and s.get("state") == "running")
    return s


def _run_box_ps1(verb: str) -> str:
    """Launch cli/box.ps1 <verb> detached (pwsh preferred, powershell fallback).
    Fire-and-forget by design — the UI reflects the outcome via status polling."""
    import shutil
    import subprocess
    ps1 = os.path.join(_HERE, "cli", "box.ps1")
    if not os.path.exists(ps1):
        raise FileNotFoundError(f"box.ps1 not found at {ps1}")
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        raise RuntimeError("Neither pwsh nor powershell is on PATH.")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, verb],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=flags, cwd=_HERE)
    return f"box.ps1 {verb} launched ({os.path.basename(exe)})"


async def box_status(request):
    """GET /box/status -> {state, public_ip, comfyui_up, tunnel_up, ...}. ?force=1 bypasses the cache."""
    force = request.query_params.get("force") in ("1", "true")
    return JSONResponse(await run_in_threadpool(_box_payload, force))


async def box_start(request):
    """POST /box/start -> ec2_session.ensure_running(wait=False); returns fresh status."""
    def _go():
        try:
            import ec2_session
            ec2_session.ensure_running(wait=False)
        except Exception as e:
            return {"ok": False, "error": f"could not start the box: {type(e).__name__}: {e}",
                    **_box_payload(force=True)}
        return {"ok": True, **_box_payload(force=True)}
    return JSONResponse(await run_in_threadpool(_go))


async def box_stop(request):
    """POST /box/stop -> best-effort tunnel-down, then ec2_session.stop(); returns fresh status."""
    def _go():
        try:
            _run_box_ps1("tunnel-down")   # harmless if no tunnel is open
        except Exception:
            pass
        try:
            import ec2_session
            ec2_session.stop()
        except Exception as e:
            return {"ok": False, "error": f"could not stop the box: {type(e).__name__}: {e}",
                    **_box_payload(force=True)}
        return {"ok": True, **_box_payload(force=True)}
    return JSONResponse(await run_in_threadpool(_go))


async def box_tunnel(request):
    """POST /box/tunnel -> open the SSH tunnels (:8188 ComfyUI + :11434 ollama) via box.ps1."""
    try:
        msg = await run_in_threadpool(_run_box_ps1, "tunnel")
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"{type(e).__name__}: {e}"})
    return JSONResponse({"ok": True, "message": msg + " — status will update shortly."})


routes = [
    Route("/health", health),
    Route("/box/status", box_status, methods=["GET"]),
    Route("/box/start", box_start, methods=["POST"]),
    Route("/box/stop", box_stop, methods=["POST"]),
    Route("/box/tunnel", box_tunnel, methods=["POST"]),
    Route("/pipeline", listruns, methods=["GET"]),
    Route("/pipeline/start", start, methods=["POST"]),
    Route("/projects/scaffold", scaffold_new, methods=["POST"]),
    Route("/pipeline/adopt", adopt, methods=["POST"]),
    Route("/pipeline/{run_id}", status, methods=["GET"]),
    Route("/pipeline/{run_id}/advance", advance, methods=["POST"]),
    Route("/pipeline/{run_id}/confirm", confirm, methods=["POST"]),
    Route("/pipeline/{run_id}/reenter", reenter, methods=["POST"]),
    Route("/pipeline/{run_id}/note", note, methods=["POST"]),
    Route("/pipeline/{run_id}/approve", approve, methods=["POST"]),
    Route("/pipeline/{run_id}/shots", shots, methods=["GET"]),
    Route("/pipeline/{run_id}/shot/{n:int}/action", shot_action, methods=["POST"]),
    Route("/media/{run_id}/{file}", media, methods=["GET"]),
    Route("/bible/{project}/checklist", bible_checklist, methods=["GET"]),
    Route("/bible/{project}/element", bible_element, methods=["POST"]),
    Route("/bible/{project}/media", bible_media, methods=["POST"]),
    Route("/bible/{project}/media/file", bible_media_file, methods=["GET"]),
    Route("/bible/{project}/media/delete", bible_media_delete, methods=["POST"]),
    Route("/bible/{project}/generate", bible_generate, methods=["POST"]),
    Route("/stage/{project}/{stage:int}/checklist", stage_checklist, methods=["GET"]),
    Route("/stage/{project}/{stage:int}/element", stage_element, methods=["POST"]),
    Route("/stage/{project}/{stage:int}/media", stage_media, methods=["POST"]),
    Route("/stage/{project}/{stage:int}/generate", stage_generate, methods=["POST"]),
    Route("/pipeline/{run_id}/cut", cut, methods=["GET"]),
    Route("/pipeline/{run_id}/audio", audio, methods=["POST"]),
    Route("/pipeline/{run_id}/script", script_get, methods=["GET"]),
    Route("/pipeline/{run_id}/script", script_save, methods=["POST"]),
    Route("/pipeline/{run_id}/kernel", script_save, methods=["POST"]),
    Route("/pipeline/{run_id}/storyboard", storyboard_get, methods=["GET"]),
    Route("/pipeline/{run_id}/keyframe", keyframe_gen, methods=["POST"]),
    Route("/pipeline/{run_id}/anchor", anchor_set, methods=["POST"]),
    Route("/pipeline/{run_id}/brief", brief_save, methods=["POST"]),
    Route("/pipeline/{run_id}/deliver", deliver, methods=["POST"]),
    Route("/pipeline/{run_id}/voices", voices, methods=["POST"]),
    Route("/pipeline/{run_id}/eval", eval_run, methods=["POST"]),
    Route("/pipeline/{run_id}/qc", qc, methods=["POST"]),
    Route("/pipeline/{run_id}/conformance", conformance_report, methods=["GET"]),
    Route("/pipeline/{run_id}/models", models, methods=["GET"]),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
               allow_methods=["*"], allow_headers=["*"]),
]

app = Starlette(routes=routes, middleware=middleware)
