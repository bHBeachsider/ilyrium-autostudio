# Storyboard — NH-S348 · "The Six Beats of the Finale" (final 90 seconds + 8 s black)

> Source: v11 §X (The Six Beats of the Finale — "the staging blueprint against which all directorial choices in
> the closing sequence must be measured"), plus The Arrest / Summer Beneath Her Portrait / The Mafia Wife
> Coronation / The Confirmation. Scene cards: `../../02_script/numbers/NH-S348_finale.scenes.json`.

**Total = 90 s + 8 s blackout.** Aspect 21:9 preferred. Environment plate: `03_design/environments/feast_stage_finale.md`.
Portrait prop: `03_design/props/summer_portrait.md`. Book prop: `03_design/props/mauve_framework_book.md`.

| Beat | t (s) | Title | Frame / camera | Stage picture | Sound | Contract |
|---|---|---|---|---|---|---|
| **1** | 0–15 | **The Denunciation** | full stage, wide, locked-off (a slow, almost imperceptible push permitted) | Full chorus, full orchestra. Dick has just been seized by the City AG; downstage center, being led in chains toward the stage-left exit. Chorus in formation behind Pengold, mauve books raised in unison like hymnals. Summer's portrait at half-height and rising, lit from below in Socialist-Realist gold. | TWEEEDS theme, most triumphant orchestration, brass forward | Everything at once — the only maximal image in the piece. |
| **2** | 15–35 | **The Listening** | two-shot logic: Dick (medium/close, downstage) vs. Pengold's back at the podium (does not turn); cut-ins: the chorus not hearing; the portrait reaching apex | The orchestra *thins* — strings out, brass out — to a single clarinet holding the TWEEEDS melody. Dick's voice over it, clear, unamplified, human: *"Pengold — you know me. You know the work. Tell them."* The chorus does not hear him. Pengold does not turn. The portrait reaches its apex and holds, blazing. "He is not drowned out. He is ignored." | single clarinet; Dick unamplified | *Load-bearing (The Clarinet Line).* Dick perfectly audible to the audience and inaudible to everyone on stage. |
| **3** | 35–50 | **The Exit** | tracking with Dick to the stage-left threshold; then a held two-shot across the stage: Dick at the threshold ↔ Valencia upstage right | Dick is led off. He does not scream. He stops speaking at the threshold, turns once, and looks — not at Pengold, not at Summer — at **Valencia**, upstage right, holding a mauve book she has not opened. She holds his look. Dick exits. | clarinet sustains → **stops mid-phrase** on his exit | "The only moment of genuine seeing in the opera." |
| **4** | 50–65 | **The Coronation** | slow processional tracking on Pengold from podium to Summer; then a locked medium two-shot: hand on shoulder, portrait blazing above | Silence on stage. Pengold turns from the podium and walks — unhurried, processional — to Summer beneath the portrait. He places his **right hand on her left shoulder**. She does not move. She does not look at him. She looks out, past the house, at nothing. **The smallest possible smile on Pengold's face. Held.** *(Optionally within the beat: "LYSTERIA's allocation is confirmed. The federal application can proceed. Your work will continue." — v11 places the Confirmation with the hand on her shoulder; keep it quiet or keep it out of the 15 s — writer's call.)* | silence (or the quiet Confirmation) | The Mafia Wife Coronation. Pengold's face is the casting test: settled, not triumphant. |
| **5** | 65–80 | **Valencia** | medium on Valencia; documentary register (flatter, truer light — "her own light"); a single insert of the book on the floor | One step downstage from upstage right, into her own light. She opens the mauve book she has been holding. She looks at it. She closes it. She lets it fall from her hand — not dramatically, just lets it fall. It hits the floor with **a single unamplified thump**. She sings one line: *"What won't you do?"* Not accusatory. Quiet. A question, offered to the house. | thump; one sung line | The question passes to the audience. |
| **6** | 80–90 | **The Chord and the Cut** | the **locked stage picture**, wide, static: Pengold's hand on Summer's shoulder; portrait blazing above them; Valencia in her own light, the dropped book at her feet; the chorus frozen mid-gesture, books still raised; nobody breathing | The orchestra enters underneath her — not a crescendo, an accumulation. Every instrument, one by one, joining a single sustained chord. Not a triad: TWEEEDS major and Valencia's modal minor inside it; the ear cannot decide the key. It grows until it is almost unbearable. **Hard cut to black. No fade. The chord does not resolve; it is severed.** | the chord → severed | *Load-bearing (The Eight Seconds).* |
| — | 90–98 | **Black** | black | Nothing. **Eight seconds** before any house light. | silence | "Eight seconds is cruel. Eight seconds is correct." |

**Render plan:**
1. Plate: feast stage with portrait half-height (Soul Location 21:9) + a second plate with portrait at apex.
2. Hero stills on the plate: Pengold at podium (back/three-quarter); Dick in chains downstage; Summer beneath the
   portrait; Valencia upstage right with the closed book; the chorus block with raised books — each with its Soul-ID /
   anchor (`--soul-id`, image reference = plate). The **locked stage picture** (beat 6) is ONE still with all four
   principals — render it first; it is the end frame for beat 4 and the whole of beat 6 (a 10-second hold with
   near-zero motion: use `end_image = start_image`).
3. i2v per beat from the stills; Kling 3.0 std for the holds/tracking (cheap), Seedance 2.0 with `audio_references`
   for beat 2 (Dick's line — lip-sync) and beat 5 (Valencia's line).
4. Assemble at fixed timings; append 8 s of black; **no fade**.

**QA gate specifics:** the hand is the right hand on the left shoulder; Summer never looks at Pengold; Pengold never
looks at Dick during beat 2; the smallest possible smile (not triumph); Valencia is the only one graded documentary;
the book thump is unamplified; the cut is a hard cut.
