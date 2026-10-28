# QA / Continuity / Governance checklist

Run on EVERY render before it is approved for release.

- [ ] Casting canon honored (origin / age / build per the character bible)?
- [ ] NO resemblance to a real public figure?  ← LEGAL GATE: reject if yes.
- [ ] Recurring motif correct? (e.g. mauve = brownish 1970s paperback, NOT lavender)
- [ ] Performance register held? (no smile-at-camera, no telegraphed emotion, no winking)
- [ ] Negative-prompt violations absent? (text / chyron / logo / modern devices / over-saturation)
- [ ] Continuity with the locked character anchor / prior shot?
- [ ] Rights/consent releases on file for any recurring face/voice? (00_admin/rights_releases/)

Fail -> regenerate using the matching fix in `style_kernel.json` -> `failure_fixes`.
This checklist is the human rubric behind the enforced release gate (approvedForRelease).
