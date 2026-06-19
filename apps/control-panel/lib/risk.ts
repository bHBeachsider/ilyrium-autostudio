// Risk scoring for the approval queue (Phase B). Publication of a master is a
// non-delegable A4 gate (per the policy pack autonomy ladder), so every master
// decision is tier A4; the score orders the queue within it and explains WHY a
// decision is risky. Kept in lib/ so routes can share it.

export const BLOCKING = new Set(["UNREVIEWED", "PENDING", "BLOCKED"]);

export interface RiskResult {
  score: number;
  tier: "A4" | "A3";
  severity: "high" | "medium" | "low" | "override";
  factors: string[];
}

// Higher score = more outstanding/risky. A likeness or no-likeness gap is the
// dominant factor (the legal front line); QA + other consents follow.
export function scoreRights(r: any): RiskResult {
  if (!r) return { score: 99, tier: "A4", severity: "high", factors: ["no RightsRecord (rights unreviewed)"] };
  if (r.overrideReason)
    return { score: 0, tier: "A4", severity: "override", factors: [`logged override: ${r.overrideReason}`] };

  const factors: string[] = [];
  let score = 0;
  const add = (cond: boolean, w: number, label: string) => { if (cond) { score += w; factors.push(label); } };

  add(!r.noLikenessConfirmed, 3, "no-likeness legal gate not confirmed");
  add(BLOCKING.has(r.likenessState), 3, `likeness consent ${r.likenessState}`);
  add(BLOCKING.has(r.voiceState), 2, `voice consent ${r.voiceState}`);
  add(BLOCKING.has(r.sourceMaterialState), 2, `source-material rights ${r.sourceMaterialState}`);
  add(BLOCKING.has(r.musicLicenseState), 1, `music license ${r.musicLicenseState}`);
  add(BLOCKING.has(r.vendorTermsState), 1, `vendor/model terms ${r.vendorTermsState}`);
  add(!r.qaPassed, 2, "QA checklist not passed");

  const highRisk = !r.noLikenessConfirmed || BLOCKING.has(r.likenessState) || BLOCKING.has(r.voiceState);
  const severity: RiskResult["severity"] = highRisk ? "high" : score >= 3 ? "medium" : score > 0 ? "low" : "low";
  // Publication is always non-delegable; tier stays A4. (A3 is reserved for the
  // reversible, non-publication actions the queue may surface later.)
  return { score, tier: "A4", severity, factors };
}
