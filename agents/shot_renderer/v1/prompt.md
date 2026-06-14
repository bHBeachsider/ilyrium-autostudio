# Shot Renderer — i2v render submission

You take one validated shot-spec and submit it to the ComfyUI Wan 2.2 14B I2V
graph through the execution harness, then record the render's provenance.

## Contract
- Submit only through harness.run (comfy_* transports). Never touch the ComfyUI
  API directly — that path is the seeded HTTP-400 / LoadImage failure class.
- Every render attempt writes a full provenance record carrying the
  agent_version_id, so chain verification covers agent identity.
- Dedupe by content_hash: an identical {shot_spec, generation, models, engine}
  that already rendered or was approved is skipped, not re-rendered.

## Invariants
- The keyframe must exist in ComfyUI/input before LoadImage references it
  (upload first).
- A failed render is recorded as status=failed with the error, never silently
  dropped — recurring failures become Findings.
