"""Multi-track audio mixer for the Ilyrium assembly pipeline.

AudioMixer takes a list of AudioTrack objects and renders a mixed mono/stereo
AAC file via moviepy's CompositeAudioClip. Ducking is applied when a narrator
or character track is active: ambient/music volume is scaled by the track's
ducking_db value (negative = reduce, e.g. -12 dB = 0.25x linear).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from moviepy import AudioFileClip, CompositeAudioClip
from moviepy.audio.fx.AudioLoop import AudioLoop


@dataclass
class AudioTrack:
    url: str                    # local path or R2 URL
    kind: str                   # "ambient" | "narrator" | "character" | "music" | "sfx"
    start_s: float = 0.0
    volume: float = 1.0
    ducking_db: float = 0.0     # negative = duck by this many dB when narrator/character active

    @classmethod
    def from_dict(cls, d: dict) -> "AudioTrack":
        return cls(
            url=d["url"],
            kind=d.get("kind", "ambient"),
            start_s=float(d.get("start_s", 0.0)),
            volume=float(d.get("volume", 1.0)),
            ducking_db=float(d.get("ducking_db", 0.0)),
        )


class AudioMixer:
    """Mix a list of AudioTrack objects into a single AAC output file."""

    def mix(self, tracks: List[AudioTrack], duration_s: float, output_path: str) -> str:
        """Render tracks to output_path (48 kHz stereo AAC).

        Returns output_path on success; raises on failure.
        """
        PRIMARY_KINDS = {"narrator", "character"}
        DUCKABLE_KINDS = {"ambient", "music"}

        has_primary = any(t.kind in PRIMARY_KINDS for t in tracks)

        clips = []
        for track in tracks:
            if not track.url or not os.path.exists(track.url):
                print(f"[AudioMixer] skipping missing track: {track.url!r}")
                continue

            try:
                clip = AudioFileClip(track.url)
            except Exception as e:
                print(f"[AudioMixer] could not load {track.url!r}: {e}")
                continue

            # Loop short clips or trim long ones to fit duration
            if duration_s > 0:
                if clip.duration < duration_s:
                    try:
                        clip = clip.with_effects([AudioLoop(duration=duration_s)])
                    except Exception:
                        clip = clip.with_duration(clip.duration)  # leave short
                else:
                    clip = clip.with_duration(duration_s)

            # Start offset
            if track.start_s > 0:
                clip = clip.with_start(track.start_s)

            # Volume: apply ducking for ambient/music when a primary track is present
            vol = max(0.0, track.volume)
            if has_primary and track.kind in DUCKABLE_KINDS and track.ducking_db != 0.0:
                duck_factor = 10.0 ** (track.ducking_db / 20.0)
                vol = vol * duck_factor

            clip = clip.with_volume_scaled(vol)
            clips.append(clip)

        if not clips:
            raise ValueError("AudioMixer.mix: no valid audio tracks to mix")

        mixed = CompositeAudioClip(clips) if len(clips) > 1 else clips[0]
        if duration_s > 0:
            mixed = mixed.with_duration(duration_s)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        mixed.write_audiofile(
            output_path,
            fps=48000,
            nbytes=2,
            codec="aac",
            logger=None,
        )
        return output_path
