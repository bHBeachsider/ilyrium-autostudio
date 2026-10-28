"use client";
import { useCallback, useEffect, useState } from "react";
import { estimateCost, wouldExceedBudget, fmtCents } from "@/lib/metrics/costMeter";

const BUDGET_KEY = "ilyrium.cost.budget_cents";
export const SESSION_KEY = "ilyrium.cost.session_cents";
const DEFAULT_BUDGET = 1000; // $10.00

export type CostState = {
  sessionCents: number;
  budgetCents: number;
  addCents: (n: number) => void;
  setBudget: (n: number) => void;
};

function readBudget(): number {
  try { return Number(localStorage.getItem(BUDGET_KEY) || DEFAULT_BUDGET); } catch { return DEFAULT_BUDGET; }
}
function readSession(): number {
  try { return Number(sessionStorage.getItem(SESSION_KEY) || 0); } catch { return 0; }
}

export function useCostState(): CostState {
  const [sessionCents, setSessionCents] = useState(0);
  const [budgetCents, setBudgetCents] = useState(DEFAULT_BUDGET);

  // Hydrate from storage after mount (SSR-safe)
  useEffect(() => {
    setSessionCents(readSession());
    setBudgetCents(readBudget());
  }, []);

  const addCents = useCallback((n: number) => {
    setSessionCents((prev) => {
      const next = prev + n;
      try { sessionStorage.setItem(SESSION_KEY, String(next)); } catch {}
      return next;
    });
  }, []);

  const setBudget = useCallback((n: number) => {
    setBudgetCents(n);
    try { localStorage.setItem(BUDGET_KEY, String(n)); } catch {}
  }, []);

  return { sessionCents, budgetCents, addCents, setBudget };
}

export function CostBar({
  projectCents,
  costState,
}: {
  projectCents: number;
  costState: CostState;
}) {
  const { sessionCents, budgetCents, setBudget } = costState;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const fillPct = Math.min(100, Math.round((sessionCents / Math.max(budgetCents, 1)) * 100));
  const warn = fillPct >= 80;

  return (
    <div className="flex items-center gap-3 text-[12px]">
      <div className="flex items-center gap-1.5">
        <span className="text-dim">Session</span>
        <span className="font-mono" style={{ color: warn ? "#ef6f6c" : "#5b9dff" }}>
          {fmtCents(sessionCents)}
        </span>
        <span className="text-dim">/</span>
        {editing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const v = parseFloat(draft);
              if (!isNaN(v) && v > 0) setBudget(Math.round(v * 100));
              setEditing(false);
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoFocus
              onBlur={() => setEditing(false)}
              className="bg-ink border border-accent/60 rounded px-1.5 py-0 w-14 text-[11px] font-mono text-fg text-right"
            />
          </form>
        ) : (
          <button
            onClick={() => { setDraft((budgetCents / 100).toFixed(2)); setEditing(true); }}
            className="font-mono text-dim hover:text-fg"
            title="Click to edit budget cap"
          >
            {fmtCents(budgetCents)}
          </button>
        )}
      </div>
      <div className="w-20 h-1.5 bg-raised rounded-full overflow-hidden border border-edge/50" title={`${fillPct}% of budget`}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${fillPct}%`, background: warn ? "#ef6f6c" : "#5b9dff" }}
        />
      </div>
      {projectCents > 0 && (
        <span className="text-dim hidden lg:inline">
          Project <span className="font-mono text-fg">{fmtCents(projectCents)}</span>
        </span>
      )}
    </div>
  );
}

export function PreSubmitEstimate({
  shotCount,
  secPerShot,
  costPerSecCents,
  costState,
  onConfirm,
  disabled,
}: {
  shotCount: number;
  secPerShot: number;
  costPerSecCents: number;
  costState: CostState;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  const { sessionCents, budgetCents } = costState;
  const est = estimateCost(shotCount, secPerShot, costPerSecCents);
  const blocked = wouldExceedBudget(sessionCents, est.estimateCents, budgetCents);

  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-raised border border-edge rounded-lg mb-3">
      <div>
        <div className="text-[13px]">
          Estimated cost:{" "}
          <span className="font-mono font-semibold" style={{ color: blocked ? "#ef6f6c" : "#e0a13a" }}>
            {fmtCents(est.estimateCents)}
          </span>
        </div>
        <div className="text-[11px] text-dim">
          {shotCount} shot{shotCount !== 1 ? "s" : ""} × ~{secPerShot}s @ {fmtCents(costPerSecCents)}/s
        </div>
        {blocked && (
          <div className="text-[11px] mt-0.5" style={{ color: "#ef6f6c" }}>
            Exceeds session budget ({fmtCents(budgetCents)}) — raise the cap in Analytics.
          </div>
        )}
      </div>
      <button
        disabled={disabled || blocked}
        onClick={onConfirm}
        className="text-amber border border-amber/40 rounded-md px-3 py-1.5 text-[14px] disabled:opacity-40"
        style={{ background: "rgba(240,167,61,0.12)" }}
      >
        Confirm cost &amp; run
      </button>
    </div>
  );
}
