#!/usr/bin/env python3
"""backlot.catalog - the backlot catalog: a SQLite index with a YAML mirror that lives in git.

The YAML (backlot/catalog/<world>.yaml) is the reviewable, diffable truth; the SQLite file is a rebuildable index for
queries. `find` takes structured filters; an embeddings column is reserved for when the catalog is large enough to
need semantic search (it is not, yet).

usage:
  python3 -m backlot.catalog rebuild                      # YAML -> SQLite
  python3 -m backlot.catalog find [kind=set] [tag=timber] [state=finished] [production=NH]
  python3 -m backlot.catalog show RallyStage
  python3 -m backlot.catalog used_in NH-S901
"""
import json
import os
import sqlite3
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
YAML_DIR = os.path.join(HERE, "catalog")
DB = os.path.join(HERE, "catalog", "catalog.sqlite")


def load_yaml():
    rows = []
    for f in sorted(os.listdir(YAML_DIR)):
        if f.endswith(".yaml"):
            rows += yaml.safe_load(open(os.path.join(YAML_DIR, f))) or []
    return rows


def rebuild():
    rows = load_yaml()
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE assets (asset_id TEXT PRIMARY KEY, kind TEXT, production TEXT, world TEXT,
                   period_start INT, period_end INT, grade TEXT, usd TEXT, states TEXT, tags TEXT, formats TEXT,
                   text_planes TEXT, control_points TEXT, method TEXT, license TEXT, approval TEXT, used_in TEXT,
                   embedding BLOB, doc TEXT)""")
    for r in rows:
        p = r.get("provenance", {})
        con.execute("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            r["asset_id"], r.get("kind"), r.get("production"), r.get("world"),
            (r.get("period") or {}).get("start"), (r.get("period") or {}).get("end"), r.get("grade"), r.get("usd"),
            json.dumps(r.get("states", [])), json.dumps(r.get("tags", [])), json.dumps(r.get("formats", [])),
            json.dumps(r.get("text_planes", [])), json.dumps(r.get("control_points", [])),
            p.get("method"), p.get("license"), p.get("approval_status"), json.dumps(p.get("used_in", [])),
            None, json.dumps(r)))
    con.commit(); con.close()
    return len(rows)


def find(**f):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    q, args = "SELECT asset_id, kind, grade, states, tags, approval FROM assets WHERE 1=1", []
    for k in ("kind", "production", "grade", "world"):
        if k in f:
            q += " AND %s = ?" % k; args.append(f[k])
    if "tag" in f:
        q += " AND tags LIKE ?"; args.append('%"' + f["tag"] + '"%')
    if "state" in f:
        q += " AND states LIKE ?"; args.append('%"' + f["state"] + '"%')
    if "text" in f:
        q += " AND text_planes != '[]'"
    rows = con.execute(q + " ORDER BY asset_id", args).fetchall(); con.close()
    return [dict(r) for r in rows]


def show(asset_id):
    con = sqlite3.connect(DB)
    r = con.execute("SELECT doc FROM assets WHERE asset_id = ?", (asset_id,)).fetchone(); con.close()
    return json.loads(r[0]) if r else None


def used_in(production):
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT asset_id FROM assets WHERE used_in LIKE ?", ('%"' + production + '"%',)).fetchall(); con.close()
    return [r[0] for r in rows]


def main():
    a = sys.argv[1:]
    if not a or a[0] == "rebuild":
        print("catalog: %d assets indexed" % rebuild()); return
    if a[0] == "find":
        f = dict(kv.split("=", 1) for kv in a[1:])
        for r in find(**f):
            print("%-14s %-10s %-13s states=%-60s tags=%s" % (r["asset_id"], r["kind"], r["grade"], r["states"], r["tags"]))
        return
    if a[0] == "show":
        print(yaml.safe_dump(show(a[1]), sort_keys=False)); return
    if a[0] == "used_in":
        print("\n".join(used_in(a[1]))); return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
