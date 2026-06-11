#!/usr/bin/env python3
"""
lora_gen.py - reusable Astria character-LoRA trainer for ANY Ilyrium character.

One tool for every character. It operates on a character's own config + folders, so a
new character needs only: a `refs/` image set and an `astria_tune_config.json`
(scaffold one with --init). Trains both an SDXL and a Flux tune from the same dataset.

Stdlib-only (urllib). Creating a tune trains on Astria's GPUs and costs credits, so
nothing runs on its own - you invoke it.

PREREQUISITE
    set ASTRIA_API_KEY in the environment   (https://www.astria.ai/users/edit#api)

LOCATING A CHARACTER (any one of):
    --config PATH                       explicit path to astria_tune_config.json
    --char  DIR                         a character dir (uses DIR/train/astria_tune_config.json)
    --project P --character C           projects/P/03_design/characters/loras/C/...

COMMANDS
    --init --char DIR --token NAME [--class person] [--image-glob '*.jpg']
                                        scaffold refs/ lora/ train/ + a config for a new character
    --dry-run                           validate config + list images (no network)
    --create [--only sdxl|flux]         create the tune(s); prints tune ids
    --poll KEY TUNE_ID                  wait for training; download weights if available; register
    --register-local KEY PATH           register a manually-downloaded CKPT/TAR/.safetensors

EXAMPLES
    python lora_gen.py --init --char ../../projects/nadia/03_design/characters/loras/nadia --token nadia --class woman
    python lora_gen.py --char  ../../projects/nadia/03_design/characters/loras/nadia --create
    python lora_gen.py --project nadia --character nadia --poll sdxl 5071234
Docs: https://docs.astria.ai/docs/api/tune/create/
"""
from __future__ import annotations
import argparse, glob, hashlib, json, mimetypes, os, sys, time, uuid
import urllib.request, urllib.error

API_BASE = "https://api.astria.ai"
# Cloudflare in front of api.astria.ai 1010-blocks default library UAs (python-urllib).
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

CONFIG_NAME = "astria_tune_config.json"


# ---------------------------------------------------------------- locating
def _find_repo_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, "projects")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            return None
        d = nd


def resolve_config_path(args):
    if args.config:
        return os.path.abspath(args.config)
    if args.char:
        return os.path.abspath(os.path.join(args.char, "train", CONFIG_NAME))
    if args.project and args.character:
        from project_paths import resolve_project
        return os.path.join(resolve_project(args.project), "03_design", "characters",
                            "loras", args.character, "train", CONFIG_NAME)
    return os.path.abspath(CONFIG_NAME)  # cwd fallback


def load_cfg(cfg_path):
    if not os.path.exists(cfg_path):
        sys.exit(f"no config at {cfg_path}\n  scaffold one with:  python {os.path.basename(__file__)} --init --char <dir> --token <name>")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    return cfg, os.path.dirname(cfg_path)   # BASE = config's directory; all rel paths resolve from here


def _tune(cfg, key):
    for t in cfg["tunes"]:
        if t["key"] == key:
            return t
    sys.exit(f"no tune with key '{key}' (have: {[t['key'] for t in cfg['tunes']]})")


def _apikey():
    k = os.environ.get("ASTRIA_API_KEY")
    if not k:
        sys.exit("ERROR: set ASTRIA_API_KEY (https://www.astria.ai/users/edit#api). Never hard-code it.")
    return k


def _abs(base, rel):
    return os.path.normpath(os.path.join(base, rel))


def _images(cfg, base):
    d = _abs(base, cfg["shared"]["images_dir"])
    return sorted(glob.glob(os.path.join(d, cfg["shared"]["image_glob"])))


# ---------------------------------------------------------------- http
def _multipart(fields, files):
    boundary = "----astria" + uuid.uuid4().hex
    out = []
    for name, value in fields:
        out.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    for name, path in files:
        fn = os.path.basename(path)
        ctype = mimetypes.guess_type(fn)[0] or "application/octet-stream"
        out.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fn}\"\r\n".encode())
        out.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        out.append(open(path, "rb").read())
        out.append(b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def _http(method, url, key, body=None, ctype=None):
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": UA}
    if ctype:
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {method} {url}\n{e.read().decode('utf-8','replace')[:800]}")


# ---------------------------------------------------------------- create / poll
def create_one(cfg, base, t):
    key = _apikey()
    sh = cfg["shared"]
    imgs = _images(cfg, base)
    if not imgs:
        sys.exit(f"no images match {sh['images_dir']}/{sh['image_glob']} (from {base})")
    if sh.get("expected_image_count") and len(imgs) != sh["expected_image_count"]:
        print(f"  WARNING: found {len(imgs)} images, expected {sh['expected_image_count']}")
    title = t["title"].replace("REPLACE_WITH_UUID", str(uuid.uuid4()))
    fields = [
        ("tune[title]", title), ("tune[name]", sh["name"]), ("tune[branch]", t["branch"]),
        ("tune[token]", sh["token"]), ("tune[model_type]", t["model_type"]),
        ("tune[face_crop]", str(sh["face_crop"]).lower()),
        ("tune[training_face_correct]", str(sh["training_face_correct"]).lower()),
    ]
    if sh.get("steps"):
        fields.append(("tune[steps]", str(sh["steps"])))
    if t.get("preset"):
        fields.append(("tune[preset]", t["preset"]))
    if t.get("base_tune_id"):
        fields.append(("tune[base_tune_id]", str(t["base_tune_id"])))
    for p in cfg.get("prompts_attributes", []):
        fields.append(("tune[prompts_attributes][][text]", p["text"]))
        fields.append(("tune[prompts_attributes][][inpaint_faces]", str(p.get("inpaint_faces", False)).lower()))
        fields.append(("tune[prompts_attributes][][super_resolution]", str(p.get("super_resolution", False)).lower()))
    files = [("tune[images][]", p) for p in imgs]
    body, ctype = _multipart(fields, files)
    print(f"[{t['key']}] POST {API_BASE}/tunes  ({len(imgs)} imgs, branch={t['branch']}, token='{sh['token']}')")
    resp = _http("POST", f"{API_BASE}/tunes", key, body, ctype)
    tid = resp.get("id")
    print(f"  -> {t['key']} tune id: {tid}   eta: {resp.get('eta')}")
    print(f"  finalize:  python {os.path.basename(__file__)} <same --char/--config> --poll {t['key']} {tid}")
    return resp


def poll(cfg, base, key_name, tune_id):
    t = _tune(cfg, key_name)
    api = _apikey()
    print(f"[{key_name}] polling tune {tune_id} ...")
    while True:
        j = _http("GET", f"{API_BASE}/tunes/{tune_id}.json", api)
        if j.get("trained_at"):
            print("  trained.")
            break
        print(f"  not ready (eta {j.get('eta')}); sleeping 30s")
        time.sleep(30)
    weights = j.get("ckpt_url") or next((u for u in (j.get("ckpt_urls") or []) if u), None)
    meta = _meta(cfg, t, tune_id, trained_at=j.get("trained_at"), ref=j.get("ref_with_trigger"))
    meta_path = _abs(base, t["meta_out"])
    if not weights:
        print(f"  TRAINED, but no downloadable weights URL is present:")
        print(f"    ckpt_url={j.get('ckpt_url')!r}  ckpt_urls={j.get('ckpt_urls')!r}")
        print(f"  Astria serves weights via the TAR/CKPT buttons on the tune page, not this field.")
        print(f"  Download from https://www.astria.ai/tunes/{tune_id} then run:")
        print(f"    python {os.path.basename(__file__)} <--char/--config> --register-local {key_name} <file>")
        print(f"  (The tune is fully usable via the API by id {tune_id} regardless.)")
        meta.update(status="trained_hosted", sha256=None, filename=None)
        _write(meta_path, meta); _register(cfg, base, t, meta)
        print(f"  registered '{t['registry_name']}' as trained_hosted.")
        return
    out = _abs(base, t["lora_out"]); os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"  downloading LoRA -> {out}")
    data = urllib.request.urlopen(urllib.request.Request(weights, headers={"User-Agent": UA}), timeout=900).read()
    open(out, "wb").write(data)
    meta.update(sha256=hashlib.sha256(data).hexdigest(), filename=os.path.basename(out), status="trained")
    _write(meta_path, meta); _register(cfg, base, t, meta)
    print(f"  done. sha256={meta['sha256'][:16]}...  registered '{t['registry_name']}'.")


# ---------------------------------------------------------------- local register
def _safe_extract_tar(src, dest):
    import tarfile
    with tarfile.open(src) as tf:
        for m in tf.getmembers():
            target = os.path.realpath(os.path.join(dest, m.name))
            if not target.startswith(os.path.realpath(dest) + os.sep):
                sys.exit(f"refusing unsafe tar member: {m.name}")
        tf.extractall(dest)


def _place_weight(src, out, outdir):
    import shutil, tempfile
    low = src.lower()
    if low.endswith((".tar", ".tar.gz", ".tgz")):
        tmp = tempfile.mkdtemp(prefix="astria_tar_")
        _safe_extract_tar(src, tmp)
        found = [os.path.join(r, f) for r, _, fs in os.walk(tmp) for f in fs]
        sts = [f for f in found if f.lower().endswith(".safetensors")]
        if not sts:
            sys.exit(f"no .safetensors inside {src}; contents: {[os.path.basename(f) for f in found]}")
        main = max(sts, key=os.path.getsize)
        shutil.copyfile(main, out)
        for f in found:
            if f != main and f.lower().endswith((".safetensors", ".pt", ".bin")):
                shutil.copyfile(f, os.path.join(outdir, os.path.basename(f)))
        return out
    if low.endswith(".safetensors"):
        shutil.copyfile(src, out); return out
    if low.endswith(".ckpt"):
        ck = os.path.splitext(out)[0] + ".ckpt"; shutil.copyfile(src, ck); return ck
    sys.exit(f"unsupported file: {src} (expected .safetensors, .ckpt, or .tar/.tgz)")


def register_local(cfg, base, key_name, path):
    t = _tune(cfg, key_name)
    if not os.path.exists(path):
        sys.exit(f"file not found: {path}")
    out = _abs(base, t["lora_out"]); outdir = os.path.dirname(out); os.makedirs(outdir, exist_ok=True)
    placed = _place_weight(path, out, outdir)
    sha = hashlib.sha256(open(placed, "rb").read()).hexdigest()
    mp = _abs(base, t["meta_out"]); prev = {}
    if os.path.exists(mp):
        try: prev = json.load(open(mp, encoding="utf-8"))
        except Exception: prev = {}
    meta = _meta(cfg, t, prev.get("astria_tune_id"), trained_at=prev.get("trained_at"), ref=prev.get("ref_with_trigger"))
    meta.update(sha256=sha, filename=os.path.basename(placed), status="trained",
                source="manual download from astria.ai tune page (CKPT/TAR button)")
    _write(mp, meta); _register(cfg, base, t, meta)
    print(f"  placed -> {placed}")
    print(f"  sha256={sha[:16]}...  status=trained  registered '{t['registry_name']}'.")


# ---------------------------------------------------------------- meta / registry
def _meta(cfg, t, tune_id, trained_at=None, ref=None):
    return {
        "name": t["registry_name"], "trigger_word": cfg["shared"]["token"],
        "subject_class": cfg["shared"]["name"], "base_model": t["branch"],
        "model_type": t["model_type"], "astria_tune_id": tune_id, "trained_at": trained_at,
        "ref_with_trigger": ref, "training_images": cfg["shared"].get("expected_image_count"),
        "sha256": None, "filename": None, "status": "trained_hosted",
    }


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), indent=2)


def _register(cfg, base, t, meta):
    reg_path = _abs(base, cfg["registry"]["lora_library"])
    reg = json.load(open(reg_path, encoding="utf-8")) if os.path.exists(reg_path) else {"version": "1.0", "loras": []}
    entry = {
        "name": t["registry_name"], "filename": meta.get("filename"),
        "trigger_word": meta["trigger_word"], "strength": t["strength"],
        "base_model": t["branch"], "sha256": meta.get("sha256"),
        "astria_tune_id": meta.get("astria_tune_id"), "trained_at": meta.get("trained_at"),
        "ref_with_trigger": meta.get("ref_with_trigger"), "status": meta.get("status", "trained"),
        "notes": f"Astria {t['branch']} tune. Generate via Astria API by tune id; sync .safetensors to EC2 models/loras/ when downloaded.",
    }
    reg["loras"] = [l for l in reg.get("loras", []) if l.get("name") != entry["name"]] + [entry]
    json.dump(reg, open(reg_path, "w"), indent=2)


# ---------------------------------------------------------------- init scaffold
def init_char(args):
    if not args.char:
        sys.exit("--init requires --char <character dir>")
    if not args.token:
        sys.exit("--init requires --token <name> (the trigger word / character key)")
    tok = args.token
    klass = args.klass or "person"
    glob_ = args.image_glob or "*.jpg"
    cdir = os.path.abspath(args.char)
    for sub in ("refs", "lora", "train"):
        os.makedirs(os.path.join(cdir, sub), exist_ok=True)
    cfg = {
        "_comment": f"Astria LoRA config for character '{tok}'. Consumed by lora_gen.py. Auth: ASTRIA_API_KEY.",
        "backend": "astria", "endpoint": "https://api.astria.ai/tunes",
        "shared": {"token": tok, "name": klass, "images_dir": "../refs", "image_glob": glob_,
                   "expected_image_count": 0, "face_crop": True, "training_face_correct": False, "steps": None},
        "tunes": [
            {"key": "sdxl", "branch": "sdxl1", "model_type": "lora", "title": f"{tok}-sdxl-REPLACE_WITH_UUID",
             "strength": 0.75, "lora_out": f"../lora/{tok}-sdxl.safetensors", "meta_out": f"../lora/{tok}-sdxl.meta.json",
             "registry_name": tok},
            {"key": "flux", "branch": "flux1", "model_type": "lora", "preset": "flux-lora-portrait",
             "base_tune_id": 1504944, "title": f"{tok}-flux-REPLACE_WITH_UUID", "strength": 0.85,
             "lora_out": f"../lora/{tok}-flux.safetensors", "meta_out": f"../lora/{tok}-flux.meta.json",
             "registry_name": f"{tok}-flux"},
        ],
        "prompts_attributes": [{"text": f"{tok} {klass}, cinematic portrait, soft key light, 85mm",
                                "inpaint_faces": True, "super_resolution": True}],
        "registry": {"lora_library": "../../lora_library.json"},
    }
    cfg_path = os.path.join(cdir, "train", CONFIG_NAME)
    if os.path.exists(cfg_path) and not args.force:
        sys.exit(f"config already exists: {cfg_path} (use --force to overwrite)")
    json.dump(cfg, open(cfg_path, "w"), indent=2)
    reg_path = os.path.normpath(os.path.join(cdir, "..", "lora_library.json"))
    if not os.path.exists(reg_path):
        json.dump({"version": "1.0", "loras": []}, open(reg_path, "w"), indent=2)
    print(f"scaffolded character '{tok}' ({klass}) at {cdir}")
    print(f"  config: {cfg_path}")
    print(f"  next:   drop training images into {os.path.join(cdir, 'refs')} (matching '{glob_}'), then")
    print(f"          python {os.path.basename(__file__)} --char {args.char} --create")


# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(description="Reusable Astria character-LoRA trainer (any character).")
    ap.add_argument("--config"); ap.add_argument("--char")
    ap.add_argument("--project"); ap.add_argument("--character")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--token"); ap.add_argument("--class", dest="klass"); ap.add_argument("--image-glob", dest="image_glob")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--only", choices=["sdxl", "flux"])
    ap.add_argument("--poll", nargs=2, metavar=("KEY", "TUNE_ID"))
    ap.add_argument("--register-local", nargs=2, metavar=("KEY", "PATH"))
    a = ap.parse_args()

    if a.init:
        return init_char(a)

    cfg_path = resolve_config_path(a)
    cfg, base = load_cfg(cfg_path)

    if a.dry_run:
        imgs = _images(cfg, base)
        print(f"config: {cfg_path}")
        print(f"token='{cfg['shared']['token']}' name='{cfg['shared']['name']}'")
        for t in cfg["tunes"]:
            print(f"  tune '{t['key']}': branch={t['branch']} -> {t['lora_out']} (registry '{t['registry_name']}')")
        print(f"{len(imgs)} images matching {cfg['shared']['image_glob']}:")
        for p in imgs:
            print("  ", os.path.basename(p))
        print("(no network call made)")
    elif a.create:
        keys = [a.only] if a.only else [t["key"] for t in cfg["tunes"]]
        for k in keys:
            create_one(cfg, base, _tune(cfg, k))
    elif a.poll:
        poll(cfg, base, a.poll[0], a.poll[1])
    elif a.register_local:
        register_local(cfg, base, a.register_local[0], a.register_local[1])
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
