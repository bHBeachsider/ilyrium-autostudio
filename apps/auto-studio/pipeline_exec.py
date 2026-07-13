"""
Pipeline executors (full build — installment 2): bind the 8-stage engine
(studio_pipeline.py) to the real studio work, and persist run-state to Neon via
/api/studio/pipeline.

Each executor takes the pipeline `state` and returns {ok, result, blocked?}. They
update the state in place with campaign_id / project_dir as the run materializes.
Imports are LAZY (inside each executor) so importing this module never triggers
heavy deps — only running a stage does.

Stage → work:
  1 brief        record the director prompt as the brief
  2 script       draft scenes from the prompt (LLM) → create the project_store project
  3 storyboard   (advisory; keyframes optional) — pass
  4 asset_gen    render each shot (producer.render_shot)
  5 review       (advisory; first usable take auto-selected) — pass
  6 assembly     assemble a LOCAL cut (no publish) → master asset + automated QA
  7 rights       run release QA; the human approves at the gate (approve_stage)
  8 delivery     publish (gate now allows) + C2PA + archive package
"""

import os

PIPELINE_URL = os.getenv("STUDIO_PIPELINE_URL", "http://127.0.0.1:3000/api/studio/pipeline")
ARCHIVE_URL = os.getenv("STUDIO_ARCHIVE_URL", "http://127.0.0.1:3000/api/studio/archive")


def persist(state: dict):
    """Best-effort: store the run state on the Project (resumable)."""
    ext = state.get("campaign_id")
    if not ext:
        return
    try:
        import requests
        requests.post(PIPELINE_URL, json={
            "externalId": ext, "pipelineState": state,
            "pipelineStage": state.get("stage"), "autonomyMode": state.get("mode"),
        }, timeout=15)
    except Exception as e:
        print(f"[PIPELINE] persist skipped ({type(e).__name__}: {e})")


# --------------------------------------------------------------------------- #
def _draft_scenes_once(prompt: str, n: int = 4, feedback: str = None, strict: bool = False) -> list:
    """One STRUCTURED draft of a scene list (#1). The model is forced to emit into the
    conformance scene-list schema via a tool call, so malformed output is impossible by
    construction. `feedback` (from the self-validation loop) is appended so the model fixes
    any residual content-rule misses. Raises if no API/key."""
    import anthropic, json
    import conformance as cf
    client = anthropic.Anthropic()
    schema = cf.schema_for("01_script", strict=strict)
    tool = {"name": "emit_scenes",
            "description": f"Emit exactly {n} ad scenes conforming to the schema.",
            "input_schema": schema}
    sys = ("You are an ad director. Call emit_scenes with the scene list. "
           "visual_prompt = a vivid, self-contained shot description (repeat any recurring "
           "subject's look every scene); do NOT include camera/lens/grade/parameter detail — "
           "the pipeline injects that. voiceover = spoken words only, no parentheticals or "
           "stage directions. No real-person likeness.")
    user = prompt if not feedback else f"{prompt}\n\n{feedback}"
    r = client.messages.create(model="claude-sonnet-5", max_tokens=1800, system=sys,
                               tools=[tool], tool_choice={"type": "tool", "name": "emit_scenes"},
                               messages=[{"role": "user", "content": user}])
    for b in r.content:
        if getattr(b, "type", None) == "tool_use" and b.name == "emit_scenes":
            return (b.input or {}).get("scenes", [])
    # Fallback: parse any JSON the model returned as text.
    import re
    text = "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", None) == "text")
    m = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not m:
        return []
    data = json.loads(m.group(0))
    return data.get("scenes", []) if isinstance(data, dict) else data


def _draft_scenes(prompt: str, n: int = 4) -> list:
    """Draft scenes that are CONFORMANT BY CONSTRUCTION (#2 self-validation loop): the
    model drafts, the deterministic contract validates, and on failure the errors are fed
    back so the model self-corrects — before the scenes ever leave this function."""
    import conformance as cf
    res = cf.generate_conformant("01_script",
                                 lambda fb: _draft_scenes_once(prompt, n, fb),
                                 max_tries=3)
    # The loop returns the best artifact; the write gate (below) is the hard stop.
    return res["artifact"] or []


def _beat(state, msg, **extra):
    """Heartbeat into the live run state so the console can SEE progress within a long stage
    (the run dict is mutated in place, so GET /pipeline/{id} polling reflects it). Proves the
    pipeline is working, not hung."""
    import time
    ts = time.strftime("%H:%M:%S")
    state.setdefault("log", []).append({"t": ts, "msg": msg})
    hb = {"t": ts, "msg": msg, "at": time.time()}
    hb.update(extra)
    state["heartbeat"] = hb


def _executors() -> dict:
    def brief(state):
        state["brief"] = state.get("brief") or state["prompt"]
        return {"ok": True, "result": "brief recorded"}

    def script(state):
        import project_store as ps
        if state.get("project_dir") and ps.load_project(state["project_dir"]):
            p = ps.load_project(state["project_dir"])
            return {"ok": True, "result": f"{len(p.get('shots', []))} existing shots"}
        from utils.storage_manager import setup_campaign_directory
        scenes = _draft_scenes(state["prompt"])
        if not scenes:
            return {"ok": False, "blocked": True, "result": "script draft returned no scenes"}
        # WRITE GATE (#3): nothing non-conformant enters the project store. The self-loop
        # should already have converged; this is the deterministic hard stop.
        import conformance as cf
        try:
            cf.commit_guard("01_script", scenes)
        except cf.ConformanceError as e:
            return {"ok": False, "blocked": True,
                    "result": "script blocked at the conformance gate: " + "; ".join(e.errors)}
        biz = (state.get("brief") or state["prompt"])[:48]
        pdir, cid = setup_campaign_directory(biz)
        project = ps.new_project(cid, biz, "High-Energy & Loud", "9:16 (Instagram Reels/TikTok)", scenes)
        ps.save_project(pdir, project)
        state["project_dir"] = pdir
        state["campaign_id"] = cid
        return {"ok": True, "result": f"drafted {len(scenes)} scenes → {cid}"}

    def storyboard(state):
        return {"ok": True, "result": "storyboard advisory (keyframes optional)"}

    def asset_gen(state):
        # Phase 4: shots are conformant by construction, so render them in PARALLEL (bounded
        # worker pool). The shared project dict + thread-safe save_project make the merge
        # trivial; per-shot heartbeats still stream to the console.
        import project_store as ps
        import throughput as tp
        from producer import render_shot
        project = ps.load_project(state["project_dir"])
        shots = sorted(project["shots"], key=lambda s: s["scene_number"])
        todo = [s for s in shots
                if not (s.get("selected_take") and ps.get_take(s, s["selected_take"])
                        and ps.get_take(s, s["selected_take"]).get("video"))]
        total = len(todo)
        if not total:
            return {"ok": True, "result": "all shots already rendered"}

        progress = {"n": 0}

        def render_one(shot):
            tid = render_shot(project, state["project_dir"], shot["scene_number"], model="grok-imagine")
            return {"ok": bool(tid), "first_pass": True, "result": tid}

        def on_event(kind, shot, payload):
            n = shot["scene_number"]
            if kind == "start":
                _beat(state, f"rendering shot {n}…", stage=4, done=progress["n"], total=total)
            elif kind == "done":
                progress["n"] += 1
                _beat(state, f"✓ shot {n} rendered ({progress['n']}/{total})",
                      stage=4, done=progress["n"], total=total)
            elif kind == "error":
                progress["n"] += 1
                _beat(state, f"⛔ shot {n} failed: {payload}", stage=4, done=progress["n"], total=total)

        workers = tp.worker_count()
        _beat(state, f"rendering {total} shot(s) across {workers} worker(s)…", stage=4, done=0, total=total)
        batch = tp.parallel_map(todo, render_one, workers=workers, on_event=on_event)
        ps.save_project(state["project_dir"], project)   # final consolidated save
        state["throughput"] = batch["meter"]
        m = batch["meter"]
        rendered = m["ok"]
        if batch["errors"]:
            return {"ok": False, "blocked": True,
                    "result": f"rendered {rendered}/{total}; failures: " + "; ".join(
                        f"shot {k}: {v}" for k, v in batch["errors"].items())}
        return {"ok": True,
                "result": f"rendered {rendered} shot(s) in {m['elapsed_s']}s "
                          f"({m['units_per_min']}/min, {workers} workers)"}

    def review(state):
        return {"ok": True, "result": "first usable take auto-selected per shot"}

    def assembly(state):
        import project_store as ps
        from producer import assemble_cut
        project = ps.load_project(state["project_dir"])
        _beat(state, "assembling cut (ffmpeg)…", stage=6)
        cut = assemble_cut(project, state["project_dir"], upload_to_r2=False)  # local only; publish at delivery
        if not cut.get("final_video"):
            return {"ok": False, "blocked": True, "result": "assembly produced no cut"}
        state["last_blockers"] = cut.get("blockers")
        return {"ok": True, "result": f"assembled {cut.get('cut_id')} (local); QA: {bool(cut.get('qa') and cut['qa'].get('passed'))}"}

    def rights(state):
        # Automated QA recorded; the human approves at this gate via approve_stage.
        import project_store as ps
        from release_gate import run_release_qa
        project = ps.load_project(state["project_dir"])
        qa = run_release_qa(project, state["project_dir"])
        state["qa_summary"] = qa.get("summary")
        return {"ok": True, "result": qa.get("summary")}

    def delivery(state):
        import project_store as ps
        from producer import assemble_cut
        project = ps.load_project(state["project_dir"])
        # PUBLISH GATE (#3/#4): nothing non-conformant ships. The rights gate already cleared
        # likeness; this is the final mechanical attestation before the master goes public.
        try:
            import conformance as cf
            cf.commit_guard("01_script", project.get("shots", []))
        except cf.ConformanceError as e:
            return {"ok": False, "blocked": True,
                    "result": "delivery blocked at the conformance gate: " + "; ".join(e.errors)}
        cut = assemble_cut(project, state["project_dir"], upload_to_r2=True)  # gate now allows -> publishes + C2PA
        try:
            import requests
            requests.post(ARCHIVE_URL, json={"externalId": state["campaign_id"]}, timeout=20)
        except Exception:
            pass
        return {"ok": True, "result": f"published={cut.get('published')} url={cut.get('public_url')}"}

    return {"brief": brief, "script": script, "storyboard": storyboard, "asset_gen": asset_gen,
            "review": review, "assembly": assembly, "rights": rights, "delivery": delivery}


def get_executors() -> dict:
    return _executors()
