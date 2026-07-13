"use client";
import { useCallback, useEffect, useRef, useState } from "react";

// Box & ComfyUI lifecycle panel — the console twin of app.py's render_box_panel.
// Polls GET {pipe}/box/status every ~5s (the service caches AWS ~5s, so polling
// is cheap) and drives POST /box/start | /box/tunnel | /box/stop. Errors are
// shown inline; a creds-less environment degrades to chips + disabled buttons.
const PIPE = process.env.NEXT_PUBLIC_PIPELINE_URL || "http://127.0.0.1:8800";

export type BoxStatus = {
  state: string;
  instance_id?: string | null;
  public_ip?: string | null;
  comfyui_up?: boolean;
  tunnel_up?: boolean;
  error?: string;
};

const BOX_DOT: Record<string, string> = { running: "🟢", pending: "🟡", stopping: "🟡", stopped: "⚪" };

function StatusChip({ label, dot, text }: { label: string; dot: string; text: string }) {
  return (
    <div className="bg-ink border border-edge rounded-md px-2.5 py-1.5 min-w-[92px]">
      <div className="text-[13px] font-mono">{dot} {text}</div>
      <div className="text-[11px] text-dim uppercase tracking-wide">{label}</div>
    </div>
  );
}

export default function BoxPanel({ onStatus }: { onStatus?: (s: BoxStatus | null) => void }) {
  const [s, setS] = useState<BoxStatus | null>(null);
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const onStatusRef = useRef(onStatus);
  onStatusRef.current = onStatus;

  const refresh = useCallback(async (force = false) => {
    try {
      const r = await fetch(`${PIPE}/box/status${force ? "?force=1" : ""}`);
      const d = await r.json();
      setS(d); setOffline(false); onStatusRef.current?.(d);
    } catch {
      setS(null); setOffline(true); onStatusRef.current?.(null);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  async function act(verb: "start" | "tunnel" | "stop") {
    setBusy(verb); setMsg("");
    try {
      const r = await fetch(`${PIPE}/box/${verb}`, { method: "POST" });
      const d = await r.json();
      if (d.error) setMsg(d.error);
      else if (verb === "start") setMsg("Start requested — watch the Box chip.");
      else if (verb === "stop") setMsg("Stop requested — billing ends once the instance is stopped.");
      else setMsg(d.message || "Tunnel opening — status will update shortly.");
      await refresh(true);
    } catch {
      setMsg(`Pipeline service unreachable at ${PIPE} — start studio_pipeline_service.py.`);
    } finally {
      setBusy("");
    }
  }

  const state = s?.state ?? (offline ? "offline" : "…");
  const transition = state === "pending" || state === "stopping";
  const err = state === "error" || offline;
  const boxDot = BOX_DOT[state] ?? "🔴";
  const tunnelUp = !!s?.tunnel_up && state === "running";

  const btn = "flex-1 text-[13px] border border-edge rounded-md px-2 py-1.5 text-fg disabled:opacity-40 hover:bg-raised transition-colors";

  return (
    <div className="bg-panel border border-edge rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[15px] font-semibold">📦 Box & ComfyUI</h3>
        <span className="text-[11px] text-dim font-mono">g6.2xlarge · ~$1.20/hr while running</span>
      </div>

      <div className="flex gap-2 flex-wrap mb-2">
        <StatusChip label="Box" dot={boxDot} text={state} />
        <StatusChip label="ComfyUI" dot={s?.comfyui_up ? "🟢" : "🔴"} text={s?.comfyui_up ? "reachable" : "unreachable"} />
        <StatusChip label="Tunnel" dot={tunnelUp ? "🟢" : "⚪"} text={tunnelUp ? "up" : "down"} />
      </div>
      <div className="text-[12px] text-dim font-mono mb-3">
        {s?.instance_id || "—"} · IP {s?.public_ip || "—"}
      </div>

      {err && (
        <div className="text-[12px] mb-2" style={{ color: "#ef6f6c" }}>
          {offline
            ? `Pipeline service offline at ${PIPE} — start studio_pipeline_service.py.`
            : `EC2 status unavailable — ${s?.error || "unknown error"}. Check AWS creds / boto3.`}
        </div>
      )}

      <div className="flex gap-2 mb-2">
        <button className={btn} disabled={!!busy || err || transition || state === "running"}
          title="ec2_session.ensure_running(wait=False) — non-blocking"
          onClick={() => act("start")}>{busy === "start" ? "…" : "▶ Start"}</button>
        <button className={btn} disabled={!!busy || state !== "running"}
          title="Opens SSH tunnels :8188 (ComfyUI) + :11434 (ollama) via cli/box.ps1 tunnel"
          onClick={() => act("tunnel")}>{busy === "tunnel" ? "…" : "🔌 Tunnel"}</button>
        <button className={btn} disabled={!!busy || err || transition || state === "stopped"}
          title="Stops the instance (ends ~$1.20/hr billing) and closes the tunnel"
          onClick={() => act("stop")}>{busy === "stop" ? "…" : "⏹ Stop"}</button>
        <button className={btn} disabled={!!busy} onClick={() => refresh(true)}>🔄 Refresh</button>
      </div>

      {msg && <div className="text-[12px] text-dim mb-1">{msg}</div>}
      {!s?.comfyui_up && !err && (
        <div className="text-[12px] text-dim">Start the box + open the tunnel to render on ComfyUI.</div>
      )}
    </div>
  );
}
