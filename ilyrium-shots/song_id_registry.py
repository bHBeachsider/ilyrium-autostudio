"""
song_id_registry - ownership guard for song IDs in ilyrium-shots/.

Why this exists
---------------
Until 2026-09-01 `shot_spec.schema.json` hardcoded `^NH-S[0-9]{2,}$` for song_id, so
EVERY project in the studio was forced onto the NH- prefix. KING SIZE ended up as
NH-S05 sitting in the same flat shots/ directory as NEW HARNOMY's NH-S101/NH-S348.
The schema now accepts `^[A-Z]{2,4}-S[0-9]{2,}$`; this module makes ownership explicit
and catches a collision BEFORE a batch of specs lands on top of another project's work.

It never renames anything. IDs with ledger history are permanent - the provenance chain
is keyed on them.

Use
---
    python song_id_registry.py check                     # audit every spec in shots/
    python song_id_registry.py check --project king_size # audit one project's IDs
    python song_id_registry.py claim KS --project king_size
    python song_id_registry.py owner NH-S05

    from song_id_registry import owner_of, assert_owned
    assert_owned("NH-S101", "new_harnomy_usa")   # raises SongIdConflict on mismatch

Pure stdlib. No network.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "SONG_ID_REGISTRY.json")
SHOTS_DIR = os.path.join(HERE, "shots")

SONG_ID_RE = re.compile(r"^([A-Z]{2,4})-S([0-9]{2,})$")
SHOT_ID_RE = re.compile(r"^([A-Z]{2,4})-S([0-9]{2,})-SH([0-9]{3,})$")


class SongIdConflict(Exception):
    pass


def load_registry(path=REGISTRY_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_song_id(song_id):
    """-> (prefix, number) or raise ValueError."""
    m = SONG_ID_RE.match(song_id or "")
    if not m:
        raise ValueError(
            "song_id %r does not match ^[A-Z]{2,4}-S[0-9]{2,}$" % (song_id,))
    return m.group(1), m.group(2)


def owner_of(song_id, reg=None):
    """Which project owns this ID? Legacy claims win over the prefix rule."""
    reg = reg or load_registry()
    legacy = reg.get("legacy_claims", {}).get(song_id)
    if legacy:
        return legacy["project"]
    prefix, _ = parse_song_id(song_id)
    entry = reg.get("prefixes", {}).get(prefix)
    if not entry:
        raise SongIdConflict(
            "prefix %r is not claimed in SONG_ID_REGISTRY.json - claim it before "
            "scaffolding (python song_id_registry.py claim %s --project <name>)"
            % (prefix, prefix))
    return entry["project"]


def assert_owned(song_id, project, reg=None):
    """Raise unless `project` owns `song_id`. Call this before writing specs."""
    actual = owner_of(song_id, reg)
    if actual != project:
        raise SongIdConflict(
            "song_id %s belongs to project %r, not %r. Pick an ID under your own "
            "prefix. Never re-prefix an ID that has ledger history."
            % (song_id, actual, project))
    return True


def _iter_specs(shots_dir=SHOTS_DIR):
    if not os.path.isdir(shots_dir):
        return
    for name in sorted(os.listdir(shots_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(shots_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                yield name, json.load(fh)
        except (ValueError, OSError) as exc:
            yield name, {"__error__": str(exc)}


def check(project=None, shots_dir=SHOTS_DIR, reg=None):
    """Audit every spec. Returns (problems, summary) - problems is a list of strings."""
    reg = reg or load_registry()
    problems = []
    by_song = defaultdict(list)

    for name, spec in _iter_specs(shots_dir):
        if "__error__" in spec:
            problems.append("%s: unreadable (%s)" % (name, spec["__error__"]))
            continue

        song_id = spec.get("song_id")
        shot_id = spec.get("shot_id")

        try:
            prefix, _ = parse_song_id(song_id)
        except ValueError as exc:
            problems.append("%s: %s" % (name, exc))
            continue

        m = SHOT_ID_RE.match(shot_id or "")
        if not m:
            problems.append(
                "%s: shot_id %r does not match ^[A-Z]{2,4}-S[0-9]{2,}-SH[0-9]{3,}$"
                % (name, shot_id))
        elif not shot_id.startswith(song_id + "-SH"):
            problems.append(
                "%s: shot_id %s is not under its own song_id %s"
                % (name, shot_id, song_id))

        try:
            owner = owner_of(song_id, reg)
        except SongIdConflict as exc:
            problems.append("%s: %s" % (name, exc))
            continue

        by_song[song_id].append((name, owner))

        if project and owner != project:
            problems.append(
                "%s: song_id %s is owned by %r, not %r"
                % (name, song_id, owner, project))

    summary = {sid: {"owner": rows[0][1], "specs": len(rows)}
               for sid, rows in sorted(by_song.items())}
    return problems, summary


def claim(prefix, project, title=None, path=REGISTRY_PATH):
    """Add a prefix claim. Refuses to silently take one that already exists."""
    reg = load_registry(path)
    prefixes = reg.setdefault("prefixes", {})
    existing = prefixes.get(prefix)
    if existing and existing.get("project") != project:
        raise SongIdConflict(
            "prefix %r already belongs to %r" % (prefix, existing.get("project")))
    prefixes[prefix] = {
        "project": project,
        "title": title or project,
        "reserved_ranges": ["%s-S01..%s-S99" % (prefix, prefix)],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=2)
        fh.write("\n")
    return prefixes[prefix]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="audit shot specs against the registry")
    c.add_argument("--project", default=None)
    c.add_argument("--shots-dir", default=SHOTS_DIR)

    o = sub.add_parser("owner", help="print the owning project for a song ID")
    o.add_argument("song_id")

    k = sub.add_parser("claim", help="claim a prefix for a project")
    k.add_argument("prefix")
    k.add_argument("--project", required=True)
    k.add_argument("--title", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "owner":
        print(owner_of(args.song_id))
        return 0

    if args.cmd == "claim":
        entry = claim(args.prefix, args.project, args.title)
        print("[OK] %s -> %s" % (args.prefix, entry["project"]))
        return 0

    problems, summary = check(args.project, args.shots_dir)
    for song_id, info in summary.items():
        print("  %-12s %-24s %3d specs" % (song_id, info["owner"], info["specs"]))
    if problems:
        print("\n[FAIL] %d problem(s):" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("\n[OK] %d song ID(s), no ownership conflicts." % len(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
