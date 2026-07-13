"use client";
import { useEffect, useRef, useState } from "react";
import type { BoxStatus } from "./BoxPanel";

// Multi-provider studio chat. A plain text conversation routed — message by
// message — to the provider picked in the dropdown, via POST /api/llm/chat
// (server-side dispatch; keys never reach the browser). Default = local qwen3
// on the box through the ollama tunnel. Unavailable providers stay listed but
// locked, so it's obvious what would light up if a key were configured.
type Prov = { id: string; label: string; available: boolean };
type Msg = { role: "user" | "assistant"; content: string; provider?: string };

export default function ChatPanel({ boxStatus }: { boxStatus?: BoxStatus | null }) {
  const [providers, setProviders] = useState<Prov[]>([]);
  const [provider, setProvider] = useState("local-qwen");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/llm/chat")
      .then((r) => r.json())
      .then((d) => {
        setProviders(d.providers || []);
        if (d.default) setProvider(d.default);
      })
      .catch(() => setErr("Could not load the provider list (/api/llm/chat)."));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [msgs, busy]);

  const tunnelDown = provider === "local-qwen" && boxStatus != null &&
    (boxStatus.state !== "running" || !boxStatus.tunnel_up);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setErr(""); setInput(""); setBusy(true);
    const history = [...msgs, { role: "user" as const, content: text }];
    setMsgs(history);
    try {
      const r = await fetch("/api/llm/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider,
          messages: history.map(({ role, content }) => ({ role, content })),
        }),
      });
      const d = await r.json();
      if (d.ok && typeof d.reply === "string") {
        setMsgs((m) => [...m, { role: "assistant", content: d.reply, provider: d.provider }]);
      } else {
        setErr(d.error || `request failed (${r.status})`);
      }
    } catch (e: any) {
      setErr(`chat request failed: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  const current = providers.find((p) => p.id === provider);

  return (
    <div className="bg-panel border border-edge rounded-xl flex flex-col min-h-[60vh]">
      {/* header: provider picker */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-edge flex-wrap">
        <h3 className="text-[15px] font-semibold">💬 Studio Chat</h3>
        <select value={provider} onChange={(e) => { setProvider(e.target.value); setErr(""); }}
          className="bg-raised border border-edge rounded-md text-fg text-[13px] px-2 py-1.5 font-mono">
          {providers.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.available}>
              {p.available ? "○ " : "🔒 "}{p.label}{p.available ? "" : " — no key set"}
            </option>
          ))}
        </select>
        <span className="text-[12px] text-dim">
          {provider === "local-qwen"
            ? "runs on your box via the ollama tunnel — no external provider in the loop"
            : "external provider — uses its server-side API key"}
        </span>
      </div>

      {/* transcript */}
      <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-3">
        {msgs.length === 0 && (
          <div className="text-dim text-[14px]">
            Pick a provider and say something. Default is <span className="font-mono">local qwen3</span> on
            the EC2 box — start the box + tunnel in the Box panel if it isn&apos;t up.
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={"max-w-[85%] rounded-lg px-3 py-2 border text-[14px] whitespace-pre-wrap " +
              (m.role === "user" ? "bg-raised border-edge" : "bg-ink border-edge")}>
              {m.content}
              {m.role === "assistant" && (
                <div className="text-[11px] text-dim font-mono mt-1.5">— {m.provider}</div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="text-dim text-[13px]">… {current?.label || provider} is replying</div>}
      </div>

      {/* errors + hints */}
      {(err || tunnelDown) && (
        <div className="px-4 pb-1 space-y-1">
          {err && <div className="text-[13px]" style={{ color: "#ef6f6c" }}>{err}</div>}
          {tunnelDown && (
            <div className="text-[12px]" style={{ color: "#e0a13a" }}>
              local qwen3 needs the box + tunnel — use ▶ Start then 🔌 Tunnel in the Box panel.
            </div>
          )}
        </div>
      )}

      {/* composer */}
      <div className="flex gap-2 p-3 border-t border-edge">
        <textarea value={input} rows={2} placeholder={`Message ${current?.label || provider}…`}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          className="flex-1 bg-ink border border-edge rounded-md text-fg text-[14px] p-2 resize-none" />
        <button onClick={send} disabled={busy || !input.trim()}
          className="text-accent border border-accent/40 rounded-md px-4 text-[14px] disabled:opacity-40"
          style={{ background: "rgba(91,157,255,0.12)" }}>
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
