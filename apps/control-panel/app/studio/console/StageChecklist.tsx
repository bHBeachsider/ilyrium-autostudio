"use client";
import { useEffect, useState } from "react";

// Generic stage-checklist panel — renders ANY scaffold stage (1-11) from the manifests
// (bible_checklist.json + stage_checklists.json) via the pipeline service. Supersedes
// Stage1Bible.tsx. Each element surfaces the inputs it accepts: text, a generation prompt
// (Astria/Midjourney), image/video/file evidence, harvested refs, or json. Completion + current
// value come from stage_scaffold, so the folder tree and this UI never drift.
//
// Backend: GET {pipe}/stage/{project}/{n}/checklist ; POST .../element {key,text,instance?} ;
//          POST .../generate {key,prompt,model_family} ; POST .../media {key,filename,b64}

type El = { key: string; name: string; what: string; required: boolean; inputs: string[]; done: boolean; detail: string; value?: string; dimension?: string | null };
type Stage = { stage: number; name: string; what: string; elements: El[] };

const STAGE_NAMES: [number, string][] = [
  [1, "Bible"], [2, "Script"], [3, "Character"], [4, "Environment"], [5, "Keyframes"],
  [6, "Shots"], [7, "Voice"], [8, "Music"], [9, "Edit"], [10, "QA"], [11, "Key art"],
];
const DOT = (e: El) => e.done ? "#57c97a" : e.required ? "#ef6f6c" : "#8a8a8a";

export default function StageChecklist({ pipe, project, initialStage = 1 }: { pipe: string; project: string; initialStage?: number }) {
  const [n, setN] = useState(initialStage);
  const [data, setData] = useState<Stage | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(""); const [msg, setMsg] = useState("");

  async function load() {
    if (!project) return;
    try { const r = await fetch(`${pipe}/stage/${project}/${n}/checklist`); setData(await r.json()); }
    catch { setMsg(`pipeline service offline at ${pipe}`); }
  }
  useEffect(() => { load(); }, [project, n]);

  const kk = (el: string) => `${n}.${el}`;
  async function post(path: string, body: any, tag: string) {
    setBusy(tag); setMsg("");
    try { const r = await fetch(`${pipe}/stage/${project}/${n}/${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const d = await r.json(); setMsg(d.ok ? "saved" : (d.error || "failed")); await load();
    } catch (e: any) { setMsg(`unreachable: ${e.message}`); } finally { setBusy(""); }
  }
  async function upload(el: string, file: File) {
    setBusy(kk(el));
    const b64 = await new Promise<string>((res) => { const r = new FileReader(); r.onload = () => res(r.result as string); r.readAsDataURL(file); });
    await post("media", { key: el, filename: file.name, b64 }, kk(el));
  }

  const els = data?.elements || [];
  const doneN = els.filter(e => e.done).length;
  const reqMissing = els.filter(e => e.required && !e.done).length;
  // group by dimension if present (Stage 1), else one flat group
  const groups: Record<string, El[]> = {};
  els.forEach(e => { const g = e.dimension || "_"; (groups[g] = groups[g] || []).push(e); });

  function Row({ el }: { el: El }) {
    return (
      <div className="grid grid-cols-[10px_1fr] gap-2">
        <span className="mt-1.5 w-2 h-2 rounded-full" style={{ background: DOT(el) }} title={el.done ? "done" : el.required ? "required" : "optional"} />
        <div>
          <div className="text-[12px] text-fg">{el.name}
            {el.required && <span className="text-[10px] text-mauve ml-1">required</span>}
            <span className="text-[11px] text-dim ml-2">{el.inputs.join(" · ")}</span>
          </div>
          <div className="text-[11px] text-dim mb-1">{el.what}</div>
          {(el.inputs.includes("text") || el.inputs.includes("json")) && (
            <div className="flex gap-1 mb-1">
              <textarea value={draft[kk(el.key)] ?? el.value ?? ""} rows={el.inputs.includes("json") ? 3 : 2}
                onChange={(e) => setDraft(s => ({ ...s, [kk(el.key)]: e.target.value }))}
                placeholder={el.what} className="flex-1 bg-panel border border-edge rounded-md text-fg text-[12px] p-1.5 font-mono" />
              <button disabled={busy === kk(el.key)} onClick={() => post("element", { key: el.key, text: draft[kk(el.key)] ?? el.value ?? "" }, kk(el.key))}
                className="text-[11px] border border-edge text-fg rounded-md px-2 self-start py-1 disabled:opacity-50">save</button>
            </div>)}
          {el.inputs.includes("prompt") && (
            <div className="flex gap-1 mb-1">
              <input value={draft[kk(el.key) + ".p"] ?? ""} placeholder="generation prompt → Astria/Midjourney"
                onChange={(e) => setDraft(s => ({ ...s, [kk(el.key) + ".p"]: e.target.value }))}
                className="flex-1 bg-panel border border-mauve/40 rounded-md text-fg text-[12px] p-1.5" />
              <button disabled={busy === kk(el.key)} onClick={() => post("generate", { key: el.key, prompt: draft[kk(el.key) + ".p"] || "", model_family: "flux" }, kk(el.key))}
                className="text-[11px] border border-mauve/40 text-mauve rounded-md px-2 self-start py-1 disabled:opacity-50">generate</button>
            </div>)}
          {(el.inputs.includes("image") || el.inputs.includes("video") || el.inputs.includes("audio") || el.inputs.includes("file")) && (
            <label className="inline-block text-[11px] text-dim border border-dashed border-edge rounded-md px-2 py-1 cursor-pointer mb-1 mr-1">
              + attach {el.inputs.filter(i => ["image", "video", "audio", "file"].includes(i)).join("/")}
              <input type="file" className="hidden"
                accept={el.inputs.includes("video") ? "video/*" : el.inputs.includes("audio") ? "audio/*" : el.inputs.includes("image") ? "image/*" : undefined}
                onChange={(e) => e.target.files?.[0] && upload(el.key, e.target.files[0])} />
            </label>)}
          {el.inputs.includes("refs") && <span className="text-[11px] text-dim">refs: <span className="font-mono">{el.detail}</span></span>}
        </div>
      </div>);
  }

  return (
    <div className="space-y-3 mb-4">
      <div className="flex flex-wrap gap-1">
        {STAGE_NAMES.map(([num, name]) => (
          <button key={num} onClick={() => setN(num)}
            className={"text-[11px] px-2 py-0.5 rounded border " + (n === num ? "border-good text-good" : "border-edge text-dim")}>
            {num}·{name}
          </button>))}
      </div>
      {data && (
        <div className="flex items-center gap-3 text-[13px]">
          <span className="text-fg font-medium">Stage {data.stage} — {data.name}</span>
          <span className="text-dim">{doneN}/{els.length} · </span>
          <span style={{ color: reqMissing ? "#ef6f6c" : "#57c97a" }}>{reqMissing} required missing</span>
          {msg && <span className="text-dim ml-2">{msg}</span>}
        </div>)}
      {Object.entries(groups).map(([g, list]) => (
        <div key={g} className="bg-ink border border-edge rounded-lg p-3 space-y-3">
          {g !== "_" && <div className="text-[12px] text-mauve uppercase tracking-wide">{g}</div>}
          {list.map(el => <Row key={el.key} el={el} />)}
        </div>))}
    </div>);
}
