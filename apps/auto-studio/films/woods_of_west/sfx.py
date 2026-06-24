"""Sound effects for the silent/establishing shots via ElevenLabs text-to-sound-effects.
Style-independent (a train whistle sounds the same in every style), so SFX are
generated once into a shared dir and reused across all three films."""

import os

# Per-shot SFX cue. Only shots WITHOUT spoken dialogue get an SFX bed; dialogue
# shots keep their voiceover. Keyed by shot id.
SFX_CUES = {
    1:  "a distant lonely steam train whistle echoing across an empty desert at dusk",
    2:  "a steam locomotive hissing, brakes screeching, and steam venting as it pulls into a station",
    3:  "heavy cowboy boots stepping down onto a hollow wooden platform, spurs jingling, a puff of dust",
    6:  "dry desert wind gusting, a tumbleweed rolling past, a loose wooden shutter banging",
    7:  "metal spurs jingling with footsteps and an old wall clock ticking",
    14: "a comedic cartoon boing with a shocked vaudeville gasp and a brass sting",
    15: "a comedic spring sproing boing followed by an awkward record-scratch and a rimshot",
    16: "lonely desert wind, sparse western ambience, a final note",
}


def render_shot_sfx(shot_id: int, out_dir: str, duration: float = 5.0):
    """Generate the SFX clip for `shot_id`. Returns the mp3 path, or None when the
    shot has no cue, the key is missing, or generation fails (SFX is optional)."""
    text = SFX_CUES.get(shot_id)
    if not text:
        return None
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print(f"⚠️  no ELEVENLABS_API_KEY — skipping SFX for shot {shot_id}")
        return None
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"sfx{shot_id}.mp3")
    if os.path.exists(out_path):
        return out_path  # reuse — SFX is style-independent and unchanging
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_sound_effects.convert(
            text=text, duration_seconds=min(22.0, max(0.5, duration)),
            output_format="mp3_44100_128",
        )
        with open(out_path, "wb") as f:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
        print(f"🔊 SFX shot {shot_id}: {os.path.basename(out_path)}")
        return out_path
    except Exception as e:
        print(f"⚠️  SFX shot {shot_id} failed ({type(e).__name__}: {e}); continuing without")
        return None


def render_all_sfx(out_dir: str) -> dict:
    """Generate every cued SFX once into `out_dir`. Returns {shot_id: path}."""
    out = {}
    for sid in SFX_CUES:
        p = render_shot_sfx(sid, out_dir)
        if p:
            out[sid] = p
    return out
