"use client";

import { useState } from "react";

// Stage-4 HITL refinement controls for the trained character LoRA (Astria).
// Drives BOTH model families: SDXL (sdxl1) and Flux (flux1). Maps 1:1 to Astria's
// prompt-create API (https://docs.astria.ai/docs/api/prompt/create/). Posts to the
// existing shot-action endpoint with op "astria_refine"; the Python pipeline service
// resolves the character's tune id from lora_library.json by model_family + character.
//
// Wardrobe + body fields fold into the prompt text. Pose / composition is precise via
// ControlNet. Clothing can be swapped non-destructively via inpaint mask, or (Flux only)
// via the Virtual Try-on garment image.

const CONTROLNETS = ["", "pose", "depth", "canny", "composition", "lineart", "tile", "reference", "segroom", "ipadapter", "mlsd", "hed", "qr"];
const STYLES = ["", "Cinematic", "Photographic", "Digital Art", "Animated", "Fantasy art", "Neonpunk", "Enhance", "Comic book", "Lowpoly", "Line art"];
const ASPECTS = ["", "1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4", "4:3", "3:4", "21:9", "9:21"];
const FLUX_PRESETS = ["", "flux-lora-portrait", "flux-lora-focus", "flux-lora-fast"];

const inp = "bg-panel border border-edge rounded-md text-fg text-[12px] px-2 py-1";
const lbl = "text-dim text-[11px] block mb-0.5";

export default function AstriaRefine({ pipe, runId, scene, basePrompt, onResult }: {
  pipe: string; runId: string; scene: number; basePrompt: string; onResult?: (shots: any[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [family, setFamily] = useState<"sdxl" | "flux">("flux");
  const [wardrobe, setWardrobe] = useState("");
  const [body, setBody] = useState("");
  const [negative, setNegative] = useState("");
  const [controlnet, setControlnet] = useState("");
  const [cnScale, setCnScale] = useState("0.7");
  const [cnTxt2img, setCnTxt2img] = useState(true);
  const [denoise, setDenoise] = useState("0.8");
  const [inputUrl, setInputUrl] = useState("");
  const [maskUrl, setMaskUrl] = useState("");
  const [garmentUrl, setGarmentUrl] = useState("");
  const [preset, setPreset] = useState("flux-lora-portrait");
  const [loraScale, setLoraScale] = useState("");
  const [style, setStyle] = useState("");
  const [aspect, setAspect] = useState("");
  const [num, setNum] = useState("4");
  const [cfg, setCfg] = useState("");
  const [steps, setSteps] = useState("");
  const [seed, setSeed] = useState("");
  const [faceCorrect, setFaceCorrect] = useState(true);
  const [faceSwap, setFaceSwap] = useState(false);
  const [superRes, setSuperRes] = useState(true);
  const [inpaintFaces, setInpaintFaces] = useState(true);
  const [hiresFix, setHiresFix] = useState(false);
  const [filmGrain, setFilmGrain] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const composed = [basePrompt, wardrobe && `wearing ${wardrobe}`, body].filter(Boolean).join(", ");
  const num_ = (v: string) => (v.trim() === "" ? undefined : Number(v));

  async function run() {
    setBusy(true); setErr("");
    const payload: any = {
      op: "astria_refine",
      model_family: family,
      text: composed,
      negative_prompt: negative || undefined,
      controlnet: controlnet || undefined,
      controlnet_txt2img: controlnet ? cnTxt2img : undefined,
      controlnet_conditioning_scale: controlnet ? Number(cnScale) : undefined,
      denoising_strength: (controlnet || inputUrl) ? Number(denoise) : undefined,
      input_image_url: inputUrl || undefined,
      mask_image_url: maskUrl || undefined,
      garment_image_url: family === "flux" ? (garmentUrl || undefined) : undefined,
      preset: family === "flux" ? (preset || undefined) : undefined,
      lora_scale: num_(loraScale),
      style: style || undefined,
      aspect_ratio: aspect || undefined,
      num_images: num_(num),
      cfg_scale: num_(cfg),
      steps: num_(steps),
      seed: num_(seed),
      face_correct: faceCorrect,
      face_swap: faceSwap,
      super_resolution: superRes,
      inpaint_faces: inpaintFaces,
      hires_fix: hiresFix,
      film_grain: filmGrain,
    };
    try {
      const r = await fetch(`${pipe}/pipeline/${runId}/shot/${scene}/action`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload),
      });
      const j = await r.json();
      if (j.error) setErr(String(j.error));
      else if (j.shots && onResult) onResult(j.shots);
    } catch {
      setErr("pipeline service unreachable");
    } finally { setBusy(false); }
  }

  const fluxOnly = family === "flux";

  return (
    <div className="mt-2 border border-edge rounded-md bg-ink/60">
      <button onClick={() => setOpen((o) => !o)} className="w-full flex items-center justify-between px-2.5 py-1.5 text-[12px] text-fg">
        <span>{open ? "▾" : "▸"} Astria refine — wardrobe · pose · model</span>
        <span className="text-dim font-mono">{family.toUpperCase()}</span>
      </button>
      {open && (
        <div className="px-2.5 pb-2.5 space-y-2">
          {/* model family */}
          <div className="flex items-center gap-1">
            {(["flux", "sdxl"] as const).map((f) => (
              <button key={f} onClick={() => setFamily(f)}
                className={"text-[11px] font-mono px-2 py-0.5 rounded border " + (family === f ? "border-accent text-accent" : "border-edge text-dim")}
                style={family === f ? { background: "rgba(91,157,255,0.12)" } : undefined}>
                {f === "sdxl" ? "SDXL" : "Flux"}
              </button>
            ))}
            <span className="text-dim text-[11px] ml-1">tune resolved from lora_library by family</span>
          </div>

          {/* wardrobe + body */}
          <div className="grid grid-cols-2 gap-2">
            <label><span className={lbl}>wardrobe / clothing</span>
              <input value={wardrobe} onChange={(e) => setWardrobe(e.target.value)} placeholder="charcoal three-piece suit" className={inp + " w-full"} /></label>
            <label><span className={lbl}>body / pose (text)</span>
              <input value={body} onChange={(e) => setBody(e.target.value)} placeholder="seated, arms crossed" className={inp + " w-full"} /></label>
          </div>

          {/* controlnet */}
          <div className="grid grid-cols-2 gap-2 items-end">
            <label><span className={lbl}>ControlNet (precise pose/composition)</span>
              <select value={controlnet} onChange={(e) => setControlnet(e.target.value)} className={inp + " w-full"}>
                {CONTROLNETS.map((c) => <option key={c} value={c}>{c || "none"}</option>)}
              </select></label>
            <label><span className={lbl}>conditioning scale {cnScale}</span>
              <input type="range" min="0" max="1" step="0.05" value={cnScale} onChange={(e) => setCnScale(e.target.value)} disabled={!controlnet} className="w-full" /></label>
          </div>
          {controlnet && (
            <div className="grid grid-cols-2 gap-2 items-center">
              <label className="flex items-center gap-1.5 text-[11px] text-fg">
                <input type="checkbox" checked={cnTxt2img} onChange={(e) => setCnTxt2img(e.target.checked)} /> txt2img (off = img2img)</label>
              <label><span className={lbl}>denoise {denoise}</span>
                <input type="range" min="0" max="1" step="0.05" value={denoise} onChange={(e) => setDenoise(e.target.value)} className="w-full" /></label>
            </div>
          )}
          <label><span className={lbl}>ControlNet / img2img reference image URL</span>
            <input value={inputUrl} onChange={(e) => setInputUrl(e.target.value)} placeholder="https://… pose or composition reference" className={inp + " w-full"} /></label>

          {/* clothing swap via inpaint */}
          <label><span className={lbl}>inpaint mask URL (repaint only the masked clothing region)</span>
            <input value={maskUrl} onChange={(e) => setMaskUrl(e.target.value)} placeholder="https://… 1-channel mask (white = repaint)" className={inp + " w-full"} /></label>

          {/* flux virtual try-on */}
          {fluxOnly && (
            <div className="grid grid-cols-2 gap-2 items-end">
              <label><span className={lbl}>Virtual Try-on garment URL (Flux)</span>
                <input value={garmentUrl} onChange={(e) => setGarmentUrl(e.target.value)} placeholder="https://… garment image" className={inp + " w-full"} /></label>
              <label><span className={lbl}>Flux preset</span>
                <select value={preset} onChange={(e) => setPreset(e.target.value)} className={inp + " w-full"}>
                  {FLUX_PRESETS.map((p) => <option key={p} value={p}>{p || "none"}</option>)}
                </select></label>
            </div>
          )}

          {/* render attrs */}
          <div className="grid grid-cols-3 gap-2">
            <label><span className={lbl}>style</span>
              <select value={style} onChange={(e) => setStyle(e.target.value)} className={inp + " w-full"}>
                {STYLES.map((s) => <option key={s} value={s}>{s || "none"}</option>)}</select></label>
            <label><span className={lbl}>aspect</span>
              <select value={aspect} onChange={(e) => setAspect(e.target.value)} className={inp + " w-full"}>
                {ASPECTS.map((a) => <option key={a} value={a}>{a || "default"}</option>)}</select></label>
            <label><span className={lbl}>images (1-8)</span>
              <input value={num} onChange={(e) => setNum(e.target.value)} className={inp + " w-full"} /></label>
            <label><span className={lbl}>cfg</span>
              <input value={cfg} onChange={(e) => setCfg(e.target.value)} placeholder="auto" className={inp + " w-full"} /></label>
            <label><span className={lbl}>steps</span>
              <input value={steps} onChange={(e) => setSteps(e.target.value)} placeholder="auto" className={inp + " w-full"} /></label>
            <label><span className={lbl}>seed</span>
              <input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="random" className={inp + " w-full"} /></label>
            {fluxOnly && <label><span className={lbl}>lora scale</span>
              <input value={loraScale} onChange={(e) => setLoraScale(e.target.value)} placeholder="default" className={inp + " w-full"} /></label>}
          </div>

          {/* boolean enhancers */}
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-fg">
            {([["face correct", faceCorrect, setFaceCorrect], ["face swap", faceSwap, setFaceSwap],
               ["super-res x4", superRes, setSuperRes], ["inpaint faces", inpaintFaces, setInpaintFaces],
               ["hires fix", hiresFix, setHiresFix], ["film grain", filmGrain, setFilmGrain]] as const).map(([label, val, set]) => (
              <label key={label} className="flex items-center gap-1">
                <input type="checkbox" checked={val as boolean} onChange={(e) => (set as any)(e.target.checked)} /> {label}</label>
            ))}
          </div>

          <details className="text-[11px] text-dim">
            <summary className="cursor-pointer">composed prompt</summary>
            <div className="font-mono mt-1 break-words">{composed}</div>
          </details>

          {err && <div className="text-[11px]" style={{ color: "#ef6f6c" }}>{err}</div>}
          <button disabled={busy} onClick={run}
            className="text-accent border border-accent/40 rounded-md px-3 py-1 text-[12px] disabled:opacity-50"
            style={{ background: "rgba(91,157,255,0.12)" }}>
            {busy ? "generating…" : `Generate (${family.toUpperCase()})`}
          </button>
        </div>
      )}
    </div>
  );
}
