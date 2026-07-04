import { generateText, Output } from "ai"
import * as z from "zod"
import type { ClaimVerdict, ResearchBrief, Segment, VerificationReport } from "@/lib/db"

// Verification gate: no script reaches audio unless its factual claims are
// supported by the research brief. Extraction and judgment are separate calls so
// the judge sees claims stripped of narrative framing. The judge reads the ACTUAL
// source snippets/text — citations alone are never trusted (misattribution is the
// dominant failure mode of search-grounded models).

const claimsSchema = z.object({
  claims: z
    .array(
      z.object({
        text: z.string().describe("The factual claim, verbatim or minimally normalized"),
        segmentIndex: z.number().int().describe("0-based index of the script segment containing it"),
        kind: z
          .enum(["statistic", "event", "quote", "attribution", "other"])
          .describe("What kind of factual assertion this is"),
      }),
    )
    .describe("Every checkable factual assertion in the script. Opinions, color, and transitions are NOT claims."),
})

const verdictsSchema = z.object({
  verdicts: z
    .array(
      z.object({
        claimIndex: z.number().int().describe("Index into the provided claims list"),
        verdict: z
          .enum(["supported", "unsupported", "contradicted"])
          .describe(
            "supported = a source's text states this (or it is attributed on-air to the source that states it); unsupported = no source addresses it; contradicted = a source states otherwise",
          ),
        sourceIds: z.array(z.string()).describe("Source ids (S1, S2…) that support or contradict the claim"),
        note: z.string().describe("One short sentence of reasoning"),
      }),
    )
    .describe("One verdict per claim, same order as provided"),
})

export type ExtractedClaim = z.infer<typeof claimsSchema>["claims"][number]

export async function extractClaims(segments: Segment[]): Promise<ExtractedClaim[]> {
  const transcript = segments.map((s, i) => `[${i}] ${s.speaker}: ${s.text}`).join("\n")
  const { output } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: claimsSchema }),
    system:
      "You are a fact-check editor. Extract every discrete, checkable factual assertion from the podcast " +
      "script: numbers, dates, names, events, quotes, decisions, dollar amounts, locations. " +
      "Do NOT extract opinions, predictions framed as such, rhetorical questions, or hosts' color commentary. " +
      "Do NOT extract absence-of-information statements — lines saying something has not been announced, " +
      "named, decided, or that details are not yet known are editorial hedging, not checkable claims. " +
      "Do NOT extract generic background about how processes typically/generally work (zoning reviews, " +
      "permitting norms, market dynamics) — only assertions specific to THIS story are claims.",
    messages: [{ role: "user", content: `Script ([index] speaker: text):\n\n${transcript}` }],
  })
  return output.claims
}

export async function judgeClaims(claims: ExtractedClaim[], brief: ResearchBrief): Promise<ClaimVerdict[]> {
  if (claims.length === 0) return []
  const sourcesText = brief.sources
    .map((s) => `${s.id} [${s.outlet}${s.date ? `, ${s.date}` : ""}] ${s.title}\n${s.fullText ?? s.snippet}`)
    .join("\n\n---\n\n")
  const claimsText = claims.map((c, i) => `${i}. (${c.kind}) ${c.text}`).join("\n")

  const { output } = await generateText({
    model: "openai/gpt-5-mini",
    output: Output.object({ schema: verdictsSchema }),
    system:
      "You are a rigorous fact-checker. For each claim, decide from the PROVIDED SOURCE TEXTS ONLY whether it " +
      "is supported, unsupported, or contradicted. A claim is supported only if a source's text actually states " +
      "it — a source merely being about the same topic is NOT support. Reasonable paraphrase and unit conversion " +
      "are fine; invented specifics (numbers, names, quotes) not present in any source are unsupported. " +
      "A claim that accurately notes information is NOT yet available/announced counts as supported when no " +
      "source contradicts it. Do not use outside knowledge.",
    messages: [
      {
        role: "user",
        content: `SOURCES:\n\n${sourcesText}\n\nCLAIMS:\n${claimsText}\n\nReturn a verdict for every claim, in order.`,
      },
    ],
  })

  // Re-key defensively: model claimIndex is authoritative only when in range.
  return output.verdicts
    .filter((v) => v.claimIndex >= 0 && v.claimIndex < claims.length)
    .map((v) => ({
      claim: claims[v.claimIndex].text,
      segmentIndex: claims[v.claimIndex].segmentIndex,
      kind: claims[v.claimIndex].kind,
      verdict: v.verdict,
      sourceIds: v.sourceIds,
      note: v.note,
    }))
}

export function failedVerdicts(verdicts: ClaimVerdict[]): ClaimVerdict[] {
  return verdicts.filter((v) => v.verdict !== "supported")
}

/** Source ids cited by supported claims — drives the show-notes Sources section. */
export function supportedSourceIds(verdicts: ClaimVerdict[]): Set<string> {
  const ids = new Set<string>()
  for (const v of verdicts) {
    if (v.verdict === "supported") for (const id of v.sourceIds) ids.add(id)
  }
  return ids
}

/** Revision feedback for generateScript listing exactly what must change. */
export function revisionFeedback(failed: ClaimVerdict[]): string {
  const lines = failed.map(
    (v) =>
      `- [segment ${v.segmentIndex}] "${v.claim}" — ${v.verdict}${v.note ? ` (${v.note})` : ""}`,
  )
  return (
    "FACT-CHECK FAILURES. The following claims are not supported by the provided sources. " +
    "Rewrite the script to REMOVE each one or replace it with what the sources actually say " +
    "(with on-air attribution). Do not introduce any new specific facts, and do not narrate " +
    "gaps in the sources — if a detail isn't sourced, simply leave it out.\n" +
    lines.join("\n")
  )
}

export function buildReport(verdicts: ClaimVerdict[], revised: boolean, passed: boolean): VerificationReport {
  return { verdicts, revised, passedAt: passed ? new Date().toISOString() : null }
}
