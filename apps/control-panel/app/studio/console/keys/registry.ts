// The single table of console key bindings (ILY-206 task 13). Data only: handlers are
// supplied at runtime by the component that owns the behaviour (useKeyBindings). The cheat
// sheet and the palette are generated from this table, so they cannot drift from it.

import { PAGES, navLabelOf } from "../pages";

export type Scope = "global" | "palette" | "review";

export type BindingDef = {
  id: string;
  scope: Scope;
  /** Chord strings (see match.ts). Empty means palette-only: no key. */
  keys: readonly string[];
  description: string;
  group: string;
  palette?: { label?: string; category: string; keywords?: string };
  /** May fire while a text field has focus. */
  inFields?: boolean;
  /** May fire while a modal (palette, cheat sheet, reject dialog) is open. */
  allowInModal?: boolean;
  /** Fires on auto-repeat (held key). */
  repeat?: boolean;
  /** Default true: the dispatcher calls preventDefault before the handler. */
  preventDefault?: boolean;
};

const REVIEW = "Review (Run, stage 5)";

const fixed: BindingDef[] = [
  { id: "palette.toggle", scope: "global", keys: ["mod+k"], description: "Open or close the command palette", group: "General", inFields: true, allowInModal: true },
  { id: "help.cheatsheet", scope: "global", keys: ["?"], description: "Show or hide this list", group: "General", allowInModal: true, preventDefault: false,
    palette: { label: "Show keyboard cheat sheet", category: "Help", keywords: "hotkeys shortcuts" } },
  { id: "overlay.close", scope: "global", keys: ["esc"], description: "Close the palette or this list", group: "General", inFields: true, allowInModal: true, preventDefault: false },

  { id: "palette.up", scope: "palette", keys: ["up"], description: "Previous command", group: "Command palette", inFields: true },
  { id: "palette.down", scope: "palette", keys: ["down"], description: "Next command", group: "Command palette", inFields: true },
  { id: "palette.run", scope: "palette", keys: ["enter"], description: "Run the selected command", group: "Command palette", inFields: true },

  { id: "review.rate-half", scope: "review", keys: ["j"], description: "Play at half speed", group: REVIEW },
  { id: "review.pause", scope: "review", keys: ["k"], description: "Pause", group: REVIEW },
  { id: "review.play", scope: "review", keys: ["l"], description: "Play at normal speed", group: REVIEW },
  { id: "review.playpause", scope: "review", keys: ["space"], description: "Play or pause", group: REVIEW },
  { id: "review.frame-back", scope: "review", keys: ["left", "shift+left"], description: "Step back one frame", group: REVIEW, repeat: true },
  { id: "review.frame-fwd", scope: "review", keys: ["right", "shift+right"], description: "Step forward one frame", group: REVIEW, repeat: true },
  { id: "review.approve", scope: "review", keys: ["a"], description: "Approve the take", group: REVIEW },
  { id: "review.reject", scope: "review", keys: ["r"], description: "Reject the take (reason required)", group: REVIEW },
  { id: "review.next", scope: "review", keys: ["n"], description: "Next take", group: REVIEW },
  { id: "review.prev", scope: "review", keys: ["p"], description: "Previous take", group: REVIEW },
  { id: "review.ab", scope: "review", keys: ["\\"], description: "Cycle A/B mode (A only, A|B, wipe)", group: REVIEW },

  { id: "box.start", scope: "global", keys: [], description: "Start GPU Box", group: "Box", palette: { category: "Box", keywords: "ec2 comfyui start" } },
  { id: "box.stop", scope: "global", keys: [], description: "Stop GPU Box", group: "Box", palette: { category: "Box", keywords: "ec2 comfyui stop billing" } },
];

// One "Go to X" command per console page. The label is navLabelOf(page), the same function
// that labels the rail (Workspace renders the rail from railPages()), so they cannot disagree.
const nav: BindingDef[] = PAGES.map((p) => ({
  id: `nav.${p.slug}`, scope: "global", keys: [], description: `Go to ${navLabelOf(p)}`, group: "Navigate",
  palette: { category: "Navigate", keywords: [p.slug, p.keywords].filter(Boolean).join(" ") },
}));

export const BINDINGS: readonly BindingDef[] = [...fixed, ...nav];

export function formatChord(chord: string): string {
  const parts = chord.split("+");
  const key = parts.pop() as string;
  const pretty: Record<string, string> = { space: "Space", esc: "Esc", enter: "Enter", up: "↑", down: "↓", left: "←", right: "→" };
  const k = pretty[key] ?? (key.length === 1 ? key.toUpperCase() : key);
  return [...parts.map((m) => (m === "mod" ? "Ctrl" : m === "alt" ? "Alt" : "Shift")), k].join(" + ");
}

export type CheatRow = { id: string; group: string; keys: string; description: string };

/** Every binding that has a key, active or not, so the sheet always equals the registry. */
export function cheatSheetRows(defs: readonly BindingDef[]): CheatRow[] {
  return defs.filter((d) => d.keys.length > 0).map((d) => ({
    id: d.id, group: d.group, keys: d.keys.map(formatChord).join(" / "), description: d.description,
  }));
}

export type PaletteCommand = { id: string; label: string; category: string; keywords: string; keys: string };

const CATEGORY_ORDER = ["Navigate", "Box", "Help"];

/** Palette entries: every def with a palette block whose handler is currently registered. */
export function paletteCommands(defs: readonly BindingDef[], has: (id: string) => boolean): PaletteCommand[] {
  const rank = (c: string) => { const i = CATEGORY_ORDER.indexOf(c); return i < 0 ? CATEGORY_ORDER.length : i; };
  return defs
    .filter((d) => d.palette && has(d.id))
    .map((d) => ({
      id: d.id, label: d.palette!.label ?? d.description, category: d.palette!.category,
      keywords: d.palette!.keywords ?? "", keys: d.keys.map(formatChord).join(" / "),
    }))
    .sort((a, b) => rank(a.category) - rank(b.category));
}

/** Palette filter: an empty query shows everything; otherwise label, category and keywords are searched. */
export function filterCommands(cmds: PaletteCommand[], query: string): PaletteCommand[] {
  if (!query.trim()) return cmds;
  const q = query.toLowerCase();
  return cmds.filter((c) => `${c.label} ${c.category} ${c.keywords}`.toLowerCase().includes(q));
}
