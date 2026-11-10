"""Cross-format ledger test, Python half (ILY-206 Phase 0 task 3).

Two line formats can be written to ilyrium-shots/ledger/<song>.jsonl:

  format 1 - ilyrium-shots/provenance.py `Ledger`: snapshot records with
             chain.prev_record_hash / chain.record_hash
  format 3 - apps/control-panel/lib/ledger.ts: {seq,event,songId,payload,ts,prev,hash}

These tests pin down, by running the real code, what the Python side does with
format-3 lines. The TypeScript half is
apps/control-panel/lib/ledger.crossformat.test.ts. Both read the same committed
goldens in tests/fixtures/ledger/, each produced by its own real writer:

  format1_provenance.jsonl  <- tests/fixtures/ledger/make_format1_golden.py
  format3_events.jsonl      <- UPDATE_LEDGER_GOLDEN=1 vitest (see the TS test)

Every write goes to a pytest tmp dir. Nothing here touches ilyrium-shots/ledger.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOTS = REPO_ROOT / "ilyrium-shots"
if str(SHOTS) not in sys.path:
    sys.path.insert(0, str(SHOTS))

import provenance  # noqa: E402

GOLDEN = REPO_ROOT / "tests" / "fixtures" / "ledger"
FORMAT1 = GOLDEN / "format1_provenance.jsonl"
FORMAT3 = GOLDEN / "format3_events.jsonl"
SONG = "TST-S001"  # fixture-only id


def _lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


@pytest.fixture
def ledger(tmp_path):
    # validate=False: these tests are about chaining across formats, and a format-3
    # line is not a provenance record at all.
    return provenance.Ledger(tmp_path, validate=False)


def _install(ledger, *sources: Path) -> Path:
    """Build <tmp>/<SONG>.jsonl from the given files, in order."""
    target = ledger.path_for(SONG)
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        for src in sources:
            for ln in _lines(src):
                fh.write(ln + "\n")
    return target


# --------------------------------------------------------------------------- #
# The goldens are what they claim to be
# --------------------------------------------------------------------------- #
def test_format1_golden_is_provenance_format_and_verifies(ledger):
    _install(ledger, FORMAT1)
    recs = ledger.read(SONG)
    assert len(recs) == 3
    assert all(r["chain"]["record_hash"].startswith("sha256:") for r in recs)
    assert all("seq" not in r and "hash" not in r for r in recs)
    assert ledger.verify_chain(SONG) is True


def test_format1_golden_is_schema_valid():
    pytest.importorskip("jsonschema")
    validate = provenance._load_validator(SHOTS / "provenance_record.schema.json")
    assert validate is not None
    for ln in _lines(FORMAT1):
        errs = validate(json.loads(ln))
        assert not errs, [e.message for e in errs[:3]]


def test_format3_golden_is_event_format():
    recs = [json.loads(ln) for ln in _lines(FORMAT3)]
    assert len(recs) == 3
    assert [r["seq"] for r in recs] == [1, 2, 3]
    assert all(set(r) == {"seq", "event", "songId", "payload", "ts", "prev", "hash"} for r in recs)
    assert all("chain" not in r for r in recs)


# --------------------------------------------------------------------------- #
# What provenance.py does with lib/ledger.ts lines
# --------------------------------------------------------------------------- #
def test_python_verifier_rejects_a_valid_format3_ledger(ledger):
    _install(ledger, FORMAT3)
    assert ledger.verify_chain(SONG) is False


def test_one_format3_line_after_provenance_history_breaks_chain_ok(ledger):
    """The case that matters for a real film ledger: valid history, then one
    lib/ledger.ts append (takes route, fal webhook)."""
    target = _install(ledger, FORMAT1)
    assert ledger.verify_chain(SONG) is True
    with target.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_lines(FORMAT3)[0] + "\n")
    assert ledger.verify_chain(SONG) is False


def test_python_append_after_format3_line_does_not_heal_the_chain(ledger):
    """After a foreign line, Ledger.append cannot find a record_hash to chain from,
    so it starts a new chain (prev None) in the middle of the file."""
    target = _install(ledger, FORMAT1)
    history = _lines(target)
    with target.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_lines(FORMAT3)[0] + "\n")

    template = {k: v for k, v in json.loads(history[0]).items() if k != "chain"}
    appended = ledger.append(SONG, template)

    assert appended["chain"]["prev_record_hash"] is None
    after = _lines(target)
    assert after[: len(history)] == history  # append-only holds for the old lines
    assert len(after) == len(history) + 2
    assert ledger.verify_chain(SONG) is False


def test_python_append_onto_a_format3_ledger_is_also_rejected_by_python(ledger):
    target = _install(ledger, FORMAT3)
    before = _lines(target)
    template = {k: v for k, v in json.loads(_lines(FORMAT1)[0]).items() if k != "chain"}
    ledger.append(SONG, template)
    assert _lines(target)[: len(before)] == before
    assert ledger.verify_chain(SONG) is False


def test_tests_never_use_the_real_ledger_dir(ledger):
    assert SHOTS / "ledger" not in ledger.dir.parents
    assert ledger.dir != SHOTS / "ledger"
    shutil.rmtree(ledger.dir, ignore_errors=True)
