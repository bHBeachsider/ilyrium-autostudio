"use client";
import { useState } from "react";
import type { C2PAStatus } from "./ReviewRoom";

export type RightsShot = {
  shotId: string;
  sceneNumber?: number;
  takes: Array<{
    takeId: string;
    model?: string | null;
    c2paStatus?: C2PAStatus;
  }>;
};

function shotRightsStatus(shot: RightsShot): "clear" | "gap" | "no-takes" {
  if (!shot.takes.length) return "no-takes";
  const worst = shot.takes.find((t) => t.c2paStatus === "broken" || t.c2paStatus === "missing");
  return worst ? "gap" : "clear";
}

const STATUS_STYLE: Record<"clear" | "gap" | "no-takes", { label: string; color: string }> = {
  clear:     { label: "Cleared",         color: "#57c97a" },
  gap:       { label: "Rights gap",      color: "#ef6f6c" },
  "no-takes": { label: "No takes",       color: "#e0a13a" },
};

export default function RightsPanel({
  shots,
  onDeliver,
}: {
  shots: RightsShot[];
  onDeliver?: () => void;
}) {
  const [filterBlocked, setFilterBlocked] = useState(false);

  const withStatus = shots.map((s) => ({ ...s, status: shotRightsStatus(s) }));
  const hasGap = withStatus.some((s) => s.status !== "clear");
  const visible = filterBlocked ? withStatus.filter((s) => s.status !== "clear") : withStatus;

  return (
    <div className="bg-panel border border-edge rounded-xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-edge flex items-center justify-between">
        <div className="text-[11px] text-dim uppercase tracking-wide">Rights &amp; Deliver</div>
        <label className="flex items-center gap-1.5 text-[11px] text-dim cursor-pointer select-none">
          <input
            type="checkbox"
            checked={filterBlocked}
            onChange={(e) => setFilterBlocked(e.target.checked)}
            className="rounded"
            aria-label="Show blocked only"
          />
          blocked only
        </label>
      </div>

      {/* Shot list */}
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {visible.length === 0 && (
          <div className="text-dim text-[13px] px-2 py-3">
            {filterBlocked ? "No blocked shots." : "No shots loaded."}
          </div>
        )}
        {visible.map((s) => {
          const style = STATUS_STYLE[s.status];
          return (
            <div
              key={s.shotId}
              className="rounded-md px-3 py-2 bg-raised/40 flex items-center justify-between gap-2"
            >
              <div>
                <div className="text-[13px] font-mono">{s.shotId}</div>
                {s.sceneNumber != null && (
                  <div className="text-[10px] text-dim">Scene {s.sceneNumber}</div>
                )}
                <div className="text-[10px] text-dim mt-0.5">
                  {s.takes.length} take{s.takes.length !== 1 ? "s" : ""}
                </div>
              </div>
              <span
                data-rights={s.status}
                className="text-[11px] font-mono px-2 py-0.5 rounded shrink-0"
                style={{ color: style.color, background: `${style.color}22` }}
              >
                {s.status !== "clear" && "⚠ "}
                {style.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Deliver gate */}
      <div className="border-t border-edge px-4 py-3">
        {hasGap && (
          <div
            className="text-[11px] mb-2 px-2 py-1.5 rounded"
            style={{ color: "#ef6f6c", background: "rgba(239,111,108,.08)", border: "1px solid rgba(239,111,108,.25)" }}
          >
            Master export blocked — {withStatus.filter((s) => s.status !== "clear").length} shot(s) have rights gaps. Resolve C2PA issues before delivering.
          </div>
        )}
        <button
          disabled={hasGap}
          onClick={onDeliver}
          data-deliver-blocked={hasGap ? "true" : undefined}
          className="w-full rounded-md px-4 py-2 text-[14px] font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          style={{
            color: hasGap ? "#97a1ad" : "#57c97a",
            border: `1px solid ${hasGap ? "rgba(151,161,173,.3)" : "rgba(87,201,122,.4)"}`,
            background: hasGap ? "transparent" : "rgba(87,201,122,.10)",
          }}
        >
          {hasGap ? "Export to Master — blocked" : "Export to Master"}
        </button>
      </div>
    </div>
  );
}
