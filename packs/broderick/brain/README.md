# Broderick Brain — operator extraction (v0 dataset derivation)

Goal: turn the existing 190-panel corpus into a `{premise → comic}` training set in Broderick's
voice, *without* requiring Broderick to articulate his own "why." We do it in two moves:

1. **Reverse-engineer the OPERATOR** from each finished strip (this directory).
2. **Invert** the operators to `premise → comic` training pairs (next step), then QLoRA-train a
   `broderick-brain` text SLM (reuse the foundry `src/{prepare,train,evaluate,export_gguf}.py`).

## Files
- `operator_schema.json` — the structured grammar we extract per strip (target / mechanism /
  escalation / register / puncture + sequential beats + visual motifs + confidence).
- `teacher_prompt.md` — the open-weight (DeepSeek) teacher prompt that fills the schema.
- `data/broderick_operators.jsonl` — output (one operator object per strip).

## Flow
```
manifest.jsonl  --group by `strip`, order by `scene_numbers`-->  per-strip panel text
   --DeepSeek (teacher_prompt) -->  operator JSON  --validate(operator_schema)-->  operators.jsonl
   --Broderick reviews low-confidence rows-->  corrected operators  --invert-->  premise→comic pairs
```

## ⚠️ The data caveat that governs quality — verbal content
Broderick's comedy is **largely verbal** (the pompous monologue, the escalating pseudo-intellectual
analysis). The manifest `caption` is a **visual** description (style, staging, composition) and
generally does **not** transcribe the in-panel dialogue/text. Extracting the operator from staging
alone yields a competent *structural* read but misses the actual jokes.

**Therefore the highest-leverage prep step is a transcription pass**: get the real in-panel text per
panel (OCR the source images, or pull from Broderick's digital originals if they exist) and feed it
to the teacher alongside the caption. Order of impact on dataset quality:
1. In-panel **text transcription** (biggest lift — recovers the verbal operator).
2. **Broderick's review** of low-confidence rows (recovers intent/soul).
3. The visual captions (what we have today — structural floor).

Without (1), set `confidence` low and lean on (2). With (1)+(2), this becomes a strong v0.
