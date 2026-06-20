// Risk scoring for the approval queue (Phase B), rewritten onto the REAL risk-based
// rights_records model. Publication of a master is a non-delegable A4 gate, so every
// master decision is tier A4; the score orders the queue within it and explains WHY a
// decision is risky. Kept in lib/ so routes can share it.

export interface RiskResult {
  score: number;
  tier: "A4" | "A3";
  severity: "high" | "medium" | "low";
  factors: string[];
}

// Higher score = more outstanding/risky. A high likeness or overall risk, or an
// unfiled SAG-AFTRA notice for a synthetic performer, dominates.
export function scoreRights(r: any): RiskResult {
  if (!r) return { score: 99, tier: "A4", severity: "high", factors: ["no rights record (rights unreviewed)"] };

  const factors: string[] = [];
  let score = 0;
  const add = (cond: boolean, w: number, label: string) => {
    if (cond) {
      score += w;
      factors.push(label);
    }
  };

  add(r.likenessRisk === "high", 3, "likeness risk high");
  add(r.riskLevel === "high", 3, "overall risk level high");
  add(r.musicRisk === "high", 2, "music risk high");
  add(r.trademarkRisk === "high", 2, "trademark risk high");
  add(!!r.syntheticPerformerFlag && !r.sagAftraNoticeFiledAt, 2, "synthetic performer, SAG-AFTRA notice unfiled");
  add(r.releaseRequired && !["approved", "released"].includes(r.releaseStatus), 1, `release status ${r.releaseStatus ?? "pending"}`);
  add(!r.approvedForRelease, 1, "not yet approved for release");

  const high =
    r.likenessRisk === "high" ||
    r.riskLevel === "high" ||
    (!!r.syntheticPerformerFlag && !r.sagAftraNoticeFiledAt);
  const severity: RiskResult["severity"] = high ? "high" : score >= 3 ? "medium" : "low";

  // Publication is always non-delegable; tier stays A4.
  return { score, tier: "A4", severity, factors };
}
