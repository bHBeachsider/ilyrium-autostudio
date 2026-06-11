"""Taste judge: score a Nast concept against a small rubric; decide whether to revise once."""
import json
import urllib.request

from . import config

NAST_RUBRIC = (
    "Score 1-5 how well this concept captures Thomas Nast's editorial taste:\n"
    "- A single dominant allegory/visual metaphor (Tammany Tiger, the Ring, a bloated boss).\n"
    "- Heavy-handed moral framing with a clear villain and victim.\n"
    "- Concrete, labeled symbols rather than abstract description.\n"
    "- Reads as a 19th-century Harper's Weekly cartoon, not a modern comic."
)


def build_judge_prompt(concept: dict) -> str:
    return (
        NAST_RUBRIC + "\n\n"
        "CONCEPT:\n"
        f"allegory_rationale: {concept.get('allegory_rationale', '')}\n"
        f"image_prompt: {concept.get('image_prompt', '')}\n\n"
        "Respond ONLY with JSON: {\"score\": <float 1-5>, \"rationale\": <str>}."
    )


def parse_verdict(raw: str) -> dict:
    """Extract {score: float(1-5), rationale: str}. Raises ValueError if no score found."""
    if not raw or "{" not in raw or "}" not in raw:
        raise ValueError("no JSON verdict in judge output")
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON verdict: {e}") from e
    if "score" not in obj:
        raise ValueError("verdict missing score")
    score = max(1.0, min(5.0, float(obj["score"])))
    return {"score": score, "rationale": str(obj.get("rationale", "") or "")}


def should_revise(verdict: dict, threshold: float = None) -> bool:
    thr = config.JUDGE_THRESHOLD if threshold is None else threshold
    return float(verdict.get("score", 0.0)) < thr


def score_concept(concept: dict, model: str = None, timeout: int = 120) -> dict:
    """Network call to OpenRouter. Returns parse_verdict(...). Requires OPENROUTER_API_KEY."""
    import os
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set; cannot run the taste judge")
    body = json.dumps({"model": model or config.JUDGE_MODEL,
                       "messages": [{"role": "user", "content": build_judge_prompt(concept)}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read())["choices"][0]["message"]["content"]
    return parse_verdict(raw)
