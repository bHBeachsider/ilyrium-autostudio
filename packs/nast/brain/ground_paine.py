"""Ground the Nast Brain in Paine's 1904 biography (thin wrapper over src.ground)."""
import argparse
import sys, pathlib
# allow running as a plain script. This pack lives in ilyrium-autostudio, so `packs` resolves from
# this repository's root (parents[3]); the SLM Foundry engine (`src`) is found through
# SLM_FOUNDRY_ROOT, default: a sibling checkout named slm-foundry. The Foundry root is appended,
# never prepended, so the Foundry's own `packs` package cannot shadow this one.
import os
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))
_FOUNDRY_ROOT = pathlib.Path(os.environ.get("SLM_FOUNDRY_ROOT", _REPO_ROOT.parent / "slm-foundry"))
if _FOUNDRY_ROOT.is_dir() and str(_FOUNDRY_ROOT) not in sys.path:
    sys.path.append(str(_FOUNDRY_ROOT))

from src.ground import ground, chunk_text, parse_to_schema  # re-export chunk_text
from packs.nast.brain.build_dataset import to_message_row

ARCHIVE_ID = "thnasthisperiodh00painuoft"
TEXT_URL = f"https://archive.org/download/{ARCHIVE_ID}/{ARCHIVE_ID}_djvu.txt"

GROUNDED_KEYS = {"event", "allegory_rationale", "image_prompt"}

EXTRACT_SYSTEM = (
    "You are a historian of political cartoons. From the passage below, if it describes a "
    "SPECIFIC Thomas Nast cartoon and the event/issue it addressed, return JSON with exactly "
    "these three keys: "
    "{\"event\": \"<a neutral one-sentence description of the modern-equivalent situation>\", "
    "\"allegory_rationale\": \"<why Nast's metaphor fits the situation>\", "
    "\"image_prompt\": \"<period-correct wood-engraving image prompt>\"}. "
    "If the passage does NOT describe a specific cartoon, return exactly {}."
)

VERIFY_SYSTEM = (
    "You are a rigorous fact-checker for historical political cartoons. "
    "Given a passage from Paine's 1904 biography of Thomas Nast and a proposed allegory/image "
    "description, respond with PASS if the allegory and image prompt are genuinely supported by "
    "the passage text, or FAIL followed by a brief explanation if they are not. "
    "Start your response with exactly 'PASS' or 'FAIL'."
)


def parse_grounded(raw: str) -> dict | None:
    """Backward-compat shim: delegate to the generic parse_to_schema with GROUNDED_KEYS."""
    return parse_to_schema(raw, GROUNDED_KEYS)


def _to_row(pair: dict) -> dict:
    return to_message_row(
        pair["event"],
        {
            "allegory_rationale": pair["allegory_rationale"],
            "image_prompt": pair["image_prompt"],
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Ground Paine 1904 biography into Nast Brain rows.")
    ap.add_argument("--out", default="packs/nast/data/brain/grounded.jsonl")
    ap.add_argument("--max", type=int, default=150, help="Max chunks to try")
    a = ap.parse_args()
    kept = ground(
        source_url=TEXT_URL,
        extract_system=EXTRACT_SYSTEM,
        verify_system=VERIFY_SYSTEM,
        schema=GROUNDED_KEYS,
        to_row=_to_row,
        out=a.out,
        max_chunks=a.max,
    )
    print(f"grounded {kept} -> {a.out}")


if __name__ == "__main__":
    main()
