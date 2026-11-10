"""Regenerate tests/fixtures/ledger/format1_provenance.jsonl.

Run from the repo root:  python tests/fixtures/ledger/make_format1_golden.py

Writes three records with the REAL writer, ilyrium-shots/provenance.py `Ledger`
(schema validation on), for a fixture song that exists nowhere else. The output is
committed so the TypeScript side can test against real provenance-format lines
without running Python. Record ids and timestamps change on every regeneration;
tests must not depend on their values.
"""
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHOTS = REPO / "ilyrium-shots"
sys.path.insert(0, str(SHOTS))

import provenance  # noqa: E402

SONG = "TST-S001"  # fixture-only; not in SONG_ID_REGISTRY.json and never rendered
OUT = Path(__file__).with_name("format1_provenance.jsonl")


def spec(n: int) -> dict:
    return {
        "shot_id": f"{SONG}-SH{n:03d}",
        "song_id": SONG,
        "duration_s": 5,
        "camera": {"shot_size": "wide", "movement": "locked-off", "lens_mm": 35},
        "subjects": [],
        "setting": "fixture setting",
        "mood": "fixture",
        "action": f"fixture action {n}",
        "prompt": f"fixture prompt {n}",
        "negative_prompt": "fixture negative",
        "keyframe": {"source": "t2i", "ref_lora": "", "seed": 1000 + n},
        "seed": 1000 + n,
        "continuity": {"prev_shot": "", "flf2v": False},
        "render": {"width": 832, "height": 480, "fps": 16, "steps": 4, "duration_s": 5},
    }


def record(n: int) -> dict:
    return provenance.new_record(
        shot={"song_id": SONG, "shot_id": f"{SONG}-SH{n:03d}", "scene_id": f"{SONG}-SC01", "sequence_index": n},
        shot_spec=spec(n),
        generation={
            "width": 832, "height": 480, "frames": 81, "fps": 16, "steps": 4, "cfg": 1.0,
            "sampler": "euler", "scheduler": "simple", "seed": 1000 + n,
            "workflow_template": {"name": "fixture.api.json", "sha256": "0" * 64, "node_map_version": "1"},
        },
        models=[{"role": "diffusion_high_noise", "filename": "fixture.safetensors", "sha256": "1" * 64, "source": None}],
        engine={"comfyui_version": "fixture", "gpu": "none", "instance_id": None, "torch": None, "cuda": None},
    )


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ilyrium-ledger-golden-"))
    try:
        ledger = provenance.Ledger(tmp, schema_path=SHOTS / "provenance_record.schema.json", validate=True)
        if ledger._validate is None:
            raise SystemExit("jsonschema is required so the golden is schema-valid")
        first = ledger.append(SONG, record(1))
        ledger.append(SONG, record(2))
        # A second snapshot of shot 1, as a state change would write it.
        approved = {k: v for k, v in first.items() if k != "chain"}
        approved["status"] = "approved"
        approved["updated_at"] = provenance.now_iso()
        approved["approval"] = {"state": "approved", "reviewer": "fixture", "decided_at": approved["updated_at"], "note": None}
        ledger.append(SONG, approved)
        assert ledger.verify_chain(SONG)
        OUT.write_bytes(ledger.path_for(SONG).read_bytes())
        print(f"wrote {OUT} ({len(ledger.read(SONG))} records)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
