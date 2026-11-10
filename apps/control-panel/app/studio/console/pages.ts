// The one table of console pages (ILY-206 task 11). The rail, the palette, [page]/page.tsx
// and the placeholders all read it. Plain module: no 'use client', no JSX, so both the
// server route and node-only tests can import it.

export type DomainKey = "pipeline" | "review" | "studio" | "script" | "generation" | "assembly" | "analytics";

export type PageDef = {
  slug: string;
  /** Heading shown for a placeholder, and the fallback nav label. */
  label: string;
  /** Rail and palette label for live and legacy pages. Run keeps "Pipeline" until the specs are updated. */
  navLabel?: string;
  /** run: Workspace renders Pipeline. legacy: Workspace renders the old domain inline. placeholder: [page]/page.tsx. */
  kind: "run" | "legacy" | "placeholder";
  domain?: DomainKey;
  /** Rail sub-line. */
  sub?: string;
  /** Extra palette search words for the page's "Go to" command (the slug is always searchable). */
  keywords?: string;
  /** Spec phase that builds a placeholder. */
  phase?: number;
  blurb?: string;
};

export const PAGES: readonly PageDef[] = [
  { slug: "run", label: "Run", navLabel: "Pipeline", kind: "run", domain: "pipeline", sub: "8-stage · auto-draft", keywords: "stages 8" },

  // Legacy pages: reachable, rendered inline, deleted together with their nav and palette
  // rows in task 17. `review` belongs to the Phase 3 placeholder, so the Neon-fed review
  // domain lives at legacy-review.
  { slug: "legacy-review", label: "Review Room", navLabel: "Review Room", kind: "legacy", domain: "review", sub: "Shot · take · approve", keywords: "takes approve" },
  { slug: "chat", label: "Studio Chat", navLabel: "Studio Chat", kind: "legacy", domain: "studio", sub: "LLM · Box control", keywords: "llm box" },
  { slug: "script", label: "Ideation & Scripting", navLabel: "Ideation & Scripting", kind: "legacy", domain: "script", sub: "Pre-Production" },
  { slug: "legacy-generation", label: "Asset Generation", navLabel: "Asset Generation", kind: "legacy", domain: "generation", sub: "Production", keywords: "render shot" },
  { slug: "legacy-assembly", label: "Timeline & Assembly", navLabel: "Timeline & Assembly", kind: "legacy", domain: "assembly", sub: "Post", keywords: "cut timeline" },
  { slug: "analytics", label: "Studio Control Plane", navLabel: "Studio Control Plane", kind: "legacy", domain: "analytics", sub: "Cost · Trace · Governance", keywords: "cost control plane" },

  // Placeholders. No blurb may contain the strings the existing specs match on.
  { slug: "floor", label: "Floor", kind: "placeholder", phase: 2, blurb: "Queue, cost and box state in one place." },
  { slug: "library", label: "Library", kind: "placeholder", phase: 3, blurb: "Every shot, take, keyframe and master a film owns." },
  { slug: "review", label: "Review", kind: "placeholder", phase: 3, blurb: "Frame-accurate take review with notes." },
  { slug: "sequence", label: "Sequence", kind: "placeholder", phase: 4, blurb: "The timeline." },
  { slug: "deliver", label: "Deliver", kind: "placeholder", phase: 5, blurb: "Release gates and delivery packages." },
  { slug: "sound", label: "Sound", kind: "placeholder", phase: 6, blurb: "Voice, music and mix." },
  { slug: "look", label: "Look", kind: "placeholder", phase: 7, blurb: "The style kernel and grade." },
  { slug: "stills", label: "Stills", kind: "placeholder", phase: 8, blurb: "Keyframes and key art." },
  { slug: "graph", label: "Graph", kind: "placeholder", phase: 8, blurb: "The asset graph." },
];

export function pageBySlug(slug: string | null | undefined): PageDef | undefined {
  return PAGES.find((p) => p.slug === slug);
}

export function isConsolePage(slug: string | null | undefined): boolean {
  return pageBySlug(slug) !== undefined;
}

export function slugForDomain(domain: DomainKey): string {
  const p = PAGES.find((x) => x.domain === domain);
  if (!p) throw new Error(`no console page for domain ${domain}`);
  return p.slug;
}

export function consoleHref(slug: string): string {
  return `/studio/console/${slug}`;
}

export function navLabelOf(p: PageDef): string {
  return p.navLabel ?? p.label;
}

/** The left rail: every non-placeholder page, in table order. Labels come from navLabelOf, the same function the palette uses. */
export function railPages(): PageDef[] {
  return PAGES.filter((p) => p.kind !== "placeholder");
}
