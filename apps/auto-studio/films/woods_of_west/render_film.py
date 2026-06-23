"""Driver for 'The Woods of the West'.

Phase 1 (bakeoff): render the signature beat in all 3 styles → pick a winner.
Phase 2 (final):   render the full film in the chosen style.

Run from apps/auto-studio:
  venv/Scripts/python -m films.woods_of_west.render_film --phase bakeoff
  venv/Scripts/python -m films.woods_of_west.render_film --phase final --style cartoon --music score.mp3
"""

import os
import sys
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_AUTOSTUDIO = os.path.dirname(os.path.dirname(_HERE))
if _AUTOSTUDIO not in sys.path:
    sys.path.insert(0, _AUTOSTUDIO)

try:
    from dotenv import load_dotenv
    # Keys (FAL_KEY, ELEVENLABS_API_KEY) live in the repo-root .env; load it first,
    # then let an auto-studio/.env override if present.
    _REPO_ROOT = os.path.dirname(os.path.dirname(_AUTOSTUDIO))
    load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=True)
    load_dotenv(os.path.join(_AUTOSTUDIO, ".env"), override=True)
except Exception:
    pass

from films.woods_of_west import script, keyframes, characters, voices
from media.comfyui_renderer import render_i2v_comfyui
from media.post_production import compile_final_video


def build_media_list(shots, keyframe_dir, clip_dir, audio_dir, render_clip, render_audio):
    """Pure orchestration: pair each shot's clip + audio into a compile manifest.
    Shots whose clip render returns None are skipped."""
    media = []
    for sh in shots:
        video = render_clip(sh)
        if not video:
            print(f"⚠️  shot {sh['id']}: no clip, skipping")
            continue
        audio = render_audio(sh)
        media.append({"scene_number": sh["id"], "video": video, "audio": audio})
    return media


def render_shot_audio(shot, audio_dir):
    """ElevenLabs dialogue for one shot. Returns the mp3 path, None for silent
    shots, and None (with a warning) on TTS failure — audio is optional and must
    NEVER abort an expensive video render."""
    try:
        return voices.render_shot_dialogue(shot, audio_dir)
    except Exception as e:
        print(f"⚠️  shot {shot['id']} dialogue failed ({type(e).__name__}: {e}); continuing silent")
        return None


def render_shot_clip(shot, style, char_refs, keyframe_dir, clip_dir):
    """Keyframe (Fal) + Wan i2v (ComfyUI) for one shot. Returns the clip path, or
    None if EITHER step fails — a single flaky shot is skipped, never fatal to the
    whole (long, expensive) render run."""
    try:
        kf = keyframes.generate_shot_keyframe(shot, style, char_refs, keyframe_dir)
        timeout = int(os.getenv("COMFYUI_I2V_TIMEOUT", "1500"))
        return render_i2v_comfyui(kf, shot["motion"], shot["id"], output_dir=clip_dir,
                                  output_name=f"shot{shot['id']}.mp4", timeout=timeout)
    except Exception as e:
        print(f"❌ shot {shot['id']} clip failed: {e}")
        return None


def _render_one_style(shots, style, out_root, music_path=None):
    style_root = os.path.join(out_root, style)
    kf_dir = os.path.join(style_root, "keyframes")
    clip_dir = os.path.join(style_root, "clips")
    aud_dir = os.path.join(style_root, "audio")
    char_dir = os.path.join(style_root, "characters")
    for d in (kf_dir, clip_dir, aud_dir, char_dir):
        os.makedirs(d, exist_ok=True)

    print(f"\n=== building character sheets ({style}) ===")
    char_refs = characters.build_character_sheets(style, char_dir)

    def render_clip(sh):
        return render_shot_clip(sh, style, char_refs, kf_dir, clip_dir)

    def render_audio(sh):
        return render_shot_audio(sh, aud_dir)

    media = build_media_list(shots, kf_dir, clip_dir, aud_dir, render_clip, render_audio)
    master = os.path.join(style_root, f"woods_of_west_{style}.mp4")
    return compile_final_video(media, output_filename=master, music_path=music_path)


def run_bakeoff(out_root):
    shots = script.shots_for_phase("bakeoff")
    results = {}
    for style in script.STYLES:
        print(f"\n########## BAKE-OFF STYLE: {style} ##########")
        results[style] = _render_one_style(shots, style, os.path.join(out_root, "bakeoff"))
    return results


def run_film(style, out_root, music_path=None):
    shots = script.shots_for_phase("film")
    return _render_one_style(shots, style, os.path.join(out_root, "final"), music_path=music_path)


def main():
    ap = argparse.ArgumentParser(description="Render 'The Woods of the West'.")
    ap.add_argument("--phase", choices=["bakeoff", "final"], required=True)
    ap.add_argument("--style", choices=list(script.STYLES), help="required for --phase final")
    ap.add_argument("--music", help="path to western score mp3 (optional)")
    ap.add_argument("--out", default=os.path.join(_AUTOSTUDIO, "outputs", "woods_of_west"))
    args = ap.parse_args()
    if args.phase == "bakeoff":
        print(run_bakeoff(args.out))
    else:
        if not args.style:
            ap.error("--style is required for --phase final")
        print(run_film(args.style, args.out, music_path=args.music))


if __name__ == "__main__":
    main()
