"""Make `packs.nast...` resolve from this repository and the Foundry engine (`src.*`) resolve
from SLM_FOUNDRY_ROOT (default: sibling checkout ../slm-foundry), appended after this repository
so the Foundry's own `packs` package cannot shadow this one. No network, no model calls."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
FOUNDRY_ROOT = Path(os.environ.get("SLM_FOUNDRY_ROOT", REPO_ROOT.parent / "slm-foundry"))
if FOUNDRY_ROOT.is_dir() and str(FOUNDRY_ROOT) not in sys.path:
    sys.path.append(str(FOUNDRY_ROOT))
