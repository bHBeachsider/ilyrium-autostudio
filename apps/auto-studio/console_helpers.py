"""
console_helpers.py — support layer for the production console in app.py.

Everything here is deliberately defensive: the console must render even when
AWS creds are missing, the box is stopped, or the tunnel is down. Backend
failures are returned as data (never raised into the Streamlit script), and
`ec2_session.status()` / `is_comfyui_up()` are cached ~5s so reruns don't
hammer AWS describe-instances.
"""

import os
import re
import json
import shutil
import subprocess

import streamlit as st

_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# Box / ComfyUI status (cached ~5s so Streamlit reruns don't spam AWS)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=5, show_spinner=False)
def box_status() -> dict:
    """ec2_session.status(), errors folded in as state='error' (never raises)."""
    try:
        import ec2_session
        return ec2_session.status()
    except Exception as e:
        return {"state": "error", "error": str(e), "instance_id": None, "public_ip": None}


@st.cache_data(ttl=5, show_spinner=False)
def comfy_up() -> bool:
    """is_comfyui_up() through the tunnel; False on any failure (never raises)."""
    try:
        import ec2_session
        return bool(ec2_session.is_comfyui_up())
    except Exception:
        return False


def clear_status_cache():
    box_status.clear()
    comfy_up.clear()


# --------------------------------------------------------------------------- #
# box.ps1 driver (tunnel open/close) — fire-and-forget subprocess
# --------------------------------------------------------------------------- #
def _box_ps1_path() -> str:
    return os.path.join(_APP_DIR, "cli", "box.ps1")


def run_box_verb(verb: str) -> str:
    """Launch `cli/box.ps1 <verb>` detached (pwsh preferred, powershell fallback).

    Non-blocking by design — the UI reflects the outcome via status polling.
    Returns a short human-readable confirmation; raises on setup problems
    (missing script / no PowerShell) so the caller can st.warning them.
    """
    ps1 = _box_ps1_path()
    if not os.path.exists(ps1):
        raise FileNotFoundError(f"box.ps1 not found at {ps1}")
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        raise RuntimeError("Neither pwsh nor powershell is on PATH.")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, verb],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags, cwd=_APP_DIR,
    )
    return f"box.ps1 {verb} launched ({os.path.basename(exe)}) — status will update shortly."


# --------------------------------------------------------------------------- #
# Model catalog (data-driven from model_registry.json — never hardcoded ids)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60, show_spinner=False)
def comfyui_model_ids() -> list:
    """All provider=='comfyui' ids from the registry, e.g. ['comfyui', 'comfyui:zimage', ...]."""
    try:
        import model_select
        reg = model_select.load_registry()
        return [m["id"] for m in reg.get("models", []) if m.get("provider") == "comfyui"]
    except Exception:
        return []


def comfyui_short_ids() -> list:
    """The on-box short ids (registry ids minus the 'comfyui:' prefix; bare 'comfyui' excluded)."""
    return [i.split(":", 1)[1] for i in comfyui_model_ids() if ":" in i]


# The non-comfyui video/other engines the per-shot renderer already supported.
# (These are engine routes in producer.render_shot, not registry entries.)
VIDEO_ENGINES = ["grok-imagine", "veo3", "veo3.1", "kling", "ue", "keyframe"]


def render_model_options() -> list:
    """Full per-shot model list: existing video engines + registry comfyui:* ids."""
    return VIDEO_ENGINES[:4] + comfyui_model_ids() + VIDEO_ENGINES[4:]


def is_comfy_model(model: str) -> bool:
    return bool(model) and model.split(":", 1)[0] == "comfyui"


def short_model_id(model_spec: str) -> str:
    """Registry id -> on-box short id: 'comfyui:flux2' -> 'flux2'. The bare
    capability entry 'comfyui' (no suffix) maps to the engine's default model
    ('zimage' — media/comfyui_engine.DEFAULT_MODEL)."""
    spec = (model_spec or "").strip()
    if ":" in spec:
        return spec.split(":", 1)[1]
    if spec in ("", "comfyui"):
        try:
            from media import comfyui_engine as ce
            return ce.DEFAULT_MODEL
        except Exception:
            return "zimage"
    return spec


def resolve_model_id(text: str):
    """Resolve user input ('flux2' or 'comfyui:flux2') to a full registry id,
    or None if it isn't a known comfyui model."""
    ids = comfyui_model_ids()
    t = (text or "").strip()
    if t in ids:
        return t
    if f"comfyui:{t}" in ids:
        return f"comfyui:{t}"
    return None


def prompt_hint(model_spec: str) -> str:
    """The gen_prompt style hint for a model — the registry recipe's 'hint'
    field when present, else inferred from the short id."""
    try:
        from media import comfyui_engine as ce
        entry = ce.load_model(model_spec)
        h = (entry.get("recipe") or {}).get("hint")
        if h:
            return h
    except Exception:
        pass
    return "flux" if "flux" in short_model_id(model_spec).lower() else "z-image"


# --------------------------------------------------------------------------- #
# Studio Chat command parsing (':'-prefixed REPL commands; plain = prompt)
# --------------------------------------------------------------------------- #
CHAT_COMMANDS = ("new", "model", "region", "denoise", "seed", "help")


def parse_chat_command(text: str):
    """Parse a Studio Chat message -> (cmd, arg).

    cmd is one of CHAT_COMMANDS, 'unknown' (':'-prefixed but unrecognized),
    or None (plain text — a generate/edit prompt, returned as arg)."""
    t = (text or "").strip()
    if not t.startswith(":"):
        return None, t
    parts = t[1:].split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""
    if cmd not in CHAT_COMMANDS:
        return "unknown", t
    return cmd, arg


# --------------------------------------------------------------------------- #
# Stage → tool grouping (authoring map; the tool LIST itself comes from
# execute_tool('list_tools') at runtime, so new tools self-surface)
# --------------------------------------------------------------------------- #
STAGE_TOOL_MAP = [
    ("1 · Brief", ["scaffold_project", "get_project_state", "recommend_models"]),
    ("2 · Script", ["set_script"]),
    ("3 · Storyboard", ["recommend_models", "list_models"]),
    ("4 · Asset Gen", ["generate_first_cut", "regenerate_shot", "select_take"]),
    ("5 · Edit", ["edit_image", "inpaint_image", "edit_shot"]),
    ("6 · Review", ["run_release_qa", "run_style_validation"]),
    ("7 · Assembly", ["reassemble_cut", "generate_music_bed", "set_audio_duck"]),
    ("8 · Rights & Delivery", ["get_release_gate", "get_approval_queue", "approve_release"]),
    ("Utility", ["list_tools", "list_models", "get_tool_manual"]),
]

# Tools whose backend is the ComfyUI box — gated on comfy_up().
COMFY_ONLY_TOOLS = {"edit_image", "inpaint_image"}
# Tools that call paid/slow generation backends — run inside st.status.
SLOW_TOOLS = {"generate_first_cut", "regenerate_shot", "edit_shot", "edit_image",
              "inpaint_image", "generate_music_bed", "reassemble_cut"}


@st.cache_data(ttl=300, show_spinner=False)
def load_tool_menu() -> list:
    """Runtime tool menu: names+summaries from execute_tool('list_tools'),
    joined with each tool's input_schema from studio_tools.TOOLS."""
    from studio_tools import execute_tool, TOOLS
    res = execute_tool("list_tools", {}, None)
    data = json.loads(res["content"])
    schemas = {t["name"]: t for t in TOOLS}
    menu = []
    for row in data.get("tools", []):
        tdef = schemas.get(row["name"], {})
        menu.append({
            "name": row["name"],
            "summary": row.get("summary", ""),
            "description": tdef.get("description", row.get("summary", "")),
            "input_schema": tdef.get("input_schema", {"type": "object", "properties": {}}),
        })
    return menu


def group_tools_by_stage(menu: list) -> list:
    """[(stage_label, [tool_dict, ...]), ...] per STAGE_TOOL_MAP; runtime tools
    not in the authoring map land in Utility so nothing is ever hidden."""
    by_name = {t["name"]: t for t in menu}
    mapped = set()
    groups = []
    for label, names in STAGE_TOOL_MAP:
        tools = [by_name[n] for n in names if n in by_name]
        mapped.update(n for n in names if n in by_name)
        groups.append((label, tools))
    leftovers = [t for t in menu if t["name"] not in mapped]
    if leftovers:
        groups[-1] = (groups[-1][0], groups[-1][1] + leftovers)
    return groups


# --------------------------------------------------------------------------- #
# Ad-project discovery (project.json dirs under outputs/) for the tool console
# --------------------------------------------------------------------------- #
def list_ad_project_dirs() -> list:
    out = []
    if os.path.isdir("outputs"):
        for name in sorted(os.listdir("outputs"), reverse=True):
            d = os.path.join("outputs", name)
            if os.path.isfile(os.path.join(d, "project.json")):
                out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Generic input_schema -> Streamlit widgets
# --------------------------------------------------------------------------- #
_LONG_TEXT_HINTS = ("prompt", "change", "scenes", "message", "reason", "voiceover")


def schema_widgets(tool: dict, key_prefix: str, enum_overrides: dict = None) -> dict:
    """Render widgets for a tool's input_schema; return the tool_input dict
    (empty/optional values omitted). Call inside an st.form.

    enum_overrides: {prop_name: [options]} to replace a schema enum with a
    data-driven list (e.g. registry comfyui model ids)."""
    schema = tool.get("input_schema") or {}
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    enum_overrides = enum_overrides or {}
    values = {}

    for pname, spec in props.items():
        wkey = f"{key_prefix}_{pname}"
        label = pname + (" *" if pname in required else "")
        help_txt = spec.get("description")
        ptype = spec.get("type")
        enum = enum_overrides.get(pname, spec.get("enum"))

        if enum:
            opts = list(enum) if pname in required else ["(default)"] + list(enum)
            sel = st.selectbox(label, opts, key=wkey, help=help_txt)
            if sel != "(default)":
                values[pname] = sel
        elif ptype == "boolean":
            values[pname] = st.checkbox(label, key=wkey, help=help_txt)
        elif ptype in ("integer", "number"):
            raw = st.text_input(label, key=wkey, help=help_txt,
                                placeholder="integer" if ptype == "integer" else "number")
            if raw.strip():
                try:
                    values[pname] = int(raw) if ptype == "integer" else float(raw)
                except ValueError:
                    values[f"__error_{pname}"] = f"'{pname}' must be a {ptype} (got '{raw}')."
        elif ptype == "array":
            raw = st.text_area(label, key=wkey, height=140,
                               help=(help_txt or "") + "  — enter a JSON array.",
                               placeholder='e.g. [{"scene_number": 1, ...}] or ["a", "b"]')
            if raw.strip():
                try:
                    values[pname] = json.loads(raw)
                except Exception as e:
                    values[f"__error_{pname}"] = f"'{pname}' is not valid JSON: {e}"
        else:  # string (and anything unmapped)
            long = any(h in pname.lower() for h in _LONG_TEXT_HINTS) or len(help_txt or "") > 120
            if long:
                raw = st.text_area(label, key=wkey, height=90, help=help_txt)
            else:
                raw = st.text_input(label, key=wkey, help=help_txt)
            if raw.strip():
                values[pname] = raw.strip()
    return values


def split_form_errors(values: dict):
    """Separate widget-level parse errors from the clean tool_input."""
    errors = [v for k, v in values.items() if k.startswith("__error_")]
    clean = {k: v for k, v in values.items() if not k.startswith("__error_")}
    return clean, errors


def missing_required(tool: dict, tool_input: dict) -> list:
    req = set((tool.get("input_schema") or {}).get("required") or [])
    return sorted(r for r in req if r not in tool_input or tool_input[r] in ("", None))


# --------------------------------------------------------------------------- #
# Tool result rendering
# --------------------------------------------------------------------------- #
_IMG_PATH_RE = re.compile(r"[\w:./\\-]+\.(?:png|jpg|jpeg|webp)", re.IGNORECASE)


def show_tool_result(content: str):
    """Pretty-print a tool result; JSON gets st.json, and any produced image
    paths that exist on disk are previewed inline."""
    try:
        st.json(json.loads(content))
        return
    except Exception:
        pass
    st.code(content, language=None)
    for m in _IMG_PATH_RE.findall(content or ""):
        if os.path.isfile(m):
            st.image(m, caption=m, width=360)
