import { describe, expect, it } from "vitest";
import { PAGES, consoleHref, isConsolePage, navLabelOf, pageBySlug, slugForDomain, type DomainKey } from "./pages";

const SPEC_SLUGS = ["run", "library", "review", "sequence", "sound", "look", "stills", "graph", "deliver", "floor"];
const DOMAINS: DomainKey[] = ["pipeline", "review", "studio", "script", "generation", "assembly", "analytics"];

describe("console pages", () => {
  it("covers the ten spec slugs", () => {
    for (const s of SPEC_SLUGS) expect(isConsolePage(s), s).toBe(true);
  });

  it("has unique slugs", () => {
    const slugs = PAGES.map((p) => p.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("gives every placeholder a phase and a blurb", () => {
    for (const p of PAGES.filter((x) => x.kind === "placeholder")) {
      expect(p.phase, p.slug).toBeGreaterThan(1);
      expect(p.blurb, p.slug).toBeTruthy();
    }
  });

  it("gives the spec review slug to the placeholder, and the old domain to legacy-review", () => {
    expect(pageBySlug("review")?.kind).toBe("placeholder");
    expect(pageBySlug("legacy-review")?.domain).toBe("review");
  });

  it("round-trips every domain through slugForDomain", () => {
    for (const d of DOMAINS) expect(pageBySlug(slugForDomain(d))?.domain).toBe(d);
  });

  it("rejects unknown slugs", () => {
    for (const s of ["bogus", "", "run/extra", null, undefined]) expect(isConsolePage(s as string)).toBe(false);
  });

  it("builds hrefs under /studio/console", () => {
    expect(consoleHref("run")).toBe("/studio/console/run");
  });

  it("keeps the rail labels the existing specs match, with Run labelled Pipeline", () => {
    expect(navLabelOf(pageBySlug("run")!)).toBe("Pipeline");
    expect(navLabelOf(pageBySlug("legacy-review")!)).toBe("Review Room");
    expect(navLabelOf(pageBySlug("analytics")!)).toBe("Studio Control Plane");
  });

  it("puts no text the specs match on into placeholders", () => {
    for (const p of PAGES.filter((x) => x.kind === "placeholder")) {
      const text = `${p.label} ${p.blurb}`;
      expect(text, p.slug).not.toMatch(/review room|analytics|control plane/i);
    }
  });

  it("uses the words 'review room' only for the legacy-review label", () => {
    const hits = PAGES.filter((p) => /review room/i.test(`${p.label} ${p.navLabel ?? ""} ${p.blurb ?? ""}`));
    expect(hits.map((p) => p.slug)).toEqual(["legacy-review"]);
  });
});
