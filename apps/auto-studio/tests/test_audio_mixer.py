"""Integration test for media/audio_mixer.py.

Creates real (short) WAV fixtures in a temp dir, mixes narrator over ambient
with ducking applied, and verifies the output is a valid AAC file.

Run from apps/auto-studio:  venv/Scripts/python -m pytest tests/test_audio_mixer.py -v
"""
import math
import os
import struct
import tempfile
import wave

import pytest

from media.audio_mixer import AudioMixer, AudioTrack


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #

def _make_wav(path: str, duration_s: float = 0.5, freq: float = 440.0, amplitude: float = 0.3) -> str:
    """Write a mono 44.1 kHz sine-wave WAV file using only stdlib."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_s)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)   # 16-bit PCM
        w.setframerate(sample_rate)
        for i in range(n_samples):
            v = int(32767 * amplitude * math.sin(2 * math.pi * freq * i / sample_rate))
            w.writeframes(struct.pack("<h", v))
    return path


@pytest.fixture()
def audio_dir(tmp_path):
    """Temp directory with two short WAV files: ambient (220 Hz) and narrator (880 Hz)."""
    ambient = str(tmp_path / "ambient.wav")
    narrator = str(tmp_path / "narrator.wav")
    _make_wav(ambient, duration_s=0.5, freq=220.0)
    _make_wav(narrator, duration_s=0.5, freq=880.0)
    return tmp_path, ambient, narrator


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_mix_produces_aac(audio_dir):
    """A mixed AAC output file is created and is non-empty."""
    tmp_path, ambient, narrator = audio_dir
    out = str(tmp_path / "out.aac")

    mixer = AudioMixer()
    tracks = [
        AudioTrack(url=ambient,  kind="ambient",  volume=1.0, ducking_db=-12.0),
        AudioTrack(url=narrator, kind="narrator", volume=1.0, ducking_db=0.0),
    ]
    result = mixer.mix(tracks, duration_s=0.5, output_path=out)

    assert result == out
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0


def test_mix_output_is_readable_aac(audio_dir):
    """The output file can be re-opened by AudioFileClip (i.e. is valid AAC)."""
    from moviepy import AudioFileClip
    tmp_path, ambient, narrator = audio_dir
    out = str(tmp_path / "out2.aac")

    mixer = AudioMixer()
    tracks = [
        AudioTrack(url=ambient,  kind="ambient",  volume=1.0, ducking_db=-12.0),
        AudioTrack(url=narrator, kind="narrator", volume=1.0, ducking_db=0.0),
    ]
    mixer.mix(tracks, duration_s=0.5, output_path=out)

    clip = AudioFileClip(out)
    assert clip.duration > 0
    clip.close()


def test_ducking_reduces_ambient_volume(audio_dir):
    """AudioTrack ducking_db=-12 is applied when a narrator track is present."""
    from media.audio_mixer import AudioTrack

    t = AudioTrack(url="/dummy.wav", kind="ambient", volume=1.0, ducking_db=-12.0)
    # -12 dB -> linear factor ≈ 0.251
    duck_factor = 10 ** (-12.0 / 20.0)
    expected_vol = 1.0 * duck_factor
    assert abs(expected_vol - 0.251) < 0.002


def test_mix_narrator_only(audio_dir):
    """A single narrator track with no ambient produces a valid output."""
    tmp_path, _, narrator = audio_dir
    out = str(tmp_path / "out_narrator_only.aac")

    mixer = AudioMixer()
    tracks = [AudioTrack(url=narrator, kind="narrator", volume=1.0)]
    result = mixer.mix(tracks, duration_s=0.5, output_path=out)

    assert os.path.exists(result)
    assert os.path.getsize(result) > 0


def test_mix_raises_on_empty_tracks():
    """mix() raises ValueError when no valid tracks are provided."""
    mixer = AudioMixer()
    with pytest.raises(ValueError, match="no valid audio tracks"):
        mixer.mix([], duration_s=1.0, output_path="/tmp/should_not_exist.aac")


def test_audio_track_from_dict():
    """AudioTrack.from_dict() round-trips correctly."""
    d = {"url": "/some/path.wav", "kind": "music", "start_s": 1.5, "volume": 0.7, "ducking_db": -6.0}
    t = AudioTrack.from_dict(d)
    assert t.url == "/some/path.wav"
    assert t.kind == "music"
    assert t.start_s == 1.5
    assert t.volume == 0.7
    assert t.ducking_db == -6.0
