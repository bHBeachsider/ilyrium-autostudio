"""
fal.ai video renderer — the "OpenRouter of media" path.

Renders a scene through fal.ai so the studio can use premium models (Google
Veo 3 / 3.1, Kling) with native audio and, for Kling/Veo, real synchronized
dialogue — instead of only xAI Grok. Mirrors media.video_renderer's contract:
returns the saved mp4 path, raises on failure (so the orchestrator records a
failed take with the reason).

fal's Python client reads the FAL_KEY env var automatically.
"""

import os
import requests

# Friendly model name -> (fal endpoint, argument builder(prompt, aspect, duration_s)).
FAL_MODELS = {
    "veo3": {
        "endpoint": "fal-ai/veo3",
        "build": lambda p, ar, dur: {
            "prompt": p, "aspect_ratio": ar, "duration": f"{dur}s",
            "resolution": "720p", "generate_audio": True, "enhance_prompt": True,
        },
    },
    "veo3.1": {
        "endpoint": "fal-ai/veo3.1",
        "build": lambda p, ar, dur: {
            "prompt": p, "aspect_ratio": ar, "duration": f"{dur}s",
            "resolution": "720p", "generate_audio": True, "enhance_prompt": True,
        },
    },
    "kling": {
        "endpoint": "fal-ai/kling-video/v3/pro/text-to-video",
        "build": lambda p, ar, dur: {"prompt": p, "aspect_ratio": ar, "duration": str(dur)},
    },
    # ByteDance Seedance 2.0 on fal (endpoint ids verified 2026-08-15 against fal.ai/models/bytedance/seedance-2.0/*):
    # text-to-video here; image-to-video (start + optional END frame) via render_i2v_fal(); omni
    # reference-to-video (up to 9 images / 3 videos / 3 AUDIO refs -> lip-sync) via render_reference_video_fal().
    # $0.30/s at 720p std, $0.24/s fast, ~2x at 1080p (i2v/t2v); duration "auto" or 4-15 s.
    "seedance2": {
        "endpoint": "bytedance/seedance-2.0/text-to-video",
        "build": lambda p, ar, dur: {"prompt": p, "aspect_ratio": ar if ar in _SEEDANCE_AR else "auto",
                                     "duration": str(max(4, min(15, int(dur)))), "resolution": "720p",
                                     "generate_audio": False},
    },
    "seedance2-fast": {
        "endpoint": "bytedance/seedance-2.0/fast/text-to-video",
        "build": lambda p, ar, dur: {"prompt": p, "aspect_ratio": ar if ar in _SEEDANCE_AR else "auto",
                                     "duration": str(max(4, min(15, int(dur)))), "resolution": "720p",
                                     "generate_audio": False},
    },
    # Seedance 2.5 on fal (verified 2026-08-15): a DIFFERENT tool, not a newer 2.0 — caps at 720p, but
    # 4-30 s native, up to 50 references (<=30 images, <=10 videos, <=10 audio; 30 s each pool), and
    # video-edit / video-extension by giving a reference VIDEO + prompt intent (no mode param).
    # ~$0.47/s at 720p ($0.22/s 480p); video refs bill at 0.6x. Prompt tokens are [Image1]/[Video1]/[Audio1]
    # (2.0 uses @Image1). i2v aspect_ratio is "auto" only (inherits the frame).
    "seedance2.5": {
        "endpoint": "bytedance/seedance-2.5/text-to-video",
        "build": lambda p, ar, dur: {"prompt": p, "aspect_ratio": ar if ar in _SEEDANCE_AR else "auto",
                                     "duration": str(max(4, min(30, int(dur)))), "resolution": "720p",
                                     "generate_audio": False},
    },
}

_SEEDANCE_AR = ("auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
SEEDANCE_I2V = {"seedance2": "bytedance/seedance-2.0/image-to-video",
                "seedance2-fast": "bytedance/seedance-2.0/fast/image-to-video",
                "seedance2.5": "bytedance/seedance-2.5/image-to-video"}
SEEDANCE_REF = {"seedance2": "bytedance/seedance-2.0/reference-to-video",
                "seedance2-fast": "bytedance/seedance-2.0/fast/reference-to-video",
                "seedance2.5": "bytedance/seedance-2.5/reference-to-video"}
# per-model contract limits (fal docs, 2026-08-15): duration range, reference caps, resolutions, ref token style
SEEDANCE_LIMITS = {
    "seedance2":      {"dur": (4, 15), "img": 9,  "vid": 3,  "aud": 3,  "res": ("480p", "720p", "1080p", "4k"), "tok": "@{kind}{n}",  "i2v_ar": _SEEDANCE_AR},
    "seedance2-fast": {"dur": (4, 15), "img": 9,  "vid": 3,  "aud": 3,  "res": ("480p", "720p", "1080p", "4k"), "tok": "@{kind}{n}",  "i2v_ar": _SEEDANCE_AR},
    "seedance2.5":    {"dur": (4, 30), "img": 30, "vid": 10, "aud": 10, "res": ("480p", "720p"),               "tok": "[{kind}{n}]", "i2v_ar": ("auto",)},
}


def seedance_ref_token(model: str, kind: str, n: int = 1) -> str:
    """The prompt token that names reference #n for this model: 2.0 -> '@Image1', 2.5 -> '[Image1]'.
    kind = 'Image' | 'Video' | 'Audio'."""
    lim = SEEDANCE_LIMITS.get(model, SEEDANCE_LIMITS["seedance2"])
    return lim["tok"].format(kind=kind, n=n)


def _extract_video_url(result) -> str | None:
    """fal results vary by model; find the produced video URL robustly."""
    if not isinstance(result, dict):
        return None
    v = result.get("video")
    if isinstance(v, dict) and v.get("url"):
        return v["url"]
    if isinstance(v, str) and v.startswith("http"):
        return v
    if isinstance(result.get("url"), str):
        return result["url"]
    # videos: [{url: ...}]
    vids = result.get("videos")
    if isinstance(vids, list) and vids and isinstance(vids[0], dict) and vids[0].get("url"):
        return vids[0]["url"]
    # last resort: any nested {"url": ...}
    for val in result.values():
        if isinstance(val, dict) and isinstance(val.get("url"), str):
            return val["url"]
    return None


def render_scene_video_fal(visual_prompt: str, scene_number: int, output_dir: str = ".",
                           aspect_ratio: str = "16:9", output_name: str = None,
                           model: str = "veo3", duration_seconds: int = 8) -> str:
    """Render one scene via fal.ai and save it. `model` is a key in FAL_MODELS
    (veo3 / veo3.1 / kling) or a raw 'fal:<endpoint>' string."""
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not set — cannot call fal.ai.")

    import fal_client  # lazy: only needed when actually rendering via fal

    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, output_name or f"scene_{scene_number}.mp4")

    # Resolve endpoint + arguments
    if model.startswith("fal:"):
        endpoint = model[len("fal:"):]
        arguments = {"prompt": visual_prompt, "aspect_ratio": aspect_ratio}
    elif model in FAL_MODELS:
        spec = FAL_MODELS[model]
        endpoint = spec["endpoint"]
        arguments = spec["build"](visual_prompt, aspect_ratio, duration_seconds)
    else:
        raise ValueError(f"Unknown fal model '{model}'. Known: {list(FAL_MODELS)} or 'fal:<endpoint>'.")

    print(f"\n🎥 [FAL PRODUCER] Scene {scene_number} via {endpoint} ({aspect_ratio}, {duration_seconds}s)…")

    def _on_update(update):
        if isinstance(update, getattr(fal_client, "InProgress", ())):
            for log in getattr(update, "logs", []) or []:
                msg = log.get("message") if isinstance(log, dict) else str(log)
                if msg:
                    print(f"   fal: {msg}")

    result = fal_client.subscribe(endpoint, arguments=arguments, with_logs=True, on_queue_update=_on_update)

    url = _extract_video_url(result)
    if not url:
        raise RuntimeError(f"fal returned no video URL for scene {scene_number}: keys={list(result) if isinstance(result, dict) else type(result)}")

    print(f"📥 Downloading fal video for scene {scene_number}…")
    data = requests.get(url, timeout=300)
    data.raise_for_status()
    with open(output_filename, "wb") as f:
        f.write(data.content)

    print(f"✅ [FAL PRODUCER] Scene {scene_number} saved as {output_filename}")
    return output_filename


# --------------------------------------------------------------------------- #
# Seedance 2.0 image-to-video (start + optional END frame) and omni reference-to-video
# (audio refs -> lip-sync). Same contract as the other renderers: return the saved path, raise
# on failure. Local paths are uploaded with fal_client.upload_file; http(s) URLs pass through.
# --------------------------------------------------------------------------- #
def _fal_url(path_or_url: str) -> str:
    if str(path_or_url).startswith(("http://", "https://", "data:")):
        return str(path_or_url)
    import fal_client
    return fal_client.upload_file(str(path_or_url))


def _download_fal(url: str, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    d = requests.get(url, timeout=600)
    d.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(d.content)
    return output_path


def render_i2v_fal(prompt: str, image: str, output_path: str, model: str = "seedance2",
                   end_image: str = None, duration: int = 8, resolution: str = "720p",
                   aspect_ratio: str = "auto", generate_audio: bool = False) -> str:
    """Seedance 2.0 image-to-video from a locked first frame, with an optional LAST frame
    (held stage pictures, transitions). `image`/`end_image` = local path or URL."""
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not set - cannot call fal.ai.")
    import fal_client
    endpoint = SEEDANCE_I2V.get(model)
    if not endpoint:
        raise ValueError(f"Unknown Seedance i2v model '{model}'. Known: {list(SEEDANCE_I2V)}")
    lim = SEEDANCE_LIMITS[model]
    lo, hi = lim["dur"]
    if resolution not in lim["res"]:
        print(f"[FAL SEEDANCE] {model} does not offer {resolution}; using 720p (allowed: {lim['res']})")
        resolution = "720p"
    args = {"prompt": prompt, "image_url": _fal_url(image),
            "duration": str(max(lo, min(hi, int(duration)))), "resolution": resolution,
            "aspect_ratio": aspect_ratio if aspect_ratio in lim["i2v_ar"] else "auto",
            "generate_audio": bool(generate_audio)}
    if end_image:
        args["end_image_url"] = _fal_url(end_image)
    print(f"\n[FAL SEEDANCE] i2v via {endpoint} ({args['duration']}s, {resolution}"
          + (", end frame" if end_image else "") + ")")
    result = fal_client.subscribe(endpoint, arguments=args, with_logs=True)
    url = _extract_video_url(result)
    if not url:
        raise RuntimeError(f"Seedance i2v returned no video URL: keys={list(result) if isinstance(result, dict) else type(result)}")
    return _download_fal(url, output_path)


def render_reference_video_fal(prompt: str, output_path: str, model: str = "seedance2",
                               image_refs: list = None, video_refs: list = None, audio_refs: list = None,
                               duration: int = 8, resolution: str = "720p", aspect_ratio: str = "auto",
                               generate_audio: bool = True) -> str:
    """Seedance omni reference-to-video. 2.0: up to 9 image / 3 video / 3 AUDIO refs, tokens @Image1 /
    @Video1 / @Audio1. 2.5 (model='seedance2.5'): up to 30 image / 10 video / 10 audio (50 total), 4-30 s,
    720p max, tokens [Image1] / [Video1] / [Audio1]; a reference VIDEO + prompt intent = video EDIT or
    EXTENSION (no mode param). Use seedance_ref_token(model, 'Image', 1) to build the right token. E.g. a
    locked keyframe + a scratch VO take for a lip-synced line - the fal equivalent of Higgsfield's
    seedance_2_0 / seedance_2_5 audio_references."""
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY is not set - cannot call fal.ai.")
    import fal_client
    endpoint = SEEDANCE_REF.get(model)
    if not endpoint:
        raise ValueError(f"Unknown Seedance reference model '{model}'. Known: {list(SEEDANCE_REF)}")
    lim = SEEDANCE_LIMITS[model]
    image_refs, video_refs, audio_refs = list(image_refs or []), list(video_refs or []), list(audio_refs or [])
    if len(image_refs) > lim["img"] or len(video_refs) > lim["vid"] or len(audio_refs) > lim["aud"] \
            or len(image_refs) + len(video_refs) + len(audio_refs) > 50:
        raise ValueError(f"{model} reference-to-video accepts <={lim['img']} images, <={lim['vid']} videos, "
                         f"<={lim['aud']} audios (50 total).")
    if not (image_refs or video_refs or audio_refs):
        raise ValueError("reference-to-video needs at least one reference; use render_scene_video_fal for t2v.")
    if resolution not in lim["res"]:
        print(f"[FAL SEEDANCE] {model} does not offer {resolution}; using 720p (allowed: {lim['res']})")
        resolution = "720p"
    lo, hi = lim["dur"]
    args = {"prompt": prompt, "duration": str(max(lo, min(hi, int(duration)))), "resolution": resolution,
            "aspect_ratio": aspect_ratio if aspect_ratio in _SEEDANCE_AR else "auto",
            "generate_audio": bool(generate_audio)}
    if image_refs:
        args["image_urls"] = [_fal_url(x) for x in image_refs]
    if video_refs:
        args["video_urls"] = [_fal_url(x) for x in video_refs]
    if audio_refs:
        args["audio_urls"] = [_fal_url(x) for x in audio_refs]
    print(f"\n[FAL SEEDANCE] reference-to-video via {endpoint} "
          f"({len(image_refs)} img / {len(video_refs)} vid / {len(audio_refs)} audio refs, {args['duration']}s)")
    result = fal_client.subscribe(endpoint, arguments=args, with_logs=True)
    url = _extract_video_url(result)
    if not url:
        raise RuntimeError(f"Seedance reference-to-video returned no video URL: keys={list(result) if isinstance(result, dict) else type(result)}")
    return _download_fal(url, output_path)
