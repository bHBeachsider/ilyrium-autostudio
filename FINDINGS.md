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
- **frequency:** 4
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
- **recurrence (2026-10-12, CRLF variant):** the sanctioned fix itself leaks.
  Python `Path.write_text(..., encoding="utf-8")` in text mode translates `\n`
  to `\r\n` on Windows, so appending one line to `.gitignore` and `.env` during
  the FilmCraft Phase 0 setup rewrote both files as CRLF. Caught by inspecting
  bytes after the write (harness), restored to LF the same session. Policy gap:
  the CLAUDE.md rule names `write_text(encoding="utf-8")` without `newline="\n"`.
- **next_candidate:** a pre-commit check rejecting a BOM **or CRLF** in any
  tracked `.json` / `.jsonl` / `.yaml` / `.md` / `.env*` / `.gitignore` under
  the repo (not only `agents/`, `evals/`, `policies/`), plus the CLAUDE.md rule
  amended to `write_text(..., encoding="utf-8", newline="\n")` (or
  `write_bytes`).

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

## F-0006 — Voice renders overwrite shotN.mp3 in place (cut reproducibility lost)

- **severity:** med
- **frequency:** 1
- **root_cause:** Voice renders overwrite `shotN.mp3` in place, breaking
  append-only takes and the reproducibility of `cut_3`/`cut_4`. Kingsize CH 69
  (`outputs/kingsize_mattress__channel_69_late-night_spot_20260803_235816/`):
  all five `shotN.mp3` (and `projects/stripe/.../kingsize_ch69/vo/ann1..5.mp3`)
  were regenerated 2026-08-06 08:06, after `cut_4` (08-06 00:01) and `cut_3`
  (08-04); neither cut can be rebuilt from disk (recipe sums to 49.69 s; the
  delivered cuts are 45.21 s and 26.76 s).
- **second symptom:** `cut_4` was never recorded in `project.json` (`cuts[]`
  stops at `cut_3`); its mix survives only as moviepy litter
  (`apps/auto-studio/..._cut_4TEMP_MPY_wvf_snd.mp4`).
- **detected_at_layer:** human_review (FilmCraft Phase 0 bake-off, 2026-10-12)
- **should_have_been_prevented_at_layer:** harness
- **remediation_type:** process
- **status:** open
- **next_candidate:** voice takes versioned like video takes, the selected VO
  take tracked in `project.json` (Phase 2, with the cut ledger).

## F-0007 — Two incompatible line formats can be appended to the same song ledger

- **severity:** high
- **frequency:** 1 (no real ledger is known to be affected yet; found by reading
  code 2026-11-10, then confirmed by test)
- **root_cause:** `ilyrium-shots/ledger/<song>.jsonl` has writers in two formats.
  Format 1: `ilyrium-shots/provenance.py` `Ledger` (and the console review route's
  own copy of its hash code) writes snapshot records with
  `chain.prev_record_hash` / `chain.record_hash`. Format 3:
  `apps/control-panel/lib/ledger.ts` writes `{seq,event,songId,payload,ts,prev,hash}`
  for the takes route and the fal webhook (PR #28); `apps/auto-studio/cut_ledger.py`
  on open PR #29 writes the same format from Python. Nothing keeps the two out of
  one file. Measured by `tests/test_ledger_cross_format.py` and
  `apps/control-panel/lib/ledger.crossformat.test.ts`, each using goldens produced
  by the real writers:
  - `provenance.Ledger.verify_chain` returns False for a valid format-3 ledger, and
    `lib/ledger.ts` `verifyChain` returns False for a valid format-1 ledger.
  - One format-3 line appended after valid format-1 history makes `chain_ok` False.
  - A later `Ledger.append` does not heal it: it finds no `record_hash` on the
    foreign line and starts a new chain (`prev_record_hash: null`) mid-file.
  - `appendLedgerEntry` onto a format-1 file writes an entry with `seq: null` and
    no `prev`.
  - In every case the lines already in the file are left byte-identical, so
    append-only holds; what is lost is verifiability.
- **exposure:** `NH-S901.jsonl` holds 142 format-1 records. A `take_registered` or
  `fal_asset_completed` write for that song, or a cut record from PR #29, would
  break its `chain_ok`. History cannot be repaired by rewriting (CLAUDE.md).
- **not covered:** the review route's hashing is a hand copy of `provenance.py`'s;
  no test here proves the two agree on every record. `Ledger.append` has no file
  lock, so two processes appending at once can fork a chain; not tested here.
- **detected_at_layer:** human_review (spec review for ILY-206)
- **should_have_been_prevented_at_layer:** ci
- **remediation_type:** test (this entry) -> gate (one writer, pending)
- **status:** open
- **durable_artifact:** the two cross-format test files above and
  `tests/fixtures/ledger/`; run in CI by `.github/workflows/console.yml`. They
  characterise the hazard; they do not remove it.
- **next_candidate:** ILY-206 spec decision D4 (pick the canonical film-ledger
  format) and Phase 0 tasks 4-6: a lock inside `Ledger.append`, one writer behind
  one endpoint, and a guard that refuses a format-3 append to a file with format-1
  history. Until then: do not merge PR #29, and do not call the takes route or the
  fal webhook for a song that already has provenance history.
