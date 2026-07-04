import { afterEach, describe, expect, it } from "vitest"
import { briefToScriptSources, buildQueries, outletFromUrl, sourcesSection, trustedDomains, usableFullText } from "./research"
import type { ResearchBrief } from "./db"

const brief: ResearchBrief = {
  queries: ["q1"],
  sources: [
    { id: "S1", title: "Hospital approved", url: "https://www.wptv.com/a", outlet: "wptv.com", date: "2026-07-01", snippet: "The council approved a 156-bed hospital." },
    { id: "S2", title: "Roadwork on I-95", url: "https://cbs12.com/b", outlet: "cbs12.com", date: null, snippet: "Lane closures begin Monday.", fullText: "Full article body ".repeat(50) },
  ],
}

describe("buildQueries", () => {
  it("uses the idea title plus cleaned source_refs headlines, capped at 3", () => {
    const q = buildQueries({
      title: "Hospital reshapes the neighborhood",
      summary: null,
      source_refs: [
        "S23. $60 Million Acquisition Closed for 43-Acre Site — Florida News",
        "S20. Construction Starts on 54-Unit Village of Valor — WPBF",
        "S18. Third headline that should be cut by the cap — Outlet",
      ],
    })
    expect(q[0]).toBe("Hospital reshapes the neighborhood")
    expect(q[1]).toBe("$60 Million Acquisition Closed for 43-Acre Site")
    expect(q).toHaveLength(3)
  })
  it("survives empty refs", () => {
    expect(buildQueries({ title: "T", summary: null, source_refs: [] })).toEqual(["T"])
  })
})

describe("usableFullText", () => {
  it("rejects paywall stubs and accepts real bodies, capped", () => {
    expect(usableFullText("short teaser")).toBeUndefined()
    expect(usableFullText(null)).toBeUndefined()
    const body = "x".repeat(10_000)
    expect(usableFullText(body)!.length).toBe(6000)
  })
})

describe("outletFromUrl", () => {
  it("extracts hostname without www", () => {
    expect(outletFromUrl("https://www.wptv.com/news/x")).toBe("wptv.com")
    expect(outletFromUrl("not a url")).toBe("unknown")
  })
})

describe("briefToScriptSources", () => {
  it("prefers fullText over snippet and tags outlet/date", () => {
    const lines = briefToScriptSources(brief)
    expect(lines[0]).toContain("S1 [wptv.com, 2026-07-01] Hospital approved")
    expect(lines[0]).toContain("council approved")
    expect(lines[1]).toContain("Full article body")
  })
})

describe("sourcesSection", () => {
  it("filters to used sources when provided", () => {
    const section = sourcesSection(brief, new Set(["S2"]))
    expect(section).toContain("Roadwork on I-95")
    expect(section).not.toContain("Hospital approved")
  })
  it("falls back to all sources when nothing marked used", () => {
    const section = sourcesSection(brief, new Set())
    expect(section).toContain("Hospital approved")
    expect(section).toContain("Roadwork on I-95")
  })
})

describe("trustedDomains", () => {
  afterEach(() => {
    delete process.env.RESEARCH_TRUSTED_DOMAINS
  })
  it("uses defaults and honors the env override with a 20 cap", () => {
    expect(trustedDomains()).toContain("wptv.com")
    process.env.RESEARCH_TRUSTED_DOMAINS = Array.from({ length: 25 }, (_, i) => `d${i}.com`).join(",")
    expect(trustedDomains()).toHaveLength(20)
    expect(trustedDomains()[0]).toBe("d0.com")
  })
})
