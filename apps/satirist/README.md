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
