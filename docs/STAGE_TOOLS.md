# Stage tools & platforms

Per stage: **Wired** = already in the Ilyrium stack; **Available** = tools/platforms you could
add to raise quality. The fast-moving categories (video, audio, image models) shift monthly —
treat the named SOTA as "as of now," and lean on the **YAML/registry pattern** so swapping a
model is config, not code.

| Stage | Element focus | Wired in the stack | Available to add / enhance |
|---|---|---|---|
| **1 Bible** | logline→casting_canon, research | Story-Architect stage agent; **collection-harvester** (`gather_references`) for visual research; `casting_canon` contract | LLMs (Claude/GPT) for development; `deep-research` skill + Perplexity for factual grounding; Notion for collaborative bible; the harvester's region-tagging for period accuracy |
| **2 Script** | scene cards (scenes.json) | Screenwriter/Copywriter agent; `scenes.json` schema | Screenwriting LLMs; Fountain / Final Draft / Highland format export; beat-sheet tools (Save-the-Cat templates); story-structure validators |
| **3 Character** | portrait prompt, anchor, LoRA | **Astria** (LoRA train + Flux portrait + refine); `lora_library.json`; `--cref` anchors | **Midjourney v8.1** `--cref`/`--oref` for identity; **FLUX** (dev/pro); **InstantID / PuLID / IP-Adapter FaceID** (ComfyUI) for face lock; **Kohya** for local LoRA; Magnific/Krea upscale |
| **4 Environment** | plates, prop macros | Astria/Flux gen; harvested `environments/` + `wardrobe_refs/` | Midjourney/FLUX for plates; **ControlNet** (depth/segment) for layout; **Magnific** upscale; 3D/volumetric (Luma, World Labs, Marigold depth) for parallax sets |
| **5 Keyframes** | keyframe per scene | `keyframe` model in the render core; `--cref` continuity | **ComfyUI + IP-Adapter + ControlNet** (pose/depth/canny/reference) — the cheapest cross-shot consistency; Krea real-time; Astria `controlnet` |
| **6 Shots** | video master prompt, takes | **Veo 3.1, Kling, Grok-Imagine, Runway, ComfyUI, Unreal Engine, fal, tensorart** (producer fallback chain) | **Sora, Luma Ray, Pika, Hailuo/MiniMax, Seedance, Runway Gen-4** (swap via registry); UE/Blender for fully-controlled camera; Wan/LTX local |
| **7 Voice** | voice casting, lines | **ElevenLabs** (`render_voiceover`, voice_id + settings) | **Cartesia, PlayHT, OpenAI TTS, Hume** alternatives; ElevenLabs voice-clone/dubbing; per-character A/B for register match |
| **8 Music** | score brief, beds, SFX | **Suno / APIFrame** (score brief mentions); R2 storage | **Udio, Stable Audio, ElevenLabs Music+SFX, AudioCraft**; licensed libraries (Artlist/Epidemic) for commercial; stem separation for ducking |
| **9 Edit** | edit notes, cut, exports | **DaVinci Resolve** project folders; OTIO/EDL exports; **FilmCraft** headless (`ILYRIUM_EDIT_ENGINE=filmcraft`: cut-as-code `cut.jsonl` → `.fcproj` → NVENC master + FCP7 XML; moviepy stays default) | Resolve **scripting API** for auto-assembly; Premiere/CapCut; auto-edit (silence/beat cut) tools; OTIO round-trip to any NLE |
| **10 QA** | qa_log, legal gate | **eval / conformance / release-gate** system; QA_CHECKLIST; A59-A61 IRB | CLIP/aesthetic scoring; **face-similarity** check vs the anchor; **C2PA** provenance manifests (`09_delivery/c2pa_manifests`); content-safety + real-figure-likeness classifiers |
| **11 Key art** | keyart prompts, variants | Astria/Flux gen reusing anchors; `keyart_refs/` | **Ideogram / Recraft** (best text-in-image for posters); Midjourney `--ar`; **Magnific** print-res upscale; Canva/Figma for layout + typography |

## Cross-cutting (every stage)
- **The registry/manifest pattern** — `museums.yaml`, `bible_checklist.json`, `stage_checklists.json`, `lora_library.json`, `models.lock.json`: swap a source/model/tool by editing config.
- **The MCP layer** — `ilyrium-studio` + `collection-harvester` MCPs expose capabilities as agent tools.
- **Storage/provenance** — R2 for masters; C2PA at delivery; the `casting_canon` contract enforced at QA.

## Highest-leverage adds (my read)
1. **ComfyUI IP-Adapter/ControlNet** at Stages 3–5 — the single biggest consistency win (face + pose lock) for the least cost.
2. **A face-similarity QA check** at Stage 10 — automates the most important gate (identity drift + real-figure-likeness) instead of eyeballing.
3. **Ideogram/Recraft** at Stage 11 — text-in-image is where general models fail; specialist tools fix posters/titles.
4. **Model-swap via registry** for Stage 6 video — the field moves monthly; make the engine a config value so you ride the SOTA without re-engineering.

---

## SOTA pinned — June 2026
Verified via web pass. The volatile rows above, with current versions. Re-check quarterly.

**Stage 6 · Video** (the fastest-moving)
- **Google Veo 3.1** — strongest all-around; only model doing **48 kHz lip-synced dialogue in one pass**, 4K landscape/portrait, best prompt adherence. *Default pick.*
- **Kling 3.0** — matches Veo on cinematic motion (hair/liquid/fabric); adds **multi-shot storyboard mode with native audio sync across cuts** (useful for our shot-sequence model).
- **Runway Gen-4.5** — pro control: camera moves, motion brush, **reference-driven character consistency** (pairs with our anchor/LoRA approach).
- **Luma Ray3 / Ray3.14** — cinematic mood + environment-heavy shots.
- Leaderboard (blind-vote arena): Alibaba **Happy Horse 1.0** (2074) > Kling v3 (1987) > LTX-2 Fast (1935).
- ⚠️ **Sora is being discontinued** — web/app **Apr 26 2026**, API **Sep 24 2026**. Remove from any roadmap.

**Stages 3–5 · Image** — the market *specialized*, no single winner:
- **Midjourney V8.1** — aesthetics leader (2K native, HD mode, 5× faster than v7); `--cref`/`--oref` for identity.
- **FLUX.2** (Black Forest Labs, 32B family): **Pro** = commercial API + photorealism leader; **dev** = open-weight (HuggingFace, self-host/ComfyUI); **klein** = sub-second on consumer GPUs.
- **GPT Image 2** — prompt-accuracy leader (best when the prompt is complex/literal).
- Practical split: **MJ v8 = look, FLUX.2 Pro = photoreal, GPT Image 2 = prompt accuracy.**

**Stage 7 · Voice** — no longer single-vendor:
- **ElevenLabs** — overall quality + cloning leader; 70+ languages; Flash v2.5 handles 40k chars/request. *(Already wired.)*
- **Cartesia Sonic** — latency leader (<100 ms time-to-first-byte), ~1/5 the cost, on-device/on-prem — for real-time/interactive.
- **OpenAI TTS** — instructable voice character (steer the speaker by prompt).

**Stage 8 · Music**
- **Suno v5.5** (Mar 2026) — best all-rounder for vocal-driven songs; adds **voice cloning, fine-tuning, and Suno Studio (a DAW)**. *(Already referenced.)*
- **Udio v1.5** — audiophile/instrumental choice; 48 kHz stereo + **2-second-segment inpainting** (surgical edits no one else has).

**Stage 11 · Key art / text-in-image**
- **Ideogram 4.0** (Jun 2026) — ~90–95% text-rendering accuracy (vs 30–50% for general models); **structured JSON prompts with bounding-box placement + locked hex palette + per-line styling**, native 2K, transparent bg, **Layerize** editable text. *The poster/title tool.*
- **Recraft V3** — when you need **editable SVG/vector** delivery (logos, scalable wordmarks).

**Sources:** [video](https://www.atlascloud.ai/blog/guides/best-ai-video-generation-models-2026) · [video arena](https://llm-stats.com/leaderboards/best-ai-for-video-generation) · [image](https://wavespeed.ai/blog/posts/midjourney-v8-vs-flux-vs-sora-best-ai-image-generator-2026/) · [music](https://neuronad.com/suno-vs-udio/) · [voice](https://sureprompts.com/blog/voice-generation-models-compared-2026) · [text-in-image](https://www.recraft.ai/ai-models/ideogram)
