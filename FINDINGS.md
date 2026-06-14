# FINDINGS — Auto-Studio RSI Loop Registry (L0)

Append-only registry of classified failures and signals worth remembering — the
**Finding** primitive of the RSI loop (RSI_LOOP_BLUEPRINTS §2.2). One row per
class. The engine of the whole system is the
`detected_at_layer` / `should_have_been_prevented_at_layer` pair: it converts
every incident into a statement about which gate was missing, and the median
`detected_at_layer` moving left (toward pre-PR / harness) is the cleanest single
health metric for the architecture.

**Invariant (CF-5).** Every recurring Finding (frequency ≥ 3) must terminate in
a durable artifact — a test, gate, validator, prompt patch, policy, or process
change — or an explicit accepted-risk record. No third state. A Finding becomes
a [Candidate](.github/PULL_REQUEST_TEMPLATE.md); merge after gates + human
approval is its Release.

**Layers** (left = earlier = better): `harness` → `pre_commit` → `ci` →
`render_runtime` → `human_review` → `production`.

**Fields:** `finding_id`, `severity` (low/med/high/critical), `frequency`,
`root_cause`, `detected_at_layer`, `should_have_been_prevented_at_layer`,
`remediation_type` (test/gate/validator/prompt/policy/process/accepted_risk),
`status` (open/mitigated/closed/accepted_risk).

---

## F-0001 — HTTP 400 from ComfyUI submit (missing/unset comfy URL)

- **severity:** high
- **frequency:** 3
- **root_cause:** Render submission posted to an empty or malformed ComfyUI
  base URL (no `--comfy` / unset `comfy_url` in the manifest), producing an
  HTTP 400 at `/prompt` with no actionable message. The submit path was raw
  `urllib` scattered across scripts, so there was no single place to validate
  the URL or record the failed request for diagnosis.
- **detected_at_layer:** render_runtime
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** gate
- **status:** mitigated
- **durable_artifact:** All ComfyUI HTTP now flows through
  `harness/run.py` (`comfy_submit_prompt` / `comfy_*`), which records the
  request/response on the trace — a 400 is now captured with its URL and
  payload rather than vanishing. The lint gate
  (`harness/lint_no_raw_sdk.py`) forbids any direct ComfyUI POST outside the
  harness, so the scattered-submit root cause cannot recur in new code.
- **next_candidate:** add an explicit pre-submit URL reachability check
  (`/system_stats` ping) in the harness that fails fast with a clear message.

## F-0002 — LoadImage node rejection (keyframe absent in ComfyUI/input)

- **severity:** high
- **frequency:** 3
- **root_cause:** The Wan I2V graph's `LoadImage` node rejected a keyframe
  filename that had not been uploaded into `ComfyUI/input` before submit (or
  was referenced by a path rather than the uploaded basename). Upload and
  submit were separate, unordered steps.
- **detected_at_layer:** render_runtime
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** process
- **status:** open
- **durable_artifact (partial):** The `shot_renderer` agent prompt encodes the
  ordering invariant (upload keyframe → reference basename → submit), and
  `harness.run.comfy_upload_image` is the single sanctioned upload path so the
  recorded trace shows whether an upload preceded the submit.
- **next_candidate:** a harness pre-submit assertion that every `LoadImage`
  input in the graph resolves to a filename already uploaded this session;
  fail before submit with the offending node id.

## F-0003 — UTF-8 BOM corruption from PowerShell file writes

- **severity:** med
- **frequency:** 3
- **root_cause:** `Set-Content` / `Out-File` on Windows prepend a UTF-8 BOM and
  may emit CRLF, corrupting JSON/YAML config and silently changing file bytes —
  which would, in turn, change any naive content hash of an agent config and
  make `agent_version_id` unstable across machines/editors.
- **detected_at_layer:** ci
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** validator
- **status:** mitigated
- **durable_artifact:** `harness/config_hash.py` canonicalises bytes before
  hashing (strips a leading UTF-8 BOM, normalises CRLF→LF), so BOM/line-ending
  noise cannot perturb `agent_version_id` or `config_hash`; a regression test
  (`tests/test_harness.py::test_config_hash_bom_and_crlf_insensitive`) locks
  this. Repo policy (CLAUDE.md) mandates Python `write_text(encoding="utf-8")`
  for multi-line writes, never PowerShell here-strings.
- **next_candidate:** a pre-commit check rejecting a BOM in any tracked
  `.json` / `.yaml` / `.md` under `agents/`, `evals/`, `policies/`.

## F-0004 — Untraced model/render execution (raw SDK + direct ComfyUI API)

- **severity:** high
- **frequency:** 13
- **root_cause:** Pre-harness code imported model SDKs directly
  (`anthropic`, `google.genai`) and posted to the ComfyUI API with raw
  `urllib`, so invocations carried no `agent_version_id`, no cost/latency
  accounting, no recorded tool I/O for replay, and no trace. Untraced
  execution was the default, not the exception.
- **detected_at_layer:** harness
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** gate
- **status:** open (strangler migration in progress)
- **durable_artifact:** `harness/lint_no_raw_sdk.py` fails any NEW file outside
  `harness/` that imports a model SDK or hits the ComfyUI API; the 13
  pre-existing violators are a frozen WARN baseline that only shrinks (each
  migration retires its baseline entry in the same PR — the strangler rule).
  `batch_render.py`, `shot_to_comfy.py`, and `bible_to_shotspecs.py` are
  already migrated.
- **next_candidate:** migrate `apps/auto-studio/stage_agents.py` to
  `harness.run.run_model()` and remove it from the baseline (highest-traffic
  remaining violator).

## F-0005 — Dry-run render emits schema-invalid provenance (null comfyui_version)

- **severity:** low
- **frequency:** 1
- **root_cause:** `batch_render --dry-run` (FakeRenderer) never contacts a box,
  so it never fills `engine.comfyui_version`; if the manifest also leaves it
  null, `provenance_record.schema.json` rejects the record
  (`['engine','comfyui_version']: None is not of type 'string'`) and the whole
  dry-run aborts. Only the LIVE path fills the version from `/system_stats`.
  Surfaced while building the ILY-203 replay acceptance corpus.
- **detected_at_layer:** render_runtime
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** accepted_risk
- **status:** accepted_risk
- **note:** Worked around by pinning `engine.comfyui_version` in the dry-run
  manifest. Not yet recurring (freq 1), so no durable fix is mandated.
- **next_candidate:** have the dry-run path stamp a sentinel
  `engine.comfyui_version = "dry-run"` when unset, so dry-runs are always
  schema-valid without manual manifest edits.
