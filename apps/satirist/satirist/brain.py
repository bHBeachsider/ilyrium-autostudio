"""Nast Brain client: build the prompt, call Ollama, parse the JSON concept."""
import json
import urllib.request

from . import config

_REQUIRED = ("allegory_rationale", "image_prompt")


def build_prompt(event_summary: str, revise_hint: str = "") -> str:
    """The Brain was trained to map an event -> {allegory_rationale, image_prompt}."""
    base = (
        "Event: " + event_summary.strip() + "\n"
        "Respond ONLY with JSON: {\"allegory_rationale\": str, \"image_prompt\": str}. "
        "image_prompt must be a 19th-century Harper's Weekly wood-engraving cartoon description."
    )
    if revise_hint:
        base += "\nRevision note: " + revise_hint.strip()
    return base


def parse_brain_output(raw: str) -> dict:
    """Extract the JSON object from the Brain's response text. Raises ValueError if absent/invalid."""
    if not raw or "{" not in raw or "}" not in raw:
        raise ValueError("no JSON object in Brain output")
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in Brain output: {e}") from e
    for k in _REQUIRED:
        if k not in obj or not str(obj[k]).strip():
            raise ValueError(f"Brain output missing required key: {k}")
    return {k: obj[k] for k in _REQUIRED} | (
        {"caption": obj["caption"]} if obj.get("caption") else {})


def ideate(event_summary: str, brain_url: str = None, revise_hint: str = "", timeout: int = 120) -> dict:
    """Call the Ollama-served Nast Brain; return the parsed concept dict. Network call."""
    url = (brain_url or config.BRAIN_URL).rstrip("/") + "/api/generate"
    body = json.dumps({"model": config.BRAIN_MODEL,
                       "prompt": build_prompt(event_summary, revise_hint),
                       "stream": False}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return parse_brain_output(resp.get("response", ""))
