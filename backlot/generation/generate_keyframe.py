#!/usr/bin/env python3
r"""generate_keyframe.py - a keyframe FROM THE WORLD: the stage's depth pass drives FLUX through a depth ControlNet.

Phase 1 of the OWS plan (docs/ows/OWS_PLATFORM_PLAN.md). The v8/v9 keyframes were made by showing an image-edit
model a clay render and hoping it kept the layout; it did not always (NH-USA-043/045/047/048/051). Here the layout is
not a suggestion: ControlNet Union Pro 2.0 in depth mode holds the diffusion to the depth pass rendered from the USD
stage at the shot's camera and set state (usd/render_passes.py), and the prompt only says what things are made of,
who is in frame, the weather and the look. Every take is then gated by gate/check_keyframe_geometry.py against the
same stage the pass came from.

Runs against a ComfyUI server (default http://127.0.0.1:8188 - the NH box's service, or a tunnel to it). The
workflow is keyframe_from_world.json (API format); prompts come from prompts/<SEQ>.json.

usage: generate_keyframe.py SHOT [SHOT ...] [--seq NH-S901] [--passes DIR] [--out DIR] [--takes 1] [--seed 0]
                            [--server http://127.0.0.1:8188] [--width 1344 --height 768] [--steps 28]
                            [--guidance 3.5] [--cn-strength 0.7] [--cn-end 0.8]
Writes <out>/<SHOT>/take_<seed>.png and take_<seed>.json (full provenance: prompt, workflow values, pass hashes,
world version) so the catalog can record how every image was made.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


class Comfy:
    def __init__(self, server):
        self.server = server.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def _json(self, path, data=None, method=None):
        req = urllib.request.Request(self.server + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def upload_image(self, path, name):
        boundary = "----backlot" + uuid.uuid4().hex
        body = b""
        body += ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"%s\"\r\n"
                 "Content-Type: image/png\r\n\r\n" % (boundary, name)).encode()
        body += open(path, "rb").read()
        body += ("\r\n--%s\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--%s--\r\n"
                 % (boundary, boundary)).encode()
        req = urllib.request.Request(self.server + "/upload/image", data=body, method="POST")
        req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())["name"]

    def queue(self, workflow):
        return self._json("/prompt", json.dumps({"prompt": workflow, "client_id": self.client_id}).encode())["prompt_id"]

    def wait(self, prompt_id, timeout=1800):
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = self._json("/history/" + prompt_id)
            if prompt_id in h:
                item = h[prompt_id]
                st = item.get("status", {})
                if st.get("status_str") == "error":
                    raise RuntimeError("ComfyUI error: %s" % json.dumps(st.get("messages", []))[:800])
                return item
            time.sleep(3)
        raise TimeoutError("ComfyUI did not finish %s in %ds" % (prompt_id, timeout))

    def fetch(self, filename, subfolder, folder_type, dst):
        q = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
        with urllib.request.urlopen(self.server + "/view?" + q, timeout=300) as r, open(dst, "wb") as f:
            f.write(r.read())


def fill(template, values):
    """Replace {{key}} placeholders; numeric strings become numbers so ComfyUI validates them."""
    def conv(v):
        if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
            return values[v[2:-2]]
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    wf = conv(template)
    wf.pop("_comment", None)
    return wf


def build_prompt(book, shot):
    s = book["shots"][shot]; sh = book["shared"]
    return "%s Weather and light: %s. %s. %s" % (s["text"], sh["gloom"], sh["dress"], sh["look"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shots", nargs="+")
    ap.add_argument("--seq", default="NH-S901")
    ap.add_argument("--passes", default=os.path.join(PKG, "usd", "nh", "passes"))
    ap.add_argument("--out", default=os.path.join(PKG, "renders", "keyframes"))
    ap.add_argument("--takes", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0, help="first seed; takes use seed, seed+1, ...")
    ap.add_argument("--server", default=os.environ.get("COMFY_SERVER", "http://127.0.0.1:8188"))
    ap.add_argument("--width", type=int, default=1344)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance", type=float, default=3.5)
    ap.add_argument("--cn-strength", type=float, default=0.7)
    ap.add_argument("--cn-end", type=float, default=0.8)
    ap.add_argument("--workflow", default=os.path.join(HERE, "keyframe_from_world.json"))
    a = ap.parse_args()

    template = json.load(open(a.workflow))
    book = json.load(open(os.path.join(HERE, "prompts", a.seq + ".json")))
    comfy = Comfy(a.server)
    for shot in a.shots:
        pdir = os.path.join(a.passes, shot)
        meta = json.load(open(os.path.join(pdir, "passes.json")))
        depth = os.path.join(pdir, "depth.png")
        uploaded = comfy.upload_image(depth, "%s_%s_depth.png" % (a.seq, shot))
        prompt = build_prompt(book, shot)
        odir = os.path.join(a.out, shot); os.makedirs(odir, exist_ok=True)
        for k in range(a.takes):
            seed = a.seed + k
            values = dict(prompt=prompt, guidance=a.guidance, depth_image=uploaded, cn_strength=a.cn_strength,
                          cn_end=a.cn_end, width=a.width, height=a.height, seed=seed, steps=a.steps,
                          prefix="backlot/%s_%s_%d" % (a.seq, shot, seed))
            wf = fill(template, values)
            t0 = time.time()
            pid = comfy.queue(wf)
            item = comfy.wait(pid)
            outs = [o for n in item["outputs"].values() for o in n.get("images", [])]
            if not outs:
                print("[FAIL] %s seed %d: no image in history" % (shot, seed), flush=True); continue
            dst = os.path.join(odir, "take_%d.png" % seed)
            comfy.fetch(outs[0]["filename"], outs[0].get("subfolder", ""), outs[0].get("type", "output"), dst)
            prov = dict(shot=shot, seq=a.seq, seed=seed, prompt=prompt, values={k: v for k, v in values.items() if k != "prompt"},
                        model="flux1-dev-fp8 + ControlNet Union Pro 2.0 (depth)", server=a.server,
                        depth_pass=dict(path=os.path.relpath(depth, PKG), sha256=sha256(depth)),
                        set_state=meta.get("set_state"), camera=meta.get("camera"), world_version=meta.get("world_version"),
                        seconds=round(time.time() - t0, 1), prompt_id=pid)
            json.dump(prov, open(os.path.join(odir, "take_%d.json" % seed), "w"), indent=1)
            print("[OK] %s seed %d -> %s (%.0fs)" % (shot, seed, dst, prov["seconds"]), flush=True)


if __name__ == "__main__":
    main()
