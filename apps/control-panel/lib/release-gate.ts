// Shared release-gate logic, rewritten onto the REAL risk-based rights_records model
// (Phase 1 reconcile). Kept in lib/ (not a route file) so /api/studio/release-gate and
// /api/studio/approve can import it without tripping Next's route-export validation.
//
// Real rights_records fields (camelCase via @map): approvedForRelease, releaseRequired,
// releaseStatus, likenessRisk/musicRisk/trademarkRisk (none|low|medium|high), riskLevel
// (low|medium|high), syntheticPerformerFlag, sagAftraNoticeFiledAt. There is NO idealized
// qaPassed/noLikenessConfirmed/*State/overrideReason — those did not exist in the DB.

const RELEASED = new Set(["approved", "released"]);

/**
 * The substantive (non-approval-flag) reasons a master may NOT be released — the
 * preconditions that must be clear BEFORE /approve flips approvedForRelease. Fail-closed:
 * a missing record is itself a blocker.
 */
export function riskBlockers(r: any): string[] {
  if (!r) return ["No rights record for the master asset (rights unreviewed)."];
  const b: string[] = [];
  if (r.likenessRisk === "high") b.push("Likeness risk is high.");
  if (r.musicRisk === "high") b.push("Music risk is high.");
  if (r.trademarkRisk === "high") b.push("Trademark risk is high.");
  if (r.riskLevel === "high") b.push("Overall risk level is high.");
  if (r.syntheticPerformerFlag && !r.sagAftraNoticeFiledAt) {
    b.push("Synthetic performer present but SAG-AFTRA notice not filed.");
  }
  return b;
}

/**
 * The full release-gate view: every outstanding blocker including the not-approved /
 * release-status checks. allowed iff this returns []. Fail-closed.
 */
export function deriveBlockers(r: any): string[] {
  if (!r) return ["No rights record for the master asset (rights unreviewed)."];
  const b = riskBlockers(r);
  if (!r.approvedForRelease) b.unshift("Not approved for release.");
  if (r.releaseRequired && !RELEASED.has(r.releaseStatus)) {
    b.push(`Release required but status is '${r.releaseStatus ?? "pending"}'.`);
  }
  return b;
}
