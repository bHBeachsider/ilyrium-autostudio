# Stage 10 — Continuity / QA / Governance

**Canonical home:** `08_qa/`  ·  **Stage key:** `09_qa`

**Purpose.** The enforceable gate. Run the checklist on every render before approval.

**Produce (put your files in this folder):**
qa_log.md (per-shot checklist results).

**Template / how to make it:**
See ../QA_CHECKLIST.md. Fail -> regenerate with the matching fix from the kernel's failure_fixes (e.g. mauve-reads-lavender, acting-at-camera).

**Gate (must pass before this stage is done):**
LEGAL GATE: reject any render resembling a real public figure. Casting canon + motifs + performance register + negatives all pass before approvedForRelease (enforced by the release gate; releases live in ../00_admin/rights_releases/).

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="09_qa", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
