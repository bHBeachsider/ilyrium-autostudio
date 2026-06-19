"use client";
import { ReactNode } from "react";

/**
 * ConsoleShell — a THIN layout abstraction for the stage workspaces.
 *
 * Why this exists: we want each of the 8 stages to feel like a pro editorial console
 * (Resolve/Blender "pages"), but we don't want to commit to a docking library before the
 * per-stage layouts are proven. So the contract here is layout-AGNOSTIC: a caller hands the
 * shell a set of named panels (by ZONE) and a layout preset; the shell decides arrangement.
 *
 * Today the implementation is a fixed CSS grid. Adopting Dockview later is a drop-in: write a
 * second component with the SAME props that renders these same panel nodes into Dockview groups.
 * Because callers only ever pass `panels` + `layout`, NOTHING in the stage pages changes when we
 * swap the implementation — no re-housing, no throwaway. That's the whole point of the seam.
 *
 *   <ConsoleShell layout="production" panels={{
 *      browser:   <ShotBrowser .../>,
 *      viewer:    <Viewer .../>,
 *      inspector: <Inspector .../>,
 *      timeline:  <TakeStrip .../>,
 *   }} topBar={<StageTabs .../>} />
 */

export type Zone = "browser" | "viewer" | "inspector" | "timeline" | "main";

export interface PanelDef {
  title?: string;
  node: ReactNode;
  /** hide the titled chrome (for a zone that's already a self-contained panel) */
  bare?: boolean;
}

export type ConsoleLayout =
  | "production"      // browser | viewer + timeline | inspector   (stage 4/6 — the editorial heart)
  | "editor"          // browser | main(editor) | inspector        (stage 2 script, 3 board)
  | "review"          // browser | viewer (A/B) | inspector         (stage 5)
  | "single"          // main only (stage 1 brief, 7 rights, 8 deliver)
  | "split";          // browser | main                             (generic fallback)

export interface ConsoleShellProps {
  panels: Partial<Record<Zone, PanelDef>>;
  layout?: ConsoleLayout;
  topBar?: ReactNode;
  /** optional override of the grid-template-areas (escape hatch for a one-off stage) */
  gridTemplate?: { areas: string; columns: string; rows: string };
}

// grid-template-areas per preset. Each token is a Zone; "." is an empty cell. The shell only
// renders a zone if (a) the layout references it AND (b) the caller supplied a panel for it.
const LAYOUTS: Record<ConsoleLayout, { areas: string; columns: string; rows: string; zones: Zone[] }> = {
  production: {
    areas: `"browser viewer inspector" "browser timeline inspector"`,
    columns: "190px 1fr 280px",
    rows: "1fr 150px",
    zones: ["browser", "viewer", "timeline", "inspector"],
  },
  editor: {
    areas: `"browser main inspector"`,
    columns: "190px 1fr 280px",
    rows: "1fr",
    zones: ["browser", "main", "inspector"],
  },
  review: {
    areas: `"browser viewer inspector"`,
    columns: "200px 1fr 260px",
    rows: "1fr",
    zones: ["browser", "viewer", "inspector"],
  },
  single: {
    areas: `"main"`,
    columns: "1fr",
    rows: "1fr",
    zones: ["main"],
  },
  split: {
    areas: `"browser main"`,
    columns: "200px 1fr",
    rows: "1fr",
    zones: ["browser", "main"],
  },
};

function Panel({ def }: { def: PanelDef }) {
  if (def.bare) return <>{def.node}</>;
  return (
    <div className="bg-panel border border-edge rounded-xl overflow-hidden flex flex-col min-h-0">
      {def.title && (
        <div className="text-[12px] text-dim uppercase tracking-wide px-3 py-2 border-b border-edge shrink-0">
          {def.title}
        </div>
      )}
      <div className="flex-1 overflow-auto min-h-0 p-3">{def.node}</div>
    </div>
  );
}

export default function ConsoleShell({ panels, layout = "split", topBar, gridTemplate }: ConsoleShellProps) {
  const preset = LAYOUTS[layout];
  const tmpl = gridTemplate || preset;
  // Only place zones that the layout references AND the caller actually provided.
  const zones = (gridTemplate ? (Object.keys(panels) as Zone[]) : preset.zones).filter((z) => panels[z]);

  return (
    <div className="flex flex-col gap-3 min-h-0">
      {topBar && <div className="shrink-0">{topBar}</div>}
      <div
        className="grid gap-3 min-h-0"
        style={{
          gridTemplateAreas: tmpl.areas,
          gridTemplateColumns: tmpl.columns,
          gridTemplateRows: tmpl.rows,
          minHeight: "60vh",
        }}
      >
        {zones.map((z) => (
          <div key={z} style={{ gridArea: z }} className="min-h-0 min-w-0">
            <Panel def={panels[z]!} />
          </div>
        ))}
      </div>
    </div>
  );
}
