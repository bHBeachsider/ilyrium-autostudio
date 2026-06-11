#!/usr/bin/env python3
"""
voice_ingest.py — ingest remotely-recorded voice samples into the Ilyrium
voice library, with optional ElevenLabs instant-voice-clone creation.

Contributors record with the bundled recorder (docs/voice/recorder.html) or any
phone/DAW, following docs/voice/VOICE_RECORDING_GUIDE.md, and send you the
files. Drop them in a folder and run this.

WHAT IT DOES
  1. validates inputs (formats: wav/flac/mp3/m4a/webm/ogg; warns on <6s, <16kHz)
  2. normalizes via ffmpeg -> 48kHz mono WAV, loudness-normalized (EBU R128,
     -19 LUFS mono) into the voice library
  3. registers the voice in voices/voice_library.json (speaker, takes, hashes,
     consent flag)
  4. optional --elevenlabs: creates/updates an ElevenLabs voice from the best
     takes (reads ELEVENLABS_API_KEY from env or repo .env) and stores the
     returned voice_id in the library entry

LIBRARY LAYOUT (client-level, shared across that client's projects)
  projects/<client>/voices/<speaker>/raw/        original uploads (untouched)
  projects/<client>/voices/<speaker>/norm/       normalized 48k mono takes
  projects/<client>/voices/voice_library.json    registry

USAGE
  python ilyrium-shots/voice_ingest.py --speaker brendan \
      --in ~/Downloads/brendan_takes --client projects/broderick
  python ilyrium-shots/voice_ingest.py --speaker brendan \
      --in ./takes --client projects/broderick --elevenlabs --consent

Requires ffmpeg on PATH. Stdlib only otherwise (ElevenLabs via urllib).
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

AUDIO_EXTS = (".wav", ".flac", ".mp3", ".m4a", ".webm", ".ogg", ".aac")
ELEVEN_API = "https://api.elevenlabs.io/v1"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ffprobe(path):
    r = sh(["ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", path])
    if r.returncode != 0:
        return None
    info = json.loads(r.stdout)
    stream = next((s for s in info.get("streams", [])
                   if s.get("codec_type") == "audio"), None)
    if not stream:
        return None
    return {"duration": float(info["format"].get("duration", 0)),
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0))}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_KEY_NAMES = ("ELEVEN_LABS_API_2", "ELEVENLABS_API_KEY")  # first match wins


def env_key():
    for name in _KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name]
    here = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(os.path.dirname(here), ".env")
    if os.path.isfile(env_path):
        found = {}
        for line in open(env_path, encoding="utf-8"):
            m = re.match(r"\s*(ELEVEN_LABS_API_2|ELEVENLABS_API_KEY)\s*=\s*(.+?)\s*$", line)
            if m:
                found[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        for name in _KEY_NAMES:
            if found.get(name):
                return found[name]
    return None


def eleven_clone(speaker, files, description=""):
    """Create an ElevenLabs IVC voice from normalized takes (max 25 files)."""
    key = env_key()
    if not key:
        sys.exit("ELEVENLABS_API_KEY not found in env or repo .env")
    boundary = "----ilyrium" + hashlib.md5(speaker.encode()).hexdigest()[:12]
    body = b""

    def field(name, value):
        return (f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{name}"\r\n\r\n{value}\r\n').encode()

    body += field("name", speaker)
    if description:
        body += field("description", description)
    for fp in files[:25]:
        fname = os.path.basename(fp)
        body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="files"; filename="{fname}"\r\n'
                 f"Content-Type: audio/wav\r\n\r\n").encode()
        body += open(fp, "rb").read() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        ELEVEN_API + "/voices/add", data=body, method="POST",
        headers={"xi-api-key": key,
                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["voice_id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", required=True, help="snake_case speaker key")
    ap.add_argument("--in", dest="indir", required=True,
                    help="folder of uploaded recordings")
    ap.add_argument("--client", default=os.path.join("projects", "broderick"))
    ap.add_argument("--elevenlabs", action="store_true",
                    help="create an ElevenLabs voice from the takes")
    ap.add_argument("--consent", action="store_true",
                    help="affirm the speaker consented to cloning (required "
                         "for --elevenlabs)")
    ap.add_argument("--description", default="",
                    help="ElevenLabs voice description")
    a = ap.parse_args()

    if a.elevenlabs and not a.consent:
        sys.exit("--elevenlabs requires --consent: confirm the speaker has "
                 "agreed in writing to voice cloning (keep the release in "
                 "00_admin/rights_releases/).")
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not on PATH")

    indir = os.path.expanduser(a.indir)
    files = [p for p in sorted(glob.glob(os.path.join(indir, "*")))
             if os.path.splitext(p)[1].lower() in AUDIO_EXTS]
    if not files:
        sys.exit(f"no audio files in {indir}")

    vdir = os.path.join(a.client, "voices", a.speaker)
    raw_dir, norm_dir = os.path.join(vdir, "raw"), os.path.join(vdir, "norm")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(norm_dir, exist_ok=True)

    takes, warnings = [], []
    for i, src in enumerate(files, 1):
        meta = ffprobe(src)
        if not meta:
            warnings.append(f"SKIP unreadable: {os.path.basename(src)}")
            continue
        if meta["duration"] < 6:
            warnings.append(f"short (<6s): {os.path.basename(src)} "
                            f"({meta['duration']:.1f}s)")
        if meta["sample_rate"] < 16000:
            warnings.append(f"low sample rate: {os.path.basename(src)} "
                            f"({meta['sample_rate']} Hz)")
        raw_dst = os.path.join(raw_dir, os.path.basename(src))
        if os.path.abspath(src) != os.path.abspath(raw_dst):
            shutil.copy2(src, raw_dst)
        norm_name = f"{a.speaker}_{i:02d}.wav"
        norm_dst = os.path.join(norm_dir, norm_name)
        r = sh(["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", "48000",
                "-af", "loudnorm=I=-19:TP=-1.5:LRA=7", norm_dst])
        if r.returncode != 0:
            warnings.append(f"FFMPEG FAIL: {os.path.basename(src)}")
            continue
        takes.append({"file": norm_name, "source": os.path.basename(src),
                      "duration_s": round(meta["duration"], 1),
                      "sha256": sha256(norm_dst)})

    lib_path = os.path.join(a.client, "voices", "voice_library.json")
    lib = (json.load(open(lib_path, encoding="utf-8"))
           if os.path.isfile(lib_path) else {})
    entry = lib.get(a.speaker, {})
    entry.update({
        "speaker": a.speaker,
        "takes": takes,
        "total_duration_s": round(sum(t["duration_s"] for t in takes), 1),
        "consent_on_file": bool(a.consent or entry.get("consent_on_file")),
        "updated": dt.date.today().isoformat(),
    })
    if a.elevenlabs:
        norm_files = [os.path.join(norm_dir, t["file"]) for t in takes]
        entry["elevenlabs_voice_id"] = eleven_clone(
            a.speaker, norm_files, a.description)
    lib[a.speaker] = entry
    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
    json.dump(lib, open(lib_path, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print(f"[ok] {a.speaker}: {len(takes)} takes, "
          f"{entry['total_duration_s']}s total -> {vdir}")
    if a.elevenlabs:
        print(f"[ok] ElevenLabs voice_id: {entry['elevenlabs_voice_id']}")
    for w in warnings:
        print("[warn]", w)


if __name__ == "__main__":
    main()
