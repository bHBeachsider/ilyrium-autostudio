#!/usr/bin/env python3
"""
voice_gen.py — ElevenLabs synthesis driver for the Ilyrium pipeline.

The production voice path (XTTS in ~/xtts-foundry on the GPU box is the
non-commercial experimentation bench; this is the commercial one). API key read
from ELEVENLABS_API_KEY in env or repo .env. Stdlib only.

SUBCOMMANDS
  voices                          list available voices (id, name, category)
  quota                           show subscription character quota
  say    --voice X --text "..."   one-off line -> audio file
  scene  --project <dir> [--scenes N,M] [--cast cast.json]
                                  batch-generate every dialogue line (and
                                  voiceover) from the project's
                                  02_script/scenes.json into
                                  06_audio/voice/sNN__<speaker>__vNN.mp3

VOICE RESOLUTION (--voice / cast values)
  1. a raw ElevenLabs voice_id
  2. a speaker key in <client>/voices/voice_library.json (uses its
     elevenlabs_voice_id) — client inferred as project parent for scene mode,
     or passed via --client
  3. a premade voice name (resolved via the live voices list)

CAST FILE (scene mode)  <project>/06_audio/voice/voice_cast.json
  {"character_key": "<voice_id | speaker_key | premade name>", ...}
  Characters without a cast entry are skipped (reported).

DELIVERY DIRECTION
  Write performance into the text: punctuation is pacing; with --model
  eleven_v3, inline audio tags ([deadpan], [sighs], [pause], [whispers]) are
  honored. Scene mode prepends each line's scene-card `delivery` note as a v3
  tag when --tag-delivery is set.

SETTINGS
  --model     eleven_multilingual_v2 (default) | eleven_v3 | eleven_turbo_v2_5
  --stability 0..1 (default 0.7 — broderick deadpan), --similarity 0..1 (0.75),
  --style 0..1 (0.0), --speed 0.7..1.2 (1.0)
  --format    mp3_44100_128 (default) | mp3_44100_192 | pcm_24000 (-> .wav)

EXAMPLES
  python ilyrium-shots/voice_gen.py voices
  python ilyrium-shots/voice_gen.py say --voice brendan --text "[deadpan] The dome was on fire." --out test.mp3
  python ilyrium-shots/voice_gen.py scene --project projects/broderick/broderick_torg --tag-delivery
"""
import argparse
import json
import os
import re
import struct
import sys
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1"


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
    sys.exit("no ElevenLabs key (ELEVEN_LABS_API_2 / ELEVENLABS_API_KEY) "
             "in env or repo .env")


def api(path, payload=None, key=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method="POST" if data else "GET",
        headers={"xi-api-key": key or env_key(),
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if "missing_permissions" in detail:
            sys.exit(f"API key lacks a permission for {path}: {detail}\n"
                     "Regenerate the key at elevenlabs.io with scopes: "
                     "text_to_speech, voices_read, voices_write, models_read, "
                     "user_read — or use an unrestricted key.")
        sys.exit(f"ElevenLabs HTTP {e.code} on {path}: {detail}")
    return body


def list_voices(key):
    return json.loads(api("/voices", key=key))["voices"]


def resolve_voice(ident, key, client=None):
    if re.fullmatch(r"[A-Za-z0-9]{15,}", ident or ""):
        return ident                                    # looks like a voice_id
    if client:
        lib_path = os.path.join(client, "voices", "voice_library.json")
        if os.path.isfile(lib_path):
            lib = json.load(open(lib_path, encoding="utf-8"))
            entry = lib.get(ident)
            if entry and entry.get("elevenlabs_voice_id"):
                return entry["elevenlabs_voice_id"]
    for v in list_voices(key):
        if v["name"].lower() == ident.lower():
            return v["voice_id"]
    sys.exit(f"cannot resolve voice {ident!r} (not an id, library speaker, "
             f"or premade name)")


def pcm_to_wav(pcm, rate):
    hdr = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE",
                      b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16,
                      b"data", len(pcm))
    return hdr + pcm


def tts(text, voice_id, a, key):
    payload = {
        "text": text, "model_id": a.model,
        "voice_settings": {"stability": a.stability,
                           "similarity_boost": a.similarity,
                           "style": a.style, "speed": a.speed},
    }
    body = api(f"/text-to-speech/{voice_id}?output_format={a.format}",
               payload, key)
    if a.format.startswith("pcm_"):
        return pcm_to_wav(body, int(a.format.split("_")[1])), ".wav"
    return body, ".mp3"


def next_version(folder, stem):
    n = 1
    while any(os.path.exists(os.path.join(folder, f"{stem}__v{n:02d}{e}"))
              for e in (".mp3", ".wav")):
        n += 1
    return n


def cmd_scene(a, key):
    proj = a.project.rstrip("/\\")
    client = a.client or os.path.dirname(proj)
    scenes = json.load(open(os.path.join(proj, "02_script", "scenes.json"),
                            encoding="utf-8"))
    cast_path = a.cast or os.path.join(proj, "06_audio", "voice",
                                       "voice_cast.json")
    if not os.path.isfile(cast_path):
        sys.exit(f"cast file not found: {cast_path}\nCreate it as "
                 '{"character_key": "<voice_id|speaker|premade name>", ...} '
                 '(use "narrator" for voiceover lines)')
    cast = json.load(open(cast_path, encoding="utf-8"))
    resolved = {k: resolve_voice(v, key, client) for k, v in cast.items()}
    out_dir = os.path.join(proj, "06_audio", "voice")
    os.makedirs(out_dir, exist_ok=True)
    only = ({int(x) for x in a.scenes.split(",")} if a.scenes else None)

    made = skipped = 0
    for card in scenes:
        sn = card["scene_number"]
        if only and sn not in only:
            continue
        jobs = [(d.get("speaker", "unknown"), d.get("line", ""),
                 d.get("delivery", "")) for d in card.get("dialogue", [])]
        if card.get("voiceover"):
            jobs.append(("narrator", card["voiceover"], ""))
        for speaker, line, delivery in jobs:
            if not line.strip():
                continue
            if speaker not in resolved:
                print(f"[skip] s{sn:02d} {speaker}: no cast entry")
                skipped += 1
                continue
            text = line
            if a.tag_delivery and delivery and a.model == "eleven_v3":
                tag = re.sub(r"[^a-z ]", "", delivery.lower()).split(",")[0].strip()
                if tag:
                    text = f"[{tag}] {line}"
            stem = f"s{sn:02d}__{speaker}"
            ver = next_version(out_dir, stem)
            audio, ext = tts(text, resolved[speaker], a, key)
            path = os.path.join(out_dir, f"{stem}__v{ver:02d}{ext}")
            open(path, "wb").write(audio)
            print(f"[ok] {os.path.relpath(path, proj)}  ({len(audio)//1024} KB)")
            made += 1
    print(f"done: {made} files, {skipped} skipped -> {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("voices", "quota", "say", "scene"):
        p = sub.add_parser(name)
        if name in ("say", "scene"):
            p.add_argument("--model", default="eleven_multilingual_v2")
            p.add_argument("--stability", type=float, default=0.7)
            p.add_argument("--similarity", type=float, default=0.75)
            p.add_argument("--style", type=float, default=0.0)
            p.add_argument("--speed", type=float, default=1.0)
            p.add_argument("--format", default="mp3_44100_128")
            p.add_argument("--client", help="client dir for voice_library lookups")
        if name == "say":
            p.add_argument("--voice", required=True)
            p.add_argument("--text", required=True)
            p.add_argument("--out", default="say_out")
        if name == "scene":
            p.add_argument("--project", required=True)
            p.add_argument("--scenes", help="comma-separated scene numbers")
            p.add_argument("--cast", help="path to voice_cast.json override")
            p.add_argument("--tag-delivery", action="store_true",
                           help="prepend scene-card delivery note as v3 tag")
    a = ap.parse_args()
    key = env_key()

    if a.cmd == "voices":
        for v in list_voices(key):
            print(f"{v['voice_id']}  {v['name']}  [{v.get('category','')}]")
    elif a.cmd == "quota":
        s = json.loads(api("/user/subscription", key=key))
        print(f"tier={s.get('tier')} used={s.get('character_count')}/"
              f"{s.get('character_limit')} chars; "
              f"voice slots used={s.get('voice_slots_used', '?')}")
    elif a.cmd == "say":
        vid = resolve_voice(a.voice, key, a.client)
        audio, ext = tts(a.text, vid, a, key)
        out = a.out if os.path.splitext(a.out)[1] else a.out + ext
        open(out, "wb").write(audio)
        print(f"[ok] {out} ({len(audio)//1024} KB)")
    elif a.cmd == "scene":
        cmd_scene(a, key)


if __name__ == "__main__":
    main()
