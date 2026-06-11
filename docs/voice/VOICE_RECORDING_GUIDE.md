# Voice Recording & Direction Guide (Ilyrium)

How remote contributors record voice samples, how we ingest them, and how the
resulting voices are modified afterward with text — for both ElevenLabs
(primary, commercial-safe) and XTTSv2 (xtts-foundry, experimentation only:
CPML license forbids commercial output).

## 1. Recording — what the contributor does

**Room.** Quiet, small, soft-furnished (closet full of clothes beats a kitchen).
No fans, AC, traffic, or hum. Phone on airplane mode. Clap once — if you hear
ring or echo, pick another room.

**Mic.** Any decent mic beats a laptop's built-in array: a phone held 15–20 cm
away at 45° off-axis, a USB mic, or earbuds-with-boom as a last resort. Keep
distance CONSTANT — don't drift. No headphones playing back.

**Settings.** Disable noise suppression / echo cancellation if the app allows
(the bundled `recorder.html` does this automatically). Target peaks around
−12 dB to −6 dB — loud but never clipping. The recorder's level bar: green good,
amber loud, red back off.

**What to record** (the recorder page shows this script):
1. NEUTRAL, 45–60s — natural storytelling, continuous speech
2. EXPRESSIVE, 30–45s — real emotional reaction, laughs and pauses included
3. DEADPAN READ, 30s — provided text, flat delivery (this is the broderick register)
4. RANGE, 20s — whisper → normal → projected

Stumbles are fine — keep rolling, don't restart. 2–5 minutes total of clean
speech is the target. More than 10 minutes adds little for cloning.

**Delivery.** Download the takes from the recorder page and send via any file
transfer (Drive/Dropbox/WeTransfer/email). Original files only — no editing,
no normalization, no MP3 re-export if avoidable.

**Consent.** The speaker must agree in writing to voice cloning and its
intended use. Store the release in the project's
`00_admin/rights_releases/`. Ingestion to ElevenLabs requires `--consent`.

## 2. Ingestion — what we do

```
python ilyrium-shots/voice_ingest.py --speaker brendan \
    --in <folder-of-uploads> --client projects/broderick \
    --elevenlabs --consent --description "deadpan narrator, broderick house voice"
```

Validates and archives the originals, normalizes to 48 kHz mono WAV at
−19 LUFS, registers takes in `projects/<client>/voices/voice_library.json`,
and (with `--elevenlabs`) creates an Instant Voice Clone and stores the
returned `voice_id`. Requires ffmpeg; API key read from repo `.env`
(`ELEVENLABS_API_KEY`).

For XTTSv2 experiments: any single normalized take ≥6s from `voices/<speaker>/norm/`
works as the `speaker_wav` reference. Best results 10–30s, expressive take.

## 3. Modifying voices via text — the part most people miss

### ElevenLabs (three distinct levers)

**a. Delivery — written into the script itself.** The model acts what it reads:
- Punctuation is direction: ellipses … slow and trail; dashes — create beats;
  CAPS add emphasis; exclamation points lift energy.
- With the v3 model, inline audio tags direct performance:
  `[whispers]`, `[laughs]`, `[sighs]`, `[sarcastic]`, `[angry]`, `[pause]`.
  Example: `[deadpan] The dome was on fire. [pause] Nobody panicked … [sighs] which was the real problem.`
- Narrative context steers tone even without tags — "he said, utterly bored,"
  influences the read of adjacent dialogue.

**b. Voice settings — per-generation knobs (API or dashboard):**
- `stability` low = expressive/variable, high = consistent/flat. Broderick
  deadpan: start ~0.65–0.75.
- `similarity_boost` how hard it clings to the clone; ~0.75 default.
- `style` exaggeration of the source style; keep low (0–0.2) for deadpan.
- `speed` 0.7–1.2.

**c. Voice design — describe a NEW voice in text only** (no recording needed):
the Text-to-Voice endpoint takes a prose description ("flat, dry, middle-aged
American male narrator, slightly nasal, complete emotional detachment") and
generates candidate voices. Useful for one-off characters with no human source.

### XTTSv2 (xtts-foundry)

XTTS has NO textual control of timbre or style — the reference WAV is the only
style input. To "modify" a voice: swap or re-cut the reference audio (use the
expressive take for lively reads, the deadpan take for flat reads). Punctuation
still shapes pacing modestly. Treat XTTS as a free experimentation bench;
production audio goes through ElevenLabs until a commercially-licensed local
model replaces it.

## 4. Where output lands

Generated line reads go to the strip project:
`projects/<client>/<strip>/06_audio/voice/<scene>__<character>__vNN.wav`
named to match scene cards so the edit can auto-place them.
