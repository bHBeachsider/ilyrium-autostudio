// Pure key matching (ILY-206 task 13). No DOM types at runtime, so node-only vitest can
// exercise it with plain objects.

export type Chord = { key: string; mod: boolean; shift: boolean; alt: boolean };

/** The parts of a KeyboardEvent the matcher reads. */
export type KeyLike = {
  key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean;
  getModifierState?: (key: string) => boolean;
};

/** Duck-typed event target: an Element, a window, a document or nothing. */
export type TargetLike = {
  tagName?: string; type?: string; isContentEditable?: boolean;
  getAttribute?: (name: string) => string | null;
} | null | undefined;

const NAMED: Record<string, string> = {
  space: " ", esc: "Escape", enter: "Enter",
  up: "ArrowUp", down: "ArrowDown", left: "ArrowLeft", right: "ArrowRight",
};

/** "mod+k", "?", "\\", "left". mod is Ctrl or Cmd. Tokens are lowercase, joined by "+". */
export function parseChord(chord: string): Chord {
  const parts = chord.split("+");
  const key = parts.pop() as string;
  if (!key) throw new Error(`bad chord "${chord}"`);
  const out: Chord = { key: NAMED[key] ?? key, mod: false, shift: false, alt: false };
  for (const p of parts) {
    if (p === "mod") out.mod = true;
    else if (p === "shift") out.shift = true;
    else if (p === "alt") out.alt = true;
    else throw new Error(`bad modifier "${p}" in chord "${chord}"`);
  }
  if (out.key.length > 1 && !Object.values(NAMED).includes(out.key)) throw new Error(`bad key "${key}" in chord "${chord}"`);
  return out;
}

const isLetter = (k: string) => k.length === 1 && k.toLowerCase() !== k.toUpperCase();

/** e.key, lowercased for single letters so Caps Lock does not break bare-letter bindings. Never e.code. */
export function eventKey(e: KeyLike): string {
  return isLetter(e.key) ? e.key.toLowerCase() : e.key;
}

/**
 * Exact modifier match: a bare key never fires with Ctrl, Meta or Alt held. Shift is
 * ignored only for single printable non-letters (? and backslash), where it is already
 * baked into e.key; for letters and named keys it must match (frame step lists shift+left
 * and shift+right itself).
 *
 * AltGr exception: on layouts that type a character with AltGr (backslash on German and
 * Nordic keyboards) Windows reports ctrlKey and altKey together, and some platforms report
 * getModifierState("AltGraph"). For a printable non-letter that is just how the character
 * was typed, so a bare chord for it still matches. A letter with Ctrl+Alt never does.
 */
export function matches(chord: Chord, e: KeyLike): boolean {
  const shiftFree = chord.key.length === 1 && !isLetter(chord.key);
  const altGr = shiftFree && !chord.mod && !chord.alt
    && (!!e.getModifierState?.("AltGraph") || (!!e.ctrlKey && !!e.altKey));
  if (!altGr) {
    if (chord.mod !== !!(e.ctrlKey || e.metaKey)) return false;
    if (chord.alt !== !!e.altKey) return false;
  }
  if (!shiftFree && chord.shift !== !!e.shiftKey) return false;
  return eventKey(e) === chord.key;
}

const NON_TEXT_INPUT = new Set(["checkbox", "radio", "range", "button", "submit", "reset", "file", "color", "image"]);

/** True when typed letters belong to the element (so single-key shortcuts must stay out). */
export function isTextEntry(t: TargetLike): boolean {
  if (!t || typeof t.tagName !== "string") return false;
  const tag = t.tagName.toUpperCase();
  if (tag === "TEXTAREA" || tag === "SELECT" || t.isContentEditable) return true;
  const role = t.getAttribute?.("role");
  if (role === "textbox" || role === "combobox" || role === "searchbox") return true;
  if (tag === "INPUT") return !NON_TEXT_INPUT.has((t.type || "text").toLowerCase());
  return false;
}

/** True when Space or Enter on the element already does something natively. */
export function isActivatable(t: TargetLike): boolean {
  if (!t || typeof t.tagName !== "string") return false;
  const tag = t.tagName.toUpperCase();
  if (tag === "BUTTON" || tag === "SUMMARY") return true;
  if (tag === "A") return t.getAttribute?.("href") != null;
  if (t.getAttribute?.("role") === "button") return true;
  return tag === "INPUT" && NON_TEXT_INPUT.has((t.type || "text").toLowerCase());
}
