# Canon reconciliation — kernel casting canon vs. v11 overview

**Status: DECIDED 2026-08-15 — Reading A** (Brad). Logged 2026-08-15 when the v11 overview was ingested into the bible; resolved the same day. Applied to `style_kernel.json` + `apps/auto-studio/kernels/new_harnomy.json` (`casting_canon` for summer/pengold/dick now reads "Cast … , plays …"; a `canon_decision` block records the rule), `03_design/characters/CASTING_CANON.md`, the three character bibles' canon lines, `SOUL_ID_PLAN.md`, `START_HERE.md`; FINDINGS.md row NH-USA-001.

The Style Kernel (`style_kernel.json` → `casting_canon`, authored May 2026) fixes *how each principal is
photographed*; the v11 overview (Aug 2026) fixes *who they are*. Three characters read differently between
the two. The Stage-1 gate ("Every character's ORIGIN/AGE/BUILD in bible.md matches the casting_canon
entry — no drift") cannot be marked green until one of the readings below is chosen.

| Character | Kernel casting canon (fixed, photographic) | v11 backstory (creative) | Tension |
|---|---|---|---|
| **summer** | European, English-Italian old-money patrician, early 40s; composure that hides cost | Affluent, blue-blood **New England** family; "ancestors arrived on ships with names… summer on the Cape"; a limousine liberal | Continent of origin |
| **pengold** | American, **Northeast working-class origin**, late 40s; long-serving machine politician elevated into European-progressive technocratic register | Did not inherit his position; obsessive careerist at university, summa cum laude; **TWEEEDS summer intern** who watched and learned; "Ivy-educated progressive" *type* | Class origin (working-class vs. credentialed careerist — not strictly contradictory: a working-class kid who brown-nosed his way through an elite university fits both) |
| **dick** | European, early 30s, **Berlin-via-Antwerp gallerist's son** in bespoke-revolutionary costume | **American trust-fund heir**, "Little Dickie"; Brooklyn-creative-director aesthetic; family regarded him as soft | Nationality + family (both are inherited-wealth art-world/creative aesthetes) |
| valencia | European (Mediterranean rim or European East), late 40s | "actual working-class organizer" — no origin given | none |
| philip | European, late 40s–early 50s; senior classical scholar | classics professor, Peloponnesian War expert — no origin given | none |
| bildersatz | European; 1990s continental theorist; single authorized 1996 portrait | never discussed | none |

## Readings (pick one)

**A. Kernel = casting, v11 = character (recommended default).** The kernel's European casting was a
deliberate legal-distance choice: it keeps every principal far from any real American public figure (WORLD_RULES
#11; the kernel's `legal_rule`). Read it as *who is cast* — a European patrician face plays a New England blue
blood, a Berlin-Antwerp gallerist's son plays Little Dickie — exactly as a British actor plays an American.
The bibles keep the v11 backstory verbatim; the kernel keeps the photographic canon; nothing changes in code.
*Cost:* accents/voice casting must be American where the script says so; Dick's "Berlin-via-Antwerp" becomes
an actor note, not a character fact.

**B. v11 overrides the kernel.** Rewrite `casting_canon` to American origins per v11. *Cost:* re-opens the
likeness risk the kernel was built to close (an American machine-politician mayor, a New England heiress);
requires the QA legal gate to be more aggressive; kernel version bump.

**C. Hybrid.** Keep the European casting for Summer and Dick (legal distance for the two "types" most likely
to resemble someone), and adopt v11's TWEEEDS-intern careerist reading for Pengold (compatible with
"Northeast working-class origin").

## Decision record
- **2026-08-15 — Reading A adopted.** Rule: `casting_canon` describes HOW each principal is photographed (the cast face); the bibles describe WHO they are (v11). European faces play American characters, exactly as a British actor plays an American; accents/voices follow the script; Dick's Berlin-via-Antwerp is an actor note. Anchors, LoRAs and Soul-IDs derive from the casting_canon face — if the casting ever changes, they are retrained (identity assets are dependents of this slot).
- Stage-1 gate item "no drift" is now **green** for origin/age/build (bible canon lines == kernel strings). Remaining Stage-1 amber: reference backlinks to real files (Stage-4 harvest).
- **Divorce date resolved 2026-09-01 (reading C).** The divorce was finalized two years before the opera's present, and the affair with Dick began before it was final. Full decision, consequences and staging note in `world/TIMELINE.md`. FINDINGS NH-USA-002 closed. Consequent bible edits: Summer's "recently divorced (finalized one year ago)" -> "divorced two years ago"; the affair reads "just over two years old", not "1-2 years".
- Stage-3 anchor locks may proceed.
