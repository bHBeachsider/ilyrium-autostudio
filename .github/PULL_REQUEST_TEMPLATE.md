<!--
RSI loop Candidate template (ILY-203 task 14; RSI_LOOP_BLUEPRINTS §2.2).
A PR is the Candidate primitive: a proposed durable change sourced from one or
more Findings. Merge after gates + human approval IS the Release record.
The optimization plane proposes; only the merge (with approval) mutates
production artifacts. Fill every section — the admission/release gates and the
human reviewer read them.
-->

## Source findings
<!-- Which FINDINGS.md row(s) does this close or advance? e.g. F-0004 -->
- Source finding IDs:

## Target artifact
<!-- Tick exactly the artifact class(es) this PR changes. Determines which
     gates apply (changes to prompt/tool/routing/validator/gate/policy/taxonomy
     go through the release_gate path). -->
- [ ] prompt (`agents/<name>/<version>/prompt.md`)
- [ ] tools (`agents/<name>/<version>/tools.yaml`)
- [ ] routing (`agents/<name>/<version>/routing.yaml` or `policies/routing.yaml`)
- [ ] validator / rubric (`evals/rubrics/`, `style_validator.py`)
- [ ] test (`tests/`)
- [ ] gate (`harness/lint_no_raw_sdk.py`, `harness/admission_gate.py`, hooks)
- [ ] other (specify):

## Patch summary
<!-- What changed and why, in 2-5 sentences. Reference the agent version(s)
     touched and whether a new agent version directory was created. -->

## Expected improvement
<!-- The measurable claim. e.g. "median detected_at_layer shifts from
     render_runtime to harness for F-0001" or "style_score on the
     shot_spec_generator golden set rises from X to Y". State the metric. -->

## Evidence
<!-- Required by the release gate. Paste / link: -->
- [ ] `python -m pytest tests/ -q` passes
- [ ] `python harness/lint_no_raw_sdk.py --all` clean (no NEW baseline entries)
- [ ] `python harness/admission_gate.py` admits all active agents
- [ ] If an agent config changed: manifest restamped
      (`python harness/config_hash.py <dir> --write-manifest`) and a new
      version directory created if behaviour changed
- [ ] If applicable: `python harness/replay.py` delta report attached
      (challenger ≥ champion on the golden set)

## Regression risk
<!-- What could this break? Which traces / projects are affected? -->

## Rollback reference
<!-- How to revert. For agents-as-data this is a pointer move: the prior
     version directory + manifest. Name it. -->
- Rollback target:

---
<!-- Release record: on merge with approval, this PR is the Release. The
     reviewer's approval + the green gates above constitute the evidence_refs
     and approved_by of the Release primitive. -->
