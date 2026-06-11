# satirist — Nast Creative Loop v1

End-to-end: a current event/signal -> Nast Brain (allegory + image prompt) ->
optional taste judge (one revise round) -> SDXL Hand LoRA render (GPU) ->
PIL caption banner -> saved PNG + sidecar JSON.

## Run (dev machine, no GPU)

```
cd apps/satirist
python -m pytest          # all logic tests, offline
python -m satirist.cli --topic "Tammany" --dry-run   # skips GPU render, emits concept + caption on a placeholder image
```

## Run the real render (GPU box only)
See "GPU Runbook" at the bottom of this README (added in the render task).

## GPU Runbook (real render)

The render step needs a CUDA box (the studio ComfyUI box `i-030994c5371ee5de9`,
or any g6.2xlarge). The dev machine and CI never run it.

1. On the box: `pip install diffusers torch transformers accelerate safetensors boto3 Pillow`
   and `pip install intake-spine` (or `pip install -e` the intake-spine repo).
2. Ensure the box's role/credentials can read `s3://ilyrium-slm-foundry/...` (the LoRA).
3. Ensure the Nast Brain is reachable: either run Ollama on the box (`ollama serve` + the
   `nast-brain` model imported) or set `BRAIN_URL` to a reachable host.
4. Set `OPENROUTER_API_KEY` if you want the taste judge (omit / pass `--no-judge` to skip).
5. Run:
   ```
   python -m satirist.cli --topic "Tammany" --ingest-feed https://example.com/politics.rss
   ```
   Output PNG + sidecar JSON land in `apps/satirist/var/output/`.

Cost note: stop or terminate the GPU box when done (see slm-foundry infra scripts) —
the volume bills even when stopped.
