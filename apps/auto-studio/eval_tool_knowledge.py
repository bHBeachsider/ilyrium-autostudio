"""
eval_tool_knowledge — measure the grounding value of the tool manuals.

Two modes:
  - DETERMINISTIC (default, no API): for a set of (tool, question, expected-fact) cases, check that
    the tool's manual actually carries the fact the agent would otherwise have to guess. This proves
    the manual supplies grounding; it's the fast, reproducible proxy.
  - LLM A/B (optional, --llm, needs ANTHROPIC_API_KEY): ask the model each question WITHOUT the
    manual then WITH it in context, and grade whether the answer contains the expected fact. This is
    the rigorous "does it change the answer" measure.

Run:  python eval_tool_knowledge.py            # deterministic
      python eval_tool_knowledge.py --llm      # A/B with the model
"""
import sys
import tool_knowledge as tk

# (tool, question a real agent would face, a substring that proves the grounded answer)
CASES = [
    ("tensorart", "What host do TensorArt jobs POST to?", "ap-east-1.tensorart.cloud"),
    ("tensorart", "May the agent top up TAMS credits itself?", "payment"),
    ("runway", "How do you cancel a Runway task?", "DELETE"),
    ("resolve", "Does Resolve render by index or job id?", "job id"),
    ("ffmpeg", "What loudness target does delivery normalize to?", "-14"),
    ("comfyui", "What route queues a ComfyUI workflow?", "/prompt"),
    ("elevenlabs", "Can the agent clone a real person's voice freely?", "consent"),
    ("igniter", "Can the agent drive Igniter via an API?", "no automatable api"),
    ("ue", "Should the agent guess Unreal MRQ class names?", "do not"),
    ("blender", "How does the agent render a Blender scene?", "--background"),
]


def deterministic():
    rows, passed = [], 0
    for tool, q, fact in CASES:
        manual = tk.get(tool).lower()
        ok = fact.lower() in manual
        passed += ok
        rows.append((tool, q, fact, ok))
    print("GROUNDING EVAL (deterministic) — does each manual carry the fact the agent needs?\n")
    for tool, q, fact, ok in rows:
        print(f"  [{'PASS' if ok else 'MISS'}] {tool:12} expects '{fact}'  —  {q}")
    print(f"\n{passed}/{len(CASES)} facts present in the manuals "
          f"(these are exactly the points an un-grounded agent would risk hallucinating).")
    return passed == len(CASES)


def llm_ab():
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — skipping LLM A/B (deterministic result above stands).")
        return
    import anthropic
    client = anthropic.Anthropic()

    def ask(q, context=None):
        sysmsg = "You operate creative tools in a film pipeline. Answer in one short sentence."
        if context:
            sysmsg += "\n\nTOOL MANUAL:\n" + context
        r = client.messages.create(model="claude-sonnet-5", max_tokens=120, system=sysmsg,
                                   messages=[{"role": "user", "content": q}])
        return "".join(b.text for b in r.content if getattr(b, "type", None) == "text")

    base_hits = manual_hits = 0
    print("\nLLM A/B — same question, WITHOUT vs WITH the manual in context:\n")
    for tool, q, fact in CASES:
        a0 = ask(q)
        a1 = ask(q, tk.get(tool))
        b = fact.lower() in a0.lower(); m = fact.lower() in a1.lower()
        base_hits += b; manual_hits += m
        print(f"  {tool:12} without:{'✓' if b else '✗'}  with:{'✓' if m else '✗'}   ({q})")
    print(f"\ncorrect WITHOUT manual: {base_hits}/{len(CASES)} | WITH manual: {manual_hits}/{len(CASES)} "
          f"| lift: +{manual_hits - base_hits}")


if __name__ == "__main__":
    ok = deterministic()
    if "--llm" in sys.argv:
        llm_ab()
    sys.exit(0 if ok else 1)
