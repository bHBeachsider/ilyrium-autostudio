# Character LoRAs — authoring home

A character LoRA encodes a character's look (from the bible) as a `.safetensors` the render engine
loads. It is authored here and *registered* in `lora_library.json`, which the ilyrium-shots
keyframe path (`keyframe_to_comfy.py`) reads via each shot spec's `keyframe.ref_lora`.

Per character (folder name = the casting-canon key):
- `<character>/source/` — raw reference images (public-domain portraits, engravings, photos).
- `<character>/refs/`   — style-transferred training set (ComfyUI img2img, denoise 0.60–0.70),
                          15–30 images at 640×640, identity retained + target style applied.
- `<character>/lora/`   — the trained `<name>.safetensors` + `<name>.meta.json` sidecar
                          (trigger_word, tensorart_job_id, base_model, sha256, trained_at).

`lora_library.json` (this folder) is the registry the render engine consumes:
  { "loras": [ { "name", "filename", "trigger_word", "strength" (0.65–0.80), "base_model",
                 "sha256", "tensorart_job_id", "trained_at", "notes" } ] }

Train with the LoRA workflow (Tensor.art training): see `docs/ILYRIUM-LORA-WORKFLOW.md`. After
training, sync the weights to the EC2 ComfyUI `models/loras/` and pin them in
`ilyrium-shots/models.lock.json` (role `lora_character`). The project scaffold is the AUTHORING
home; `models.lock.json` is the RENDER pin — no duplication.
