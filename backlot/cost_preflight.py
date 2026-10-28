#!/usr/bin/env python3
"""backlot.cost_preflight - no generation without a price and a budget.

fal has no balance endpoint (its 403 "balance" probe only says when it is gone), so the studio keeps its own book:
backlot/budget.yaml holds deposits and a floor; every entry point appends what it spent. Rates are OBSERVED, not
assumed: Veo 3.1 billed above the $0.20/s the teaser budgeted, so it is booked at $0.25/s until measured better.

usage (as a library):
    from backlot.cost_preflight import preflight, book
    preflight("veo3.1", seconds=6, shot="NH-S901-SH009")   # raises BudgetRefused if over cap / under floor
    book("veo3.1", 1.50, shot="NH-S901-SH009", note="take 3")
usage (cli):  python3 -m backlot.cost_preflight status | deposit 24 | book veo3.1 1.20 NH-S901-SH009
"""
import datetime
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = os.path.join(HERE, "budget.yaml")

RATES = {                                   # USD; observed where noted
    "veo3.1": {"per_second": 0.25, "note": "billed above the $0.20/s estimate in NH-S901 v8 (balance ran out early)"},
    "veo3.1-fast": {"per_second": 0.10},
    "nano-banana-pro/edit": {"per_image": 0.15},
    "elevenlabs/sfx": {"per_clip": 0.10},
    "wan2.2-box": {"per_second": 0.0, "note": "EC2 time is booked separately as gpu_hours"},
    "gpu_hours": {"per_hour": 1.21, "note": "g5.2xlarge on-demand, us-east-1"},
    "judge": {"per_call": 0.02, "note": "one vision call on a comparison sheet (claude-sonnet-4-5, ~2k tokens)"},
}


class BudgetRefused(Exception):
    pass


def _load():
    if not os.path.exists(BUDGET):
        return {"deposits": [], "spend": [], "floor_usd": 2.0, "per_shot_cap_usd": 6.0}
    return yaml.safe_load(open(BUDGET)) or {}


def _save(b):
    yaml.safe_dump(b, open(BUDGET, "w"), sort_keys=False)


def balance(b=None):
    b = b or _load()
    return sum(d["usd"] for d in b.get("deposits", [])) - sum(s["usd"] for s in b.get("spend", []))


def shot_spend(shot, b=None):
    b = b or _load()
    return sum(s["usd"] for s in b.get("spend", []) if s.get("shot") == shot)


def estimate(service, **q):
    r = RATES[service]
    if "per_second" in r:
        return r["per_second"] * q.get("seconds", 0)
    if "per_image" in r:
        return r["per_image"] * q.get("images", 1)
    if "per_call" in r:
        return r["per_call"] * q.get("calls", 1)
    if "per_clip" in r:
        return r["per_clip"] * q.get("clips", 1)
    if "per_hour" in r:
        return r["per_hour"] * q.get("hours", 0)
    return 0.0


def preflight(service, shot=None, **q):
    b = _load()
    cost = estimate(service, **q)
    bal = balance(b)
    if bal - cost < b.get("floor_usd", 2.0):
        raise BudgetRefused("%s would cost $%.2f; balance $%.2f would fall below the $%.2f floor" % (service, cost, bal, b.get("floor_usd", 2.0)))
    if shot and shot_spend(shot, b) + cost > b.get("per_shot_cap_usd", 6.0):
        raise BudgetRefused("%s: $%.2f already spent on %s; this $%.2f would pass the $%.2f per-shot cap - ask before spending"
                            % (service, shot_spend(shot, b), shot, cost, b.get("per_shot_cap_usd", 6.0)))
    print("[preflight] %s $%.2f ok - balance $%.2f -> $%.2f%s" % (service, cost, bal, bal - cost, (" (shot %s: $%.2f)" % (shot, shot_spend(shot, b) + cost)) if shot else ""))
    return cost


def book(service, usd, shot=None, note=""):
    b = _load()
    b.setdefault("spend", []).append({"when": datetime.datetime.now().isoformat(timespec="minutes"), "service": service,
                                      "usd": round(float(usd), 2), "shot": shot, "note": note})
    _save(b)


def deposit(usd, note=""):
    b = _load()
    b.setdefault("deposits", []).append({"when": datetime.datetime.now().isoformat(timespec="minutes"), "usd": float(usd), "note": note})
    _save(b)


def main():
    a = sys.argv[1:]
    if not a or a[0] == "status":
        b = _load()
        print("balance $%.2f  (floor $%.2f, per-shot cap $%.2f, %d deposits, %d bookings)" % (
            balance(b), b.get("floor_usd", 2.0), b.get("per_shot_cap_usd", 6.0), len(b.get("deposits", [])), len(b.get("spend", []))))
        return
    if a[0] == "deposit":
        deposit(float(a[1]), " ".join(a[2:])); print("deposited $%.2f; balance $%.2f" % (float(a[1]), balance())); return
    if a[0] == "book":
        book(a[1], float(a[2]), a[3] if len(a) > 3 else None, " ".join(a[4:])); print("booked; balance $%.2f" % balance()); return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
