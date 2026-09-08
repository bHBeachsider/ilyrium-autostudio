#!/usr/bin/env python3
r"""judge.py - a vision model reads the comparison sheet and rules on each invariant (Phase 2, task 15).

The geometry gate measures pixels; it cannot tell a second row of chairs from a row of hay bales, or a workman from
a lamppost. A vision-language model can, if it is asked one narrow question at a time and made to answer in a fixed
form. This judge shows the model the BLOCKOUT | KEYFRAME sheet (the world on the left, the generated frame on the
right) and the shot's invariants (prompts/<SEQ>.json -> shots.<SHOT>.invariants), and gets back one verdict per
invariant: holds / violated / cannot_tell, with a one-line reason.

STATUS: ADVISORY. Verdicts are recorded beside the take and shown in the report; they block nothing until the
false-positive rate per invariant is measured against the eye on the regression set (gate/regression.py) and found
under 5%. Then individual invariants are promoted to blocking in BLOCKING below - never the whole judge at once.

Providers: anthropic (default; ANTHROPIC_API_KEY, claude-sonnet-4-5), openai-compatible (--provider openai with
OPENAI_API_KEY / --base-url for a Qwen-VL endpoint on the box). Each call is booked through cost_preflight as
"judge" (~$0.02).

usage: judge.py SHEET.png --shot SH009 [--seq NH-S901] [--provider anthropic|openai] [--model M] [--json OUT.json]
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))

BLOCKING = set()            # invariant texts promoted to blocking after measurement; empty until then

SYSTEM = ("You are the continuity supervisor on a film set. You are shown one image: on the LEFT a plain grey 3D "
          "blockout of the set from the shot camera (this is the ground truth of where things are), on the RIGHT the "
          "generated keyframe from the same camera. Judge ONLY the right-hand frame, using the left as the reference "
          "for layout. Answer strictly as JSON.")


def ask(sheet_path, invariants, provider, model, base_url=None):
    b64 = base64.b64encode(open(sheet_path, "rb").read()).decode()
    numbered = "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(invariants))
    user = ("For each numbered invariant below, say whether the RIGHT-hand keyframe satisfies it. Reply with JSON only: "
            "{\"verdicts\": [{\"n\": 1, \"verdict\": \"holds\"|\"violated\"|\"cannot_tell\", \"reason\": \"...\"}, ...]}. "
            "Be literal and strict: 'exactly two' means two, 'one row' means one row; if the thing is not visible in the "
            "frame at all, answer cannot_tell, not violated.\n\nInvariants:\n" + numbered)
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise SystemExit("[FAIL] ANTHROPIC_API_KEY not set")
        body = {"model": model or "claude-sonnet-4-5", "max_tokens": 1200, "system": SYSTEM,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": user}]}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read().decode())
        text = "".join(c.get("text", "") for c in out.get("content", []))
        usage = out.get("usage", {})
    else:
        key = os.environ.get("OPENAI_API_KEY", "none")
        url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        body = {"model": model or "gpt-4o-mini", "max_tokens": 1200,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": [
                                 {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
                                 {"type": "text", "text": user}]}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + key, "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.loads(r.read().decode())
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage", {})
    s = text[text.find("{"):text.rfind("}") + 1]
    return json.loads(s), usage, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet"); ap.add_argument("--shot", required=True); ap.add_argument("--seq", default="NH-S901")
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    ap.add_argument("--model"); ap.add_argument("--base-url"); ap.add_argument("--json")
    ap.add_argument("--no-book", action="store_true", help="skip the budget ledger (calibration runs)")
    a = ap.parse_args()
    book = json.load(open(os.path.join(PKG, "generation", "prompts", a.seq + ".json")))
    inv = book["shots"][a.shot].get("invariants", [])
    if not inv:
        print("  n/a  no invariants for %s" % a.shot); return 0
    if not a.no_book:
        from backlot import cost_preflight
        cost_preflight.preflight("judge", calls=1)
    t0 = time.time()
    res, usage, raw = ask(a.sheet, inv, a.provider, a.model, a.base_url)
    if not a.no_book:
        cost_preflight.book("judge", cost_preflight.estimate("judge", calls=1), note="judge %s %s" % (a.shot, os.path.basename(a.sheet)))
    verdicts = []
    blocking_fail = 0
    for v in res.get("verdicts", []):
        n = int(v.get("n", 0)); text = inv[n - 1] if 0 < n <= len(inv) else "?"
        verdict = v.get("verdict", "cannot_tell")
        blocking = text in BLOCKING
        if verdict == "violated" and blocking:
            blocking_fail += 1
        tag = {"holds": "ok  ", "violated": "FAIL" if blocking else "WARN", "cannot_tell": "n/a "}.get(verdict, "?   ")
        print("  %s %s - %s" % (tag, text, v.get("reason", "")))
        verdicts.append(dict(invariant=text, verdict=verdict, reason=v.get("reason", ""), blocking=blocking))
    out = dict(sheet=a.sheet, shot=a.shot, provider=a.provider, model=a.model, verdicts=verdicts, usage=usage,
               seconds=round(time.time() - t0, 1), status="advisory" if not BLOCKING else "partly blocking")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    n_viol = sum(v["verdict"] == "violated" for v in verdicts)
    print("[%s] judge: %d/%d invariants hold, %d violated (advisory%s)" % (
        "FAIL" if blocking_fail else "OK", sum(v["verdict"] == "holds" for v in verdicts), len(verdicts), n_viol,
        "" if not BLOCKING else ", %d blocking" % len(BLOCKING)))
    return 1 if blocking_fail else 0


if __name__ == "__main__":
    sys.exit(main())
