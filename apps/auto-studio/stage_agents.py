"""
Per-stage agent surface — an ideation/refinement collaborator for every component
of the project scaffold.

Each pipeline stage (00_bible … 10_keyart) gets a specialized agent with the right
persona, grounded in the project's Style Kernel + casting canon + the stage's
template/gate (from scaffold.STAGES). The agent can READ any project file for
context and WRITE draft files into its own stage folder — so you can ideate and
refine a stage in conversation, and it persists the result.

Autonomy = A1 (draft/propose; human accepts). Agents never delete files, never
approve for release, and never contradict the kernel or casting canon.

Surfaces: callable from studio_tools / the MCP server (`stage_ideate`) and any UI.
"""

import os

import scaffold  # reuse STAGES (folder, title, purpose, produce, template, gate)

MODEL = "claude-sonnet-5"

# folder -> (persona name, upstream stage folders it should read for context)
PERSONAS = {
    "00_bible":        ("Story Architect", []),
    "01_script":       ("Screenwriter", ["00_bible"]),
    "02_characters":   ("Casting & Character Director", ["00_bible"]),
    "03_environments": ("Art Director", ["00_bible", "01_script"]),
    "04_keyframes":    ("Storyboard Artist", ["01_script", "02_characters", "03_environments"]),
    "05_shots":        ("Cinematographer", ["01_script", "04_keyframes"]),
    "06_voice":        ("Voice Director", ["00_bible", "01_script", "02_characters"]),
    "07_music":        ("Music Supervisor", ["00_bible", "01_script"]),
    "08_edit":         ("Editor", ["01_script", "05_shots"]),
    "09_qa":           ("QA & Continuity Supervisor", ["02_characters"]),
    "10_keyart":       ("Key-Art Director", ["00_bible", "02_characters"]),
}

_STAGE_BY_FOLDER = {s[0]: s for s in scaffold.STAGES}


def list_stage_agents() -> list:
    """(folder, persona, title) for every stage agent."""
    return [(f, PERSONAS[f][0], _STAGE_BY_FOLDER[f][1]) for f in PERSONAS if f in _STAGE_BY_FOLDER]


def _safe_join(project_dir: str, rel: str) -> str:
    full = os.path.normpath(os.path.join(project_dir, rel))
    if not full.startswith(os.path.normpath(project_dir)):
        raise ValueError("Path escapes the project directory.")
    return full


def _kernel_block(project_dir: str) -> str:
    path = os.path.join(project_dir, "style_kernel.json")
    if not os.path.exists(path):
        return "(no style_kernel.json found in project root)"
    import json
    k = json.load(open(path, encoding="utf-8"))
    canon = "\n".join(f"  - {w}: {d}" for w, d in (k.get("casting_canon") or {}).items())
    return (f"LOOK: {k.get('look','')}\nREGISTER: {k.get('register','')}\n"
            f"NEGATIVES: {k.get('negatives','')}\nLEGAL RULE: {k.get('legal_rule','')}\n"
            f"CASTING CANON:\n{canon or '  (none)'}")


def _categories_block(stage_folder: str) -> str:
    """The stage's information-category checklist from prompt_taxonomy.json (source-tagged).
    Fail-safe: returns '' if the taxonomy/kit isn't available."""
    try:
        import prompt_kit
        tax = prompt_kit.load_taxonomy()
        rows = []
        for key, c, required in prompt_kit.stage_categories(tax, stage_folder):
            tag = c["source"].upper()
            auto = " [auto — do NOT retype]" if c["source"] in ("kernel", "derived") else ""
            rows.append(f"  - {'★' if required else '·'} {c['label']} ({tag}){auto}")
        if not rows:
            return ""
        return ("INFORMATION CATEGORIES TO COVER (★ = required by the gate; KERNEL/DERIVED are "
                "supplied by the pipeline — reference them, never retype them):\n" + "\n".join(rows))
    except Exception:
        return ""


def _tool_manuals_line() -> str:
    """Compact hint pointing the agent at get_tool_manual(...). Fail-safe."""
    try:
        import tool_knowledge
        return tool_knowledge.index_line()
    except Exception:
        return ""


def build_system_prompt(stage_folder: str, project_dir: str) -> str:
    persona, upstream = PERSONAS.get(stage_folder, ("Studio Collaborator", []))
    s = _STAGE_BY_FOLDER.get(stage_folder)
    title = s[1] if s else stage_folder
    purpose, produce, template, gate = (s[2], s[3], s[4], s[5]) if s else ("", "", "", "")
    upstream_note = (", ".join(upstream) + " (read these for continuity)") if upstream else "none"

    return f"""You are the **{persona}** for an Ilyrium film production — the ideation and refinement \
collaborator for the **{title}** stage. You help the human develop and sharpen THIS stage's content.

STAGE PURPOSE: {purpose}
WHAT THIS STAGE PRODUCES: {produce}
TEMPLATE TO FOLLOW: {template}
GATE THIS STAGE MUST PASS: {gate}

{_categories_block(stage_folder)}

{_tool_manuals_line()}

PRODUCTION VALUES (the Style Kernel — never contradict these):
{_kernel_block(project_dir)}

UPSTREAM CONTEXT: {upstream_note}. Use read_project_file to pull the kernel, casting canon, or any \
upstream stage's files before proposing, so your ideas stay continuous with the rest of the production.

HOW YOU WORK:
- Ideate and refine in conversation. Offer concrete options, push the creative, ask only the few \
questions that change the output.
- When the human approves a draft, persist it with write_stage_file into THIS stage's folder.
- Autonomy A1: you draft and propose; the human accepts. You NEVER delete files, NEVER approve \
anything for release, and NEVER contradict the casting canon, the legal no-likeness rule, or the \
kernel look/register.
- Keep replies concrete and short. Reference the template and the gate so the human always knows \
what "done" looks like for this stage."""


def _tools():
    return [
        {"name": "read_project_file",
         "description": "Read any file in the project for context (e.g. style_kernel.json, "
                        "02_characters/CASTING_CANON.md, 01_script/scenes.json, an upstream stage's files).",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
        {"name": "list_project_files",
         "description": "List the files that exist in the project so you know what context is available.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "write_stage_file",
         "description": "Persist a draft into THIS stage's folder (only when the human approves it).",
         "input_schema": {"type": "object",
                          "properties": {"filename": {"type": "string"}, "content": {"type": "string"}},
                          "required": ["filename", "content"]}},
    ]


def _exec_tool(name, args, stage_folder, project_dir):
    if name == "list_project_files":
        out = []
        for root, _dirs, files in os.walk(project_dir):
            for fn in files:
                out.append(os.path.relpath(os.path.join(root, fn), project_dir).replace("\\", "/"))
        return "\n".join(sorted(out)) or "(empty)"
    if name == "read_project_file":
        p = _safe_join(project_dir, args["path"])
        if not os.path.exists(p):
            return f"(not found: {args['path']})"
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()[:20000]
    if name == "write_stage_file":
        # Resolve the stage's STABLE key to its canonical home path (canonical
        # scaffold v2), so drafts land in e.g. 01_development/bible, not a bare key.
        rel_dir = scaffold.STAGE_PATHS.get(stage_folder, stage_folder)
        d = os.path.join(project_dir, rel_dir)
        os.makedirs(d, exist_ok=True)
        p = _safe_join(project_dir, os.path.join(rel_dir, os.path.basename(args["filename"])))
        with open(p, "w", encoding="utf-8") as f:
            f.write(args["content"])
        return f"Wrote {rel_dir}/{os.path.basename(args['filename'])}."
    return f"Unknown tool: {name}"


def run_stage_agent(stage_folder: str, project_dir: str, messages: list,
                    progress_cb=None, max_iters: int = 8) -> dict:
    """Run one turn of the stage agent's tool-use loop. `messages` is the running
    Anthropic-format conversation. Returns {messages, assistant_text}."""
    import anthropic
    if stage_folder not in PERSONAS:
        raise ValueError(f"Unknown stage '{stage_folder}'. Known: {list(PERSONAS)}")

    client = anthropic.Anthropic()
    system = build_system_prompt(stage_folder, project_dir)
    tools = _tools()

    for _ in range(max_iters):
        resp = client.messages.create(model=MODEL, max_tokens=3000, system=system,
                                       tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
            return {"messages": messages, "assistant_text": text or "(done)"}
        results = []
        for tu in tool_uses:
            if progress_cb:
                progress_cb(f"🛠️ {tu.name}")
            try:
                content = _exec_tool(tu.name, dict(tu.input), stage_folder, project_dir)
            except Exception as e:
                content = f"{type(e).__name__}: {e}"
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": content})
        messages.append({"role": "user", "content": results})

    return {"messages": messages, "assistant_text": "(stopped after max tool steps — ask me to continue.)"}
