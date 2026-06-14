# STRIPE (series)

Crude satirical strip. Lead: **Stripe** — a grotesquely fat, balding Boca mattress mogul
(made his fortune on refurbished mattresses), brassy and vulgar, thick gold chain, too-tight
white speedo. He brags poolside about his Gulfstream, his mansion, and the hardship of
splitting time between Boca / Aspen / the Jersey Shore — oblivious to the brown **stripe** on
the seat of his speedo that every lady can see. The title is the gag.

## Render approach
Uses the **Broderick hand** (`brdrck` style LoRA @ 0.95) as the drawing style — rough scratchy
B&W pen-and-pencil, grotesque underground-comix, white ground. **No char LoRA** (Stripe is a new
character); he's held together by an identical text description per panel. Art is rendered with
`satirist.render.render_flux_panels` (one Flux load for all panels); the strip is assembled with
`satirist.strip_compositor.compose_strip` (title card + balloons).

Repro scripts: `render_test/render_stripe.py` (panels) + `render_test/compose_stripe.py` (strip).

## render_test/ (2026-06-14, first pipeline test)
5 panels + composited `STRIPE_strip.png`. Verdict: pipeline works end-to-end; style + rough
consistency good. **Known miss:** panel 4 was meant to be a REAR view showing the stripe, but
Flux rendered Stripe front-facing — the visual punchline didn't land. Text alone won't reliably
force a back view on Flux.

## Next steps to make the gag land
1. Re-roll panel 4 with an explicit rear-view prompt ("seen from directly behind, his bare back
   and speedo to the camera, face away") + a few seeds; pick the one that shows the stripe.
2. For lock-in + the stripe as a learned feature: train a `stripe` character LoRA (like `brdmc`)
   on a small consistent reference set.
3. For guaranteed pose/orientation: ControlNet (OpenPose/depth) on the render step.
