"""ElevenLabs voice casting for the three characters. voice_ids are starting picks
from the ElevenLabs prebuilt library — audition and swap before the full render."""

from media.audio_generator import render_voiceover

VOICE_CAST = {
    # Shakes: gravelly, frantic old-timer  (prebuilt "Clyde")
    "shakes": {"voice_id": "2EiwWnXFnvU5JabPnv8n", "stability": 0.45, "similarity": 0.85},
    # Pringle: dry, slow deadpan drawl, older  (prebuilt "Bill")
    "pringle": {"voice_id": "pqHfZKP75CvOlQylNhV4", "stability": 0.80, "similarity": 0.85},
    # Cal: low, menacing, smug  (prebuilt "Adam")
    "cal": {"voice_id": "pNInz6obpgDQGcFmaJgB", "stability": 0.70, "similarity": 0.85},
}


def render_shot_dialogue(shot: dict, out_dir: str):
    """Synthesize the shot's line with its cast voice. Returns the mp3 path, or
    None for silent shots."""
    if not shot.get("line"):
        return None
    cast = VOICE_CAST[shot["speaker"]]
    return render_voiceover(
        text=shot["line"],
        scene_number=shot["id"],
        output_dir=out_dir,
        output_name=f"shot{shot['id']}.mp3",
        voice_id=cast["voice_id"],
        stability=cast["stability"],
        similarity=cast["similarity"],
    )
