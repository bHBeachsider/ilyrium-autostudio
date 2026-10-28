"""
check_tool_updates — detect when a tool changed so its manual can be refreshed before it goes stale.

A stale manual is worse than none (the agent becomes confidently wrong), so this watches three
fingerprint kinds per app and compares to a recorded baseline (manuals/_versions.json):

  - winver : the INSTALLED version of a local app (registry DisplayVersion on Windows). Highest
             signal — this is how the "new DaVinci update just dropped" is caught directly.
  - file   : sha256 of a captured local source (e.g. the Resolve scripting README, the Igniter PDF,
             the Blender manual index). Catches a re-captured/updated doc.
  - web    : sha256 of a live doc page (advisory — web pages have dynamic bits, so treat as a hint).

Run on the Windows host (it needs the installs + network):
    python check_tool_updates.py                 # report drift vs baseline
    python check_tool_updates.py --update         # record current fingerprints as the new baseline
    python check_tool_updates.py --json           # machine-readable (for a scheduled task)

Best invoked on a schedule (weekly). A CHANGED app means: re-run the manual-to-agent-transform skill
on that tool's source and bump its agent_package.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_MANUALS = os.path.join(_REPO, "manuals")
_BASELINE = os.path.join(_MANUALS, "_versions.json")

# Per app: the fingerprint sources to watch.
CHECKS = {
    "davinci-resolve": [
        {"kind": "winver", "name": "DaVinci Resolve"},
        {"kind": "file", "path": "manuals/davinci-resolve/source/Resolve_Scripting_README.txt"},
    ],
    "blender": [
        {"kind": "winver", "name": "Blender"},
    ],
    "igniter": [
        {"kind": "file", "path": "manuals/igniter/source/Igniter_Manual.pdf"},
    ],
    "tensorart-tams": [
        {"kind": "web", "url": "https://tams-docs.tensor.art/docs/api/intro"},
    ],
    "runway": [
        {"kind": "web", "url": "https://docs.dev.runwayml.com/api-details/sdks/"},
    ],
    "comfyui": [
        {"kind": "web", "url": "https://docs.comfy.org/development/comfyui-server/comms_overview"},
    ],
    "elevenlabs": [
        # docs site is JS-rendered (doesn't fetch cleanly); the captured source is the stable anchor.
        {"kind": "file", "path": "manuals/elevenlabs/source/elevenlabs_api_docs.md"},
    ],
    "ffmpeg": [
        # studio-scoped CLI notes; binary ships via imageio-ffmpeg, so the notes file is the anchor.
        {"kind": "file", "path": "manuals/ffmpeg/source/ffmpeg_cli_notes.md"},
    ],
    "unreal-engine": [
        # Epic's Python docs are JS-rendered; track the installed engine version (highest signal).
        {"kind": "winver", "name": "Unreal Engine"},
    ],
    "filmcraft": [
        # pinned clone (FILMCRAFT_PIN); docs copied from filmcraft/docs, commands.json is the
        # CLI's `commands --json` output — re-capture both when the pin moves.
        {"kind": "file", "path": "manuals/filmcraft/source/agents.md"},
        {"kind": "file", "path": "manuals/filmcraft/source/control-protocol.md"},
        {"kind": "file", "path": "manuals/filmcraft/source/commands.json"},
    ],
}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def _fingerprint(src) -> str:
    kind = src["kind"]
    try:
        if kind == "file":
            p = os.path.join(_REPO, src["path"])
            if not os.path.exists(p):
                return "MISSING"
            with open(p, "rb") as f:
                return "file:" + _sha(f.read())
        if kind == "winver":
            if platform.system() != "Windows":
                return "SKIP(not-windows)"
            ps = ("Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*',"
                  "'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' "
                  "-ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq '" + src["name"] +
                  "' } | Select-Object -First 1 -ExpandProperty DisplayVersion")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, text=True, timeout=30)
            v = (r.stdout or "").strip()
            return "ver:" + v if v else "NOT-INSTALLED"
        if kind == "web":
            import urllib.request
            req = urllib.request.Request(src["url"], headers={"User-Agent": "ilyrium-update-check"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                txt = resp.read().decode("utf-8", "replace")
            # normalize: collapse whitespace to reduce churn from formatting
            norm = " ".join(txt.split())
            return "web:" + _sha(norm.encode())
    except Exception as e:
        return f"ERR({type(e).__name__})"
    return "UNKNOWN"


def run(update=False):
    baseline = {}
    if os.path.exists(_BASELINE):
        try:
            baseline = json.load(open(_BASELINE, encoding="utf-8"))
        except Exception:
            baseline = {}
    current, status = {}, {}
    for app, srcs in CHECKS.items():
        current[app] = {f"{s['kind']}:{s.get('name') or os.path.basename(s.get('path','') ) or s.get('url','')}": _fingerprint(s) for s in srcs}
        old = baseline.get(app, {})
        changed = [k for k, v in current[app].items()
                   if k in old and old[k] != v and not v.startswith(("SKIP", "ERR"))]
        new = [k for k in current[app] if k not in old]
        if changed:
            status[app] = ("CHANGED", changed)
        elif not old:
            status[app] = ("NEW", new)
        else:
            status[app] = ("ok", [])
    return current, status


def main(argv):
    update = "--update" in argv
    as_json = "--json" in argv
    current, status = run(update=update)

    if as_json:
        print(json.dumps({"status": {k: v[0] for k, v in status.items()},
                          "changed": [k for k, v in status.items() if v[0] == "CHANGED"]}, indent=2))
    else:
        print("Tool-manual staleness check (baseline: manuals/_versions.json)\n")
        for app, (st, detail) in status.items():
            mark = {"CHANGED": "⚠ CHANGED — re-transform", "NEW": "· new (recording baseline)", "ok": "✓ up to date"}[st]
            extra = f"  [{', '.join(detail)}]" if detail else ""
            print(f"  {app:18} {mark}{extra}")
        stale = [k for k, v in status.items() if v[0] == "CHANGED"]
        print(f"\n{len(stale)} manual(s) need refresh" + (": " + ", ".join(stale) if stale else "."))

    if update:
        json.dump(current, open(_BASELINE, "w", encoding="utf-8"), indent=2)
        print(f"\nBaseline written → {_BASELINE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
