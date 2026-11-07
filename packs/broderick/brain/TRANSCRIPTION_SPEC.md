# Broderick Panel-Transcription Pass — Spec

## Why (the problem this solves)
The manifest `caption` is a **visual** description; it omits the in-panel **text** (caption boxes,
dialogue/shouted lettering, signage, SFX). Broderick's comedy is largely *verbal* — the escalating
pompous monologue *is* the joke — so operator extraction from captions alone is structurally blind.
Validated on `broderick_autobiography_707b`: the captions render a vivid KKK-hood shop-teacher
memoir but contain **zero** of the caption-box/shouted text that carries the bit.

**Goal:** recover the in-panel text per panel and write it as a sidecar that
`extract_operators.py` already consumes (`<dataset>/transcripts/<panel-base>.txt`).

## Method — vision-LLM, NOT classic OCR
Tesseract/PaddleOCR fail badly on stylized hand-lettering. Use a **multimodal model** that reads
hand-lettering, respects reading order, and separates balloons from captions from signage.

- **Primary:** an **open-weight** vision model — **Qwen2.5-VL** (via OpenRouter `qwen/qwen-2.5-vl-7b`
  or run on the GPU box). Open-weight keeps the *training-data pipeline* ToS-clean, since these
  transcripts feed the DeepSeek teacher.
- **Note on ToS:** pure transcription is *factual extraction of Broderick's own words*, not
  distillation of a model's creative capability — so a frontier vision model is defensible as a
  fallback for a few unreadable panels. But default to open-weight for consistency + cost.

## Output format — `transcripts/<base>.txt` (structured text the runner reads verbatim)
```
CAPTION: <narration / caption-box text, in order>
<SPEAKER>: <dialogue from a balloon>           # SPEAKER = a short label (TEACHER, KID, NARRATOR)
SIGN: <signage / labels in the art>            # e.g. road signs, t-shirt text, bumper stickers
SFX: <sound effects>
[illegible: <what + why>]                       # never guess; flag instead
```
One file per panel; the runner appends it after `IN-PANEL TEXT (transcribed):`. (Plain structured
text keeps it human-editable for the Broderick review pass.)

## The vision prompt
```
Transcribe ALL text visible in this single comic panel EXACTLY as written — do not paraphrase,
correct, or translate. Read in natural order (top-to-bottom, left-to-right; follow balloon tails).

Label each piece by type:
  CAPTION:  narration / caption-box text
  <SPEAKER>: dialogue inside a speech balloon (use a short speaker label if identifiable, else SPEAKER)
  SIGN:     text that appears in the artwork (signs, shirts, labels, stickers)
  SFX:      sound effects / onomatopoeia

If any text is unreadable, write "[illegible: <what + why>]" — NEVER invent or complete words.
If the panel has no text, output exactly: (no text)
End with a line: CONFIDENCE: <0.0-1.0> — your confidence in the transcription.
Output only the labeled lines.
```

## Runner (sketch — `transcribe_panels.py`)
```
for each non-excluded panel in manifest:
    skip if transcripts/<base>.txt exists                 # resumable
    img = base64(images/<file_name>)
    raw = qwen_vl(VISION_PROMPT, img)                      # OpenRouter multimodal call
    split off the trailing CONFIDENCE: line
    write transcripts/<base>.txt (labeled lines)
    record {base, confidence} to transcripts/_index.jsonl
```
`--review` lists panels by ascending confidence (the human spot-check queue).

## Human spot-check (cheap, high-value)
Sort by `CONFIDENCE` ascending; have Broderick/an assistant eyeball the lowest ~20-30 and any
`[illegible]`. Hand-lettering + his idiolect mean the model will miss; 30 min of correction
materially lifts the whole downstream dataset. Corrected `.txt` files are just edited in place.

## Sequence + cost
1. `transcribe_panels.py` over the 190 panels — OpenRouter Qwen2.5-VL, ~a few cents total, ~minutes,
   **no GPU box needed**.
2. Spot-check the low-confidence tail.
3. Re-run `extract_operators.py` — it now reads `transcripts/`, confidence rises, the *verbal*
   operator is captured.

## Risks / honest limits
- Reading order in dense multi-balloon panels can scramble — the spot-check catches it.
- Speaker attribution is best-effort; if unclear the model uses `SPEAKER:` and the operator
  extraction still benefits from the raw lines.
- Some lettering is genuinely illegible at the dataset's resolution; flagged, not guessed.
