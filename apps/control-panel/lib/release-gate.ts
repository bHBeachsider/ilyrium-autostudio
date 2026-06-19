// Shared release-gate logic (Phase A step 5). Kept in lib/ (not a route file) so
// both /api/studio/release-gate and /api/studio/approve can import it without
// tripping Next's route-export validation.

// Rights states that count as still-blocking when a field is applicable.
export const APPLICABLE_BLOCKING = new Set(["UNREVIEWED", "PENDING", "BLOCKED"]);

// Re-derives the outstanding blockers for a master asset's rights record.
// An explicit, logged override (overrideReason) clears the gate. Otherwise the
// no-likeness legal gate + QA must pass and no applicable rights state may block.
// Fail-closed: a missing record is not releasable.
export function deriveBlockers(rights: any): string[] {
  const b: string[] = [];
  if (!rights) return ["No RightsRecord for the master asset (rights unreviewed)."];
  if (rights.overrideReason) return [];
  if (!rights.noLikenessConfirmed) b.push("No-likeness legal gate not confirmed.");
  if (!rights.qaPassed) b.push("QA checklist not passed.");
  for (const [field, label] of [
    ["sourceMaterialState", "source-material rights"],
    ["likenessState", "likeness consent"],
    ["voiceState", "voice consent"],
    ["musicLicenseState", "music license"],
    ["vendorTermsState", "vendor/model terms"],
  ] as const) {
    if (APPLICABLE_BLOCKING.has(rights[field])) b.push(`Unresolved ${label} (${rights[field]}).`);
  }
  return b;
}
