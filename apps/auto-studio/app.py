import streamlit as st
import os
import json
import base64
import anthropic
import requests
from dotenv import load_dotenv

# Load environment variables immediately so media scripts can see them.
# override=True forces .env to win over any stale inherited vars (e.g. a leftover
# XAI_API_KEY in the shell/profile that shadows the correct key in .env).
load_dotenv(override=True)

# Local render orchestrator (xAI video + ElevenLabs audio + moviepy + R2)
from producer import produce_campaign, render_shot, assemble_cut
import project_store as ps
import ad_studio_agent
import otio_export
import stage_agents
from media import apiframe as apiframe_client
from media import comfyui_engine as ce
import console_helpers as ch

# --- PAGE CONFIG ---
st.set_page_config(page_title="Ilyrium Auto-Studio", page_icon="🎬", layout="wide")

# --- CUSTOM CSS FOR UPLOADER BUTTONS ---
st.markdown("""
<style>
    /* Target the file uploader delete 'X' button */
    [data-testid="stFileUploaderDeleteBtn"] {
        background-color: #ff4b4b; /* Streamlit red */
        color: white;
        transform: scale(1.5); /* Make it 50% bigger */
        margin-right: 5px; /* Give it a little breathing room */
        border-radius: 50%;
    }
    
    /* Make it darker red when you hover over it */
    [data-testid="stFileUploaderDeleteBtn"]:hover {
        background-color: #c93a3a;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- HISTORIC CAMPAIGN LOADER HELPER ---
def get_saved_campaigns():
    """Scan outputs/ for past runs (newest first). Prefer manifest.json, but fall
    back to project.json — campaigns produced by the director / 'Render Now' path
    save project.json (not manifest.json), so they were previously invisible here.
    project.json shots are normalized to the manifest 'scenes' shape so loading works."""
    campaigns = {}
    outputs_dir = "outputs"
    if not os.path.exists(outputs_dir):
        return campaigns
    folders = [f for f in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, f))]
    for folder in sorted(folders, reverse=True):  # timestamped names -> newest first
        fp = os.path.join(outputs_dir, folder)
        manifest_path = os.path.join(fp, "manifest.json")
        project_path = os.path.join(fp, "project.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    campaigns[folder] = json.load(f)
                    continue
            except Exception:
                pass
        if os.path.exists(project_path):
            try:
                with open(project_path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                campaigns[folder] = {
                    "business_name": p.get("business_name"),
                    "vibe": p.get("vibe"),
                    "format": p.get("format"),
                    "scenes": [
                        {"scene_number": s.get("scene_number"),
                         "visual_prompt": s.get("visual_prompt", ""),
                         "voiceover": s.get("voiceover", "")}
                        for s in sorted(p.get("shots", []), key=lambda x: x.get("scene_number", 0))
                    ],
                }
            except Exception:
                pass
    return campaigns

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "draft_scenes" not in st.session_state:
    st.session_state.draft_scenes = []
if "loaded_business_name" not in st.session_state:
    st.session_state.loaded_business_name = "Ilyrium Bar & Grill"
if "loaded_vibe" not in st.session_state:
    st.session_state.loaded_vibe = "High-Energy & Loud"
if "loaded_format" not in st.session_state:
    st.session_state.loaded_format = "9:16 (Instagram Reels/TikTok)"
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "active_project_dir" not in st.session_state:
    st.session_state.active_project_dir = None

# --- SIDEBAR: NEW PROJECT ---
st.sidebar.header("🎬 Project")
if st.sidebar.button("🆕 New Project", use_container_width=True,
                     help="Clear the current script, chat, and uploads and start a fresh project."):
    st.session_state.chat_history = []
    st.session_state.draft_scenes = []
    st.session_state.loaded_business_name = "Ilyrium Bar & Grill"
    st.session_state.loaded_vibe = "High-Energy & Loud"
    st.session_state.loaded_format = "9:16 (Instagram Reels/TikTok)"
    st.session_state.uploader_key += 1
    st.session_state.active_project_dir = None
    st.toast("Started a new project.", icon="🆕")
    st.rerun()
st.sidebar.divider()

# --- SIDEBAR: GLOBAL ACTIVE IMAGE MODEL --------------------------------------
# One always-visible selector (registry-driven) that seeds the default model of
# the stage-4 shot renderer, the edit/inpaint tool forms, and the Studio Chat.
st.sidebar.header("🎨 Active image model")
_global_model_ids = ch.comfyui_model_ids()
# A ':model <id>' Studio Chat command lands here so the widget can be updated
# BEFORE it is instantiated (Streamlit forbids writes after instantiation).
if "_pending_active_model" in st.session_state:
    _pend = st.session_state.pop("_pending_active_model")
    if _pend in _global_model_ids:
        st.session_state["active_image_model"] = _pend
if _global_model_ids:
    if st.session_state.get("active_image_model") not in _global_model_ids:
        # zimage is the fast on-box default; fall back to the first registry id.
        st.session_state["active_image_model"] = (
            "comfyui:zimage" if "comfyui:zimage" in _global_model_ids
            else _global_model_ids[0])
    st.sidebar.selectbox(
        "Active image model", _global_model_ids, key="active_image_model",
        help="On-box ComfyUI models from model_registry.json (provider == "
             "'comfyui'). Each control can still override per run.")
    st.sidebar.caption("Used by Render, Edit, Inpaint, and the Studio Chat tab.")
else:
    st.sidebar.caption("model_registry.json unavailable — no comfyui models found.")
st.sidebar.divider()

# --- SIDEBAR HISTORY PANEL ---
st.sidebar.header("📁 Campaign History")
saved_runs = get_saved_campaigns()

if saved_runs:
    selected_run = st.sidebar.selectbox("Select a past run", options=list(saved_runs.keys()))
    if st.sidebar.button("📂 Load Selected Campaign", use_container_width=True):
        manifest_data = saved_runs[selected_run]
        st.session_state.draft_scenes = manifest_data.get("scenes", [])
        st.session_state.loaded_business_name = manifest_data.get("business_name", "Ilyrium Bar & Grill")
        st.session_state.loaded_vibe = manifest_data.get("vibe", "High-Energy & Loud")
        st.session_state.loaded_format = manifest_data.get("format", "9:16 (Instagram Reels/TikTok)")
        # If this run has a project.json, make it the active project so the
        # Production Console can revise it shot by shot.
        st.session_state.active_project_dir = os.path.join("outputs", selected_run)
        st.sidebar.success(f"Loaded: {selected_run}")
        st.rerun()
else:
    st.sidebar.info("No saved local campaigns found yet. Run your first complete production to start a history!")

# --- BOX & COMFYUI CONTROL PANEL (upgraded Cloud-GPU block) ------------------
# Full lifecycle: Start box / Open tunnel / Stop box + live status chips.
# Rendered in the sidebar (always visible) AND in the "Box & Status" tab.
# All status reads go through console_helpers' ~5s cache so Streamlit reruns
# don't spam AWS describe-instances; every backend call is try/except-wrapped
# so a missing-creds environment degrades to a warning, never a traceback.
def render_box_panel(key: str):
    """Box & ComfyUI panel. `key` de-dupes widget keys across placements."""
    s = ch.box_status()
    state = s.get("state", "error")
    alive = ch.comfy_up()

    if state == "error":
        st.warning(f"EC2 status unavailable — {s.get('error', 'unknown error')}. "
                   "Check AWS creds / boto3. Box controls disabled.")
    _inst_dot = {"running": "🟢", "pending": "🟡", "stopping": "🟡",
                 "stopped": "⚪"}.get(state, "🔴")
    _tunnel = ("🟢 up" if alive else "⚪ down") if state == "running" else "⚪ down"
    st.markdown(
        f"**Instance:** {_inst_dot} {state}  \n"
        f"**ComfyUI:** {'🟢 reachable' if alive else '🔴 unreachable'}  \n"
        f"**Tunnel:** {_tunnel}"
    )
    st.caption(f"`{s.get('instance_id') or '—'}` · IP {s.get('public_ip') or '—'}")

    _transition = state in ("pending", "stopping")
    _b1, _b2, _b3 = st.columns(3)
    if _b1.button("▶ Start", key=f"{key}_start", use_container_width=True,
                  help="ec2_session.ensure_running(wait=False) — non-blocking.",
                  disabled=(state == "running" or _transition or state == "error")):
        try:
            import ec2_session
            with st.spinner("Requesting start…"):
                ec2_session.ensure_running(wait=False)
            st.toast("Start requested — watch the Instance chip.", icon="▶️")
        except Exception as e:
            st.warning(f"Could not start the box: {e}")
        ch.clear_status_cache()
        st.rerun()
    if _b2.button("🔌 Tunnel", key=f"{key}_tunnel", use_container_width=True,
                  disabled=(state != "running"),
                  help="Opens SSH tunnels :8188 (ComfyUI) + :11434 (ollama) via cli/box.ps1 tunnel."):
        try:
            st.toast(ch.run_box_verb("tunnel"), icon="🔌")
        except Exception as e:
            st.warning(f"Could not open the tunnel: {e}")
        ch.clear_status_cache()
    if _b3.button("⏹ Stop", key=f"{key}_stop", use_container_width=True,
                  help="Stops the instance (ends ~$1.20/hr billing) and closes the tunnel.",
                  disabled=(state == "stopped" or _transition or state == "error")):
        try:
            ch.run_box_verb("tunnel-down")   # best-effort; harmless if no tunnel
        except Exception:
            pass
        try:
            import ec2_session
            with st.spinner("Requesting stop…"):
                ec2_session.stop()
            st.toast("Stop requested — billing ends once the instance is stopped.", icon="⏹️")
        except Exception as e:
            st.warning(f"Could not stop the box: {e}")
        ch.clear_status_cache()
        st.rerun()

    if st.button("🔄 Refresh status", key=f"{key}_refresh", use_container_width=True):
        ch.clear_status_cache()
        st.rerun()
    if not alive:
        st.caption("Start the box + open the tunnel to render on ComfyUI.")
    st.caption("💸 g6.2xlarge ≈ $1.20/hr while running — Stop when done.")


st.sidebar.divider()
with st.sidebar:
    st.header("📦 Box & ComfyUI")
    render_box_panel(key="sb")

# --- MAIN UI ---
st.title("🎬 Ilyrium Auto-Studio")
st.subheader("AI Social Media Content Generator for Local Businesses")
st.divider()

# Top-level layout: the new stage-organized tool console ("Production"), the
# original end-to-end ad flow ("Ad Studio", unchanged behavior), the qwen3 +
# ComfyUI conversational REPL ("Studio Chat"), and the full box lifecycle
# panel ("Box & Status").
tab_prod, tab_ad, tab_chat, tab_box = st.tabs(
    ["🎛️ Production", "🎬 Ad Studio", "💬 Studio Chat", "📦 Box & Status"])

with tab_ad:
    # --- AD STUDIO: conversational director (primary, intuitive surface) ---
    st.header("🎬 Ad Studio — talk to the director")
    st.caption(
        "Describe your business and what you want. The director focuses the brief, writes the "
        "script, produces it, and revises it as you chat. Renders cost money and take a few minutes. "
        "(The manual tools below still work for hands-on control.)"
    )

    if "ad_messages" not in st.session_state:
        st.session_state.ad_messages = []      # Anthropic-format running conversation (with tool calls)
    if "ad_display" not in st.session_state:
        st.session_state.ad_display = []       # [{role, text}] for rendering the chat

    for _m in st.session_state.ad_display:
        with st.chat_message(_m["role"]):
            st.markdown(_m["text"])

    with st.form("ad_studio_form", clear_on_submit=True):
        _ad_prompt = st.text_area(
            "Message the director",
            placeholder="e.g., I run a taco bar in Ft. Pierce and need a punchy 15s Instagram ad",
            height=80, label_visibility="collapsed",
        )
        _ad_files = st.file_uploader(
            "📎 Attach reference images and/or docs for the director — optional (style, product, character, brief, brand guide)",
            type=["png", "jpg", "jpeg", "webp", "md", "txt", "csv", "json"],
            accept_multiple_files=True, key="ad_dir_uploader",
        )
        _ad_sent = st.form_submit_button("➤ Send to director", use_container_width=True)

    if _ad_sent and _ad_prompt.strip():
        # Thread attachments to the director: images -> vision blocks (Claude sees them);
        # text docs -> inline context. Images are persisted so they can later be locked
        # as a shot's first frame via set_script(source_image=...).
        _content, _n_imgs, _saved, _docs = [], 0, [], ""
        for _f in (_ad_files or []):
            try:
                _ext = _f.name.rsplit(".", 1)[-1].lower()
                if _ext in ("png", "jpg", "jpeg", "webp"):
                    _mt = "image/jpeg" if _ext in ("jpg", "jpeg") else f"image/{_ext}"
                    _content.append({"type": "image", "source": {
                        "type": "base64", "media_type": _mt,
                        "data": base64.b64encode(_f.getvalue()).decode("utf-8")}})
                    _refdir = os.path.join("outputs", "_director_refs")
                    os.makedirs(_refdir, exist_ok=True)
                    _sp = os.path.join(_refdir, _f.name)
                    with open(_sp, "wb") as _out:
                        _out.write(_f.getbuffer())
                    _saved.append(_sp.replace("\\", "/"))
                    _n_imgs += 1
                else:  # md / txt / csv / json -> inline text context
                    _docs += f"\n\n--- Attached document: {_f.name} ---\n{_f.getvalue().decode('utf-8', errors='replace')[:8000]}\n"
            except Exception:
                pass
        _text = _ad_prompt
        if _docs:
            _text += "\n\n[Reference documents the user attached:]" + _docs
        if _saved:
            _text += ("\n\n[Reference image(s) attached and saved at: " + ", ".join(_saved) +
                      ". To lock a shot to one of these, set that scene's source_image to its path in set_script.]")
        _content.append({"type": "text", "text": _text})
        st.session_state.ad_display.append({"role": "user", "text": _ad_prompt + (f"  📎 {_n_imgs} image(s)" if _n_imgs else "")})
        st.session_state.ad_messages.append({"role": "user", "content": _content if _n_imgs else _ad_prompt})
        _ad_err = None
        with st.status("🎬 Director working… (focusing, scripting, or rendering)", expanded=True) as _adstat:
            try:
                _res = ad_studio_agent.run_agent_turn(
                    st.session_state.ad_messages,
                    st.session_state.get("active_project_dir"),
                    progress_cb=lambda msg: st.write(msg),
                )
                st.session_state.ad_messages = _res["messages"]
                if _res.get("project_dir"):
                    st.session_state.active_project_dir = _res["project_dir"]
                st.session_state.ad_display.append({"role": "assistant", "text": _res["assistant_text"]})
                _adstat.update(label="Director responded", state="complete")
            except Exception as e:
                _ad_err = e
                _adstat.update(label="Director error", state="error")
        if _ad_err:
            st.error(f"Ad Studio error: {_ad_err}")
        else:
            st.rerun()

    st.divider()

    # --- 1. CONSOLIDATED BRAND KIT & ARTIFACTS ---
    st.header("🎯 1. Brand Kit & Campaign Context")
    st.write("Define your brand settings and upload any text, images, or reference videos to ground the AI.")

    # Create two columns to consolidate the UI
    col1, col2 = st.columns(2)

    with col1:
        business_name = st.text_input("Business Name", value=st.session_state.loaded_business_name)
        brand_color = st.color_picker("Primary Brand Color", "#D9534F")
    
        vibe_opts = ["High-Energy & Loud", "Chill & Relaxed", "Professional"]
        vibe_idx = vibe_opts.index(st.session_state.loaded_vibe) if st.session_state.loaded_vibe in vibe_opts else 0
        vibe = st.selectbox("Content Vibe", vibe_opts, index=vibe_idx)
    
        format_opts = ["9:16 (Instagram Reels/TikTok)", "16:9 (YouTube)"]
        format_idx = format_opts.index(st.session_state.loaded_format) if st.session_state.loaded_format in format_opts else 0
        output_format = st.selectbox("Output Format", format_opts, index=format_idx)

    with col2:
        # 1. The Clear Button
        if st.button("🗑️ Clear Uploads", use_container_width=True, help="Wipe all uploaded files to start fresh."):
            st.session_state.uploader_key += 1 # Changing the key forces the uploader to reset
            st.rerun()

        # 2. Multimodal Uploader (Now using the dynamic key)
        uploaded_files = st.file_uploader(
            "Upload reference documents & media", 
            type=["txt", "md", "csv", "json", "png", "jpg", "jpeg", "mp4", "mov"], 
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )
    
        # Process files into memory
        text_context = ""
        image_context = []
    
        if uploaded_files:
            with st.expander("Preview Uploaded Artifacts", expanded=False):
                for file in uploaded_files:
                    ext = file.name.split(".")[-1].lower()
                
                    # 1. Handle Text
                    if ext in ["txt", "md", "csv", "json"]:
                        try:
                            content = file.getvalue().decode("utf-8")
                            text_context += f"\n--- Document: {file.name} ---\n{content}\n"
                            st.caption(f"📄 Text loaded: {file.name}")
                        except Exception as e:
                            st.error(f"Could not read {file.name}: {e}")
                        
                    # 2. Handle Images (Base64 encoding for Claude Vision)
                    elif ext in ["png", "jpg", "jpeg"]:
                        st.image(file, caption=file.name, use_container_width=True)
                        encoded = base64.b64encode(file.getvalue()).decode("utf-8")
                        media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
                        image_context.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": encoded}
                        })
                    
                    # 3. Handle Video (UI preview only)
                    elif ext in ["mp4", "mov"]:
                        st.video(file)
                        st.caption(f"🎥 Video reference loaded: {file.name} (Visual reference only)")

    st.divider()

    # --- 2. SCRIPT GENERATION CHAT ---
    st.header("💬 2. Script Generation Chat")

    # Container to render the ongoing chat conversation safely
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                if isinstance(msg["content"], list):
                    for block in msg["content"]:
                        if block["type"] == "text":
                            st.markdown(block["text"])
                        elif block["type"] == "image":
                            st.caption("📎 [Image provided to AI]")
                else:
                    st.markdown(msg["content"])

    # Accept user chat inputs
    if user_prompt := st.chat_input(f"e.g., Draft a script for {business_name}..."):
    
        # 1. Build the User Message Payload
        message_content = []
    
        if image_context:
            message_content.extend(image_context)
    
        message_content.append({"type": "text", "text": user_prompt})
    
        st.session_state.chat_history.append({"role": "user", "content": message_content})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_prompt)
                if image_context:
                    st.caption(f"📎 [+ {len(image_context)} image(s) attached]")
        
            # 2. Query Anthropic
            with st.chat_message("assistant"):
                with st.spinner("🧠 Claude is analyzing artifacts & thinking..."):
                    client = anthropic.Anthropic()
                
                    artifact_injection = ""
                    if text_context:
                        artifact_injection = f"\n\n=== PROVIDED TEXT ARTIFACTS ===\n{text_context}\n===================================="
                
                    system_prompt = f"""
                    You are a creative director and social media manager. We are brainstorming video concepts for a local business.
                    Business Profile: {business_name}
                    Target Content Vibe: {vibe}
                    Target Dimensions: {output_format}{artifact_injection}
                
                    CRITICAL CONSISTENCY & SAFETY RULES:
                    1. VISUAL ANCHORING (NO MEMORY): The video AI has zero memory between scenes. If your script features a specific person, you MUST copy/paste their exact physical description into EVERY SINGLE `visual_prompt`. 
                    2. AUDIO SAFETY: The `voiceover` field MUST contain ONLY the exact English words to be spoken. NEVER use stage directions.
                
                    FINALIZING THE SCRIPT: 
                    Only when the user explicitly approves a final script, output the final script as a JSON array inside a markdown code block (using triple backticks and the word json). Each scene MUST have keys: "scene_number", "visual_prompt", "voiceover".
                    """
            
                    try:
                        response = client.messages.create(
                            model="claude-sonnet-5",
                            max_tokens=3000,
                            system=system_prompt,
                            messages=st.session_state.chat_history
                        )
                    
                        claude_reply = response.content[0].text
                        st.markdown(claude_reply)
                    
                        st.session_state.chat_history.append({"role": "assistant", "content": claude_reply})
                    
                        # 3. Automatic JSON Extraction
                        if "```json" in claude_reply:
                            try:
                                raw_json = claude_reply.split("```json")[1].split("```")[0].strip()
                                st.session_state.draft_scenes = json.loads(raw_json)
                                st.toast("✨ Script successfully parsed!", icon="🚀")
                            except Exception as json_err:
                                st.error(f"⚠️ Failed to parse JSON: {json_err}")
                            
                    except Exception as api_err:
                        st.error(f"❌ Anthropic API Connection Error: {api_err}")

    # --- 3. REVIEW, EDIT & RENDER ---
    if st.session_state.draft_scenes:
        st.divider()
        st.header("✍️ 3. Review & Edit Formatted Script")
    
        edited_scenes = []
        for i, scene in enumerate(st.session_state.draft_scenes):
            st.markdown(f"### Scene {i + 1}")
        
            col_v, col_a = st.columns(2)
        
            with col_v:
                visual_edit = st.text_area(
                    "Visual Prompt", 
                    value=scene.get("visual_prompt", ""), 
                    key=f"visual_{i}",
                    height=150
                )
        
            with col_a:
                audio_edit = st.text_area(
                    "Voiceover",
                    value=scene.get("voiceover", ""),
                    key=f"audio_{i}",
                    height=150
                )

            # Per-prompt input source (optional): attach a reference IMAGE (used as the
            # shot's keyframe first-frame -> continuity) or a CLIP (ingested directly).
            src_up = st.file_uploader(
                "📎 Reference image (keyframe first-frame) or clip — optional",
                type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "m4v"],
                key=f"src_{i}",
                help="Image → used as the first frame and animated (locks the look across shots). "
                     "Video → ingested directly as this shot's clip (no generation).",
            )
            source_image = source_clip = None
            if src_up is not None:
                _updir = os.path.join("outputs", "_prompt_uploads")
                os.makedirs(_updir, exist_ok=True)
                _dest = os.path.join(_updir, f"scene{i + 1}_{src_up.name}")
                with open(_dest, "wb") as _f:
                    _f.write(src_up.getbuffer())
                if (src_up.type or "").startswith("video"):
                    source_clip = _dest
                    st.caption(f"🎞️ Clip attached — will be ingested directly: {src_up.name}")
                else:
                    source_image = _dest
                    st.image(_dest, width=160, caption="Keyframe first-frame")

            _sc = {
                "scene_number": i + 1,
                "visual_prompt": visual_edit,
                "voiceover": audio_edit,
            }
            if source_image:
                _sc["source_image"] = source_image
            if source_clip:
                _sc["source_clip"] = source_clip
            edited_scenes.append(_sc)
        
        st.divider()
    
        # --- 4. PRODUCTION PIPELINE ---
        st.header("🎬 4. Send to Studio OS Pipeline")
        st.write("Ready to build? This will send your approved script to your Next.js backend for database tracking and async rendering.")
    
        if st.button("🚀 Send to Production Pipeline", use_container_width=True, type="primary"):
            import time
        
            # 1. Prepare the payload for Next.js mapping
            mapped_scenes = []
            for scene in edited_scenes:
                mapped_scenes.append({
                    "scene_number": scene["scene_number"],
                    "technical_visual_prompt": scene["visual_prompt"], 
                    "clean_voiceover": scene["voiceover"] 
                })
            
            campaign_title = f"{business_name} - {vibe} Campaign"
            payload = {
                "title": campaign_title,
                "scenes": mapped_scenes
            }

            # 2. Fire to Next.js Database
            st.info("📡 Connecting to Studio OS API...")
            NEXTJS_API_URL = "http://localhost:3000/api/campaigns"
        
            try:
                response = requests.post(NEXTJS_API_URL, json=payload)
            
                if response.status_code == 201:
                    data = response.json()
                    st.success(f"✅ Success! Campaign ID: `{data['campaignId']}` created in Neon Database with {data['sceneCount']} scenes.")
                    st.balloons()
                
                    # 3. Save locally to maintain Streamlit sidebar history
                    run_id = f"campaign_{int(time.time())}"
                    output_dir = os.path.join("outputs", run_id)
                    os.makedirs(output_dir, exist_ok=True)
                
                    manifest_data = {
                        "business_name": business_name,
                        "vibe": vibe,
                        "format": output_format,
                        "scenes": edited_scenes
                    }
                    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
                        json.dump(manifest_data, f, indent=4)
                    
                else:
                    st.error(f"❌ Failed to send to Studio OS. Status Code: {response.status_code}")
                    st.write(response.text)
                
            except requests.exceptions.ConnectionError:
                st.error("🚨 Could not connect to Studio OS. Is your Next.js server running on `http://localhost:3000`?")

        # --- 5. RENDER THE ACTUAL VIDEO (LOCAL + R2) ---
        st.divider()
        st.header("🎥 5. Render the Video")
        st.write(
            "Run the full production pipeline now: **xAI Grok** renders each scene, "
            "**ElevenLabs** generates the voiceovers, the clips are stitched into one "
            "commercial, and the master is uploaded to your **R2** bucket. "
            "This calls paid APIs and can take several minutes."
        )

        if st.button("🎬 Render Video Now (Local + R2)", use_container_width=True):
            with st.status("Rendering campaign… this can take a few minutes.", expanded=True) as status:

                def _cb(msg):
                    st.write(msg)

                try:
                    result = produce_campaign(
                        business_name=business_name,
                        vibe=vibe,
                        output_format=output_format,
                        scenes=edited_scenes,
                        upload_to_r2=True,
                        progress_cb=_cb,
                    )
                    st.session_state.active_project_dir = result.get("project_dir")

                    final_video = result.get("final_video")
                    if final_video and os.path.exists(final_video):
                        status.update(label="✅ Render complete!", state="complete")
                        st.success(f"Final video saved to: `{final_video}`")
                        st.video(final_video)
                        if result.get("public_url"):
                            st.write(f"☁️ **R2 URL:** {result['public_url']}")
                        # Surface any scenes that failed to render
                        failed = [s["scene_number"] for s in result.get("scene_results", []) if not s["video_ok"]]
                        if failed:
                            st.warning(f"Note: scene(s) {failed} failed to render and were skipped.")
                    else:
                        status.update(label="❌ Render failed", state="error")
                        st.error("No final video was produced. Check the log above for which scenes failed.")

                except Exception as e:
                    status.update(label="❌ Render crashed", state="error")
                    st.error(f"Render error: {e}")


    # --- 6. PRODUCTION CONSOLE: revise the project shot by shot (non-destructive) ---
    _proj_dir = st.session_state.get("active_project_dir")
    if _proj_dir and os.path.exists(os.path.join(_proj_dir, "project.json")):
        project = ps.load_project(_proj_dir)
        if project:
            st.divider()
            st.header("🎛️ 6. Production Console — revise shot by shot")
            st.caption(
                f"Project `{project['campaign_id']}` · regenerating a shot adds a new "
                f"take and never overwrites the others. Pick the take you want, then re-assemble the cut."
            )

            for shot in sorted(project["shots"], key=lambda s: s["scene_number"]):
                n = shot["scene_number"]
                st.markdown(f"#### Shot {n}")
                ok_takes = [t for t in shot.get("takes", []) if t.get("video")]

                col_prev, col_ctrl = st.columns([2, 1])
                with col_prev:
                    sel_id = shot.get("selected_take")
                    sel = ps.get_take(shot, sel_id) if sel_id else None
                    if sel and sel.get("video") and os.path.exists(sel["video"]):
                        st.video(sel["video"])
                        st.caption(f"Selected: {sel_id} · model {sel.get('model')} · {len(ok_takes)} take(s)")
                    else:
                        st.info("No usable take yet for this shot.")
                    st.caption(shot.get("visual_prompt", "")[:160])

                with col_ctrl:
                    if ok_takes:
                        options = [t["take_id"] for t in ok_takes]
                        current = sel_id if sel_id in options else options[0]
                        chosen = st.radio(
                            "Take in the cut", options, index=options.index(current),
                            key=f"take_select_{n}",
                        )
                        if chosen != shot.get("selected_take"):
                            ps.set_selected_take(project, n, chosen)
                            ps.save_project(_proj_dir, project)
                            st.rerun()

                    _model = st.selectbox(
                        "Model", ch.render_model_options(),
                        key=f"model_{n}",
                        help="grok = fast draft · veo/kling = premium w/ dialogue · comfyui:<id> = "
                             "self-hosted registry model on the EC2 box (stills; ids from "
                             "model_registry.json) · ue = Unreal 3D (prompt=level-sequence) · keyframe = "
                             "Midjourney still -> image-to-video (kernel-styled, consistent)",
                    )
                    # ComfyUI renders RAISE when the endpoint is dead — gate on reachability.
                    _comfy_blocked = ch.is_comfy_model(_model) and not ch.comfy_up()
                    if _comfy_blocked:
                        st.caption("⛔ Start the box + open the tunnel to render on ComfyUI "
                                   "(Box & Status tab).")
                    _regen = st.button(f"🔄 Regenerate shot {n}", key=f"regen_{n}",
                                       use_container_width=True, disabled=_comfy_blocked)
                if _regen:
                    _err = None
                    with st.status(f"Regenerating shot {n} via {_model}…", expanded=True) as s_status:
                        try:
                            render_shot(project, _proj_dir, n, model=_model, progress_cb=lambda m: st.write(m))
                            s_status.update(label=f"Shot {n}: new take added", state="complete")
                        except Exception as e:
                            _err = e
                            s_status.update(label="Regen failed", state="error")
                    if _err:
                        st.error(f"{_err}")
                    else:
                        st.rerun()

            st.divider()
            if st.button("🎬 Re-assemble cut from selected takes", use_container_width=True, type="primary"):
                with st.status("Assembling new cut…", expanded=True) as c_status:
                    try:
                        cut = assemble_cut(project, _proj_dir, upload_to_r2=True,
                                           progress_cb=lambda m: st.write(m))
                        if cut.get("final_video") and os.path.exists(cut["final_video"]):
                            c_status.update(label=f"{cut['cut_id']} ready", state="complete")
                            st.success(f"New cut: {cut['final_video']}")
                            st.video(cut["final_video"])
                            if cut.get("public_url"):
                                st.write(f"☁️ R2: {cut['public_url']}")
                        else:
                            c_status.update(label="Assembly failed", state="error")
                            st.error("No cut produced — make sure shots have selected takes.")
                    except Exception as e:
                        c_status.update(label="Assembly crashed", state="error")
                        st.error(f"{e}")

            # --- Music bed + finishing ---
            st.divider()
            st.subheader("🎵 Music & finishing")
            _mc1, _mc2 = st.columns(2)
            with _mc1:
                _music_file = st.file_uploader("Music bed (mp3/wav)", type=["mp3", "wav", "m4a"], key="music_up")
                _gain = st.slider("Music volume", 0.0, 1.0, float(project.get("music_gain", 0.15)), 0.05, key="music_gain_sl")
                if _music_file is not None:
                    _music_path = os.path.join(_proj_dir, "music_bed" + os.path.splitext(_music_file.name)[1])
                    with open(_music_path, "wb") as _mf:
                        _mf.write(_music_file.getvalue())
                    project["music"] = _music_path
                    project["music_gain"] = _gain
                    ps.save_project(_proj_dir, project)
                    st.caption(f"Music: {os.path.basename(_music_path)} — re-assemble the cut to hear it.")
                elif _gain != project.get("music_gain", 0.15):
                    project["music_gain"] = _gain
                    ps.save_project(_proj_dir, project)
                if project.get("music"):
                    st.caption(f"Current music: {os.path.basename(project['music'])}")
                with st.expander("✨ Generate music with Suno (APIFrame)"):
                    _sp = st.text_input("Describe the music", placeholder="upbeat warm acoustic, ~90 bpm", key="suno_prompt")
                    _si = st.checkbox("Instrumental", value=True, key="suno_inst")
                    if st.button("Generate music", key="suno_gen", use_container_width=True) and _sp.strip():
                        with st.status("Generating music via Suno…", expanded=True) as _ms:
                            try:
                                _mp = apiframe_client.generate_music(
                                    _sp, os.path.join(_proj_dir, "music_bed.mp3"), instrumental=_si)
                                project["music"] = _mp
                                ps.save_project(_proj_dir, project)
                                _ms.update(label="Music generated", state="complete")
                                st.audio(_mp)
                                st.caption("Set as the bed — re-assemble the cut to mix it in.")
                            except Exception as e:
                                _ms.update(label="Music generation failed", state="error")
                                st.error(f"{e}")
            with _mc2:
                st.caption("Hand the rough cut to DaVinci Resolve for trims, color, and master render.")
                if st.button("🎞️ Export timeline (.otio) for DaVinci", use_container_width=True):
                    try:
                        _otio = otio_export.export_project_otio(project, _proj_dir)
                        st.success(f"Exported: {_otio}")
                    except Exception as e:
                        st.error(f"OTIO export failed: {e}")


    # --- STUDIO ROOMS: per-stage ideation/refinement agents for scaffold film projects ---
    st.divider()
    st.header("🏛️ Studio Rooms — per-stage ideation agents")
    st.caption(
        "Each pipeline stage of a scaffolded film project has a dedicated agent (Story Architect, "
        "Screenwriter, Cinematographer, …) grounded in the project's Style Kernel + casting canon. "
        "It reads project context and writes drafts into the stage folder. Autonomy A1: it proposes, you accept."
    )

    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ilyrium-autostudio
    _PROJECTS_DIR = os.path.join(_REPO_ROOT, "projects")
    import project_paths as _project_paths
    _room_project_map = dict(_project_paths.list_projects())   # "client/proj" or "proj" -> abs path
    _room_projects = sorted(_room_project_map)

    if not _room_projects:
        st.caption("No scaffolded projects yet — run `python scaffold.py \"Title\"` to create one under projects/.")
    else:
        if "room_convos" not in st.session_state:
            st.session_state.room_convos = {}
        if "room_display" not in st.session_state:
            st.session_state.room_display = {}

        _rc1, _rc2 = st.columns(2)
        _sel_proj = _rc1.selectbox("Project", _room_projects, key="room_proj")
        _stages = stage_agents.list_stage_agents()
        _labels = [f"{f} · {persona}" for f, persona, title in _stages]
        _sel_i = _rc2.selectbox("Room (stage)", range(len(_stages)),
                                format_func=lambda i: _labels[i], key="room_stage")
        _stage_folder, _persona = _stages[_sel_i][0], _stages[_sel_i][1]
        _proj_path = _room_project_map.get(_sel_proj) or os.path.join(_PROJECTS_DIR, _sel_proj)
        _ckey = f"{_sel_proj}::{_stage_folder}"
        _disp = st.session_state.room_display.setdefault(_ckey, [])

        for _m in _disp:
            with st.chat_message(_m["role"]):
                st.markdown(_m["text"])

        with st.form(f"room_form_{_ckey}", clear_on_submit=True):
            _msg = st.text_area(f"Talk to the {_persona}", height=80, label_visibility="collapsed",
                                placeholder="e.g., draft a logline and three recurring world motifs")
            _room_files = st.file_uploader(
                "📎 Attach references/docs — optional",
                type=["png", "jpg", "jpeg", "webp", "md", "txt", "csv", "json"],
                accept_multiple_files=True, key=f"room_up_{_ckey}",
            )
            _send = st.form_submit_button(f"➤ Send to {_persona}", use_container_width=True)

        if _send and _msg.strip():
            _convo = st.session_state.room_convos.setdefault(_ckey, [])
            # Thread images as vision blocks + docs as inline text, like the director.
            _rc_content, _rc_docs, _rc_imgs = [], "", 0
            for _rf in (_room_files or []):
                try:
                    _re = _rf.name.rsplit(".", 1)[-1].lower()
                    if _re in ("png", "jpg", "jpeg", "webp"):
                        _rmt = "image/jpeg" if _re in ("jpg", "jpeg") else f"image/{_re}"
                        _rc_content.append({"type": "image", "source": {"type": "base64",
                            "media_type": _rmt, "data": base64.b64encode(_rf.getvalue()).decode("utf-8")}})
                        _rc_imgs += 1
                    else:
                        _rc_docs += f"\n\n--- {_rf.name} ---\n{_rf.getvalue().decode('utf-8', errors='replace')[:8000]}\n"
                except Exception:
                    pass
            _rc_text = _msg + (("\n\n[Attached documents:]" + _rc_docs) if _rc_docs else "")
            _rc_content.append({"type": "text", "text": _rc_text})
            _convo.append({"role": "user", "content": _rc_content if (_rc_imgs or _rc_docs) else _msg})
            _disp.append({"role": "user", "text": _msg + (f"  📎 {_rc_imgs} image(s)" if _rc_imgs else "") + (" 📄 doc(s)" if _rc_docs else "")})
            _rerr = None
            with st.status(f"{_persona} working…", expanded=True) as _rstat:
                try:
                    _rres = stage_agents.run_stage_agent(_stage_folder, _proj_path, _convo,
                                                         progress_cb=lambda m: st.write(m))
                    st.session_state.room_convos[_ckey] = _rres["messages"]
                    _disp.append({"role": "assistant", "text": _rres["assistant_text"]})
                    _rstat.update(label=f"{_persona} responded", state="complete")
                except Exception as e:
                    _rerr = e
                    _rstat.update(label="Room error", state="error")
            if _rerr:
                st.error(f"Studio Room error: {_rerr}")
            else:
                st.rerun()


# =============================================================================
# 🎛️ PRODUCTION TAB — every studio tool, grouped by pipeline stage
# =============================================================================
def _render_tool_expander(tool: dict, key_prefix: str, project_dir, comfy_alive: bool):
    """One studio tool as a usable control: a form generated from its
    input_schema, executed via studio_tools.execute_tool. Never raises into
    the UI — every failure lands in st.error."""
    name = tool["name"]
    fkey = f"{key_prefix}_{name}"
    comfy_tool = name in ch.COMFY_ONLY_TOOLS

    with st.expander(f"**{name}** — {tool['summary']}"):
        st.caption(tool["description"])

        # Data-driven model choices for the ComfyUI still-edit tools: the
        # on-box short ids from model_registry.json (provider == 'comfyui').
        enum_overrides = {}
        if comfy_tool:
            _shorts = ch.comfyui_short_ids()
            if _shorts:
                enum_overrides["model"] = _shorts
                # Default the form's model field to the sidebar's global
                # "Active image model" (short id: comfyui:flux2 -> flux2).
                # Re-synced whenever the global choice changes; the user can
                # still override inside the form.
                _g_short = ch.short_model_id(
                    st.session_state.get("active_image_model", ""))
                if (_g_short in _shorts and
                        st.session_state.get(f"_model_synced_{fkey}") != _g_short):
                    st.session_state[f"{fkey}_model"] = _g_short
                    st.session_state[f"_model_synced_{fkey}"] = _g_short

        mask_path = None
        with st.form(f"form_{fkey}", clear_on_submit=False):
            values = ch.schema_widgets(tool, fkey, enum_overrides=enum_overrides)
            if name == "inpaint_image":
                _mask_up = st.file_uploader(
                    "Mask image (white=change, black=keep) — optional alternative to region",
                    type=["png", "jpg", "jpeg", "webp"], key=f"{fkey}_mask_up")
                if _mask_up is not None:
                    _mdir = os.path.join("outputs", "_masks")
                    os.makedirs(_mdir, exist_ok=True)
                    mask_path = os.path.join(_mdir, _mask_up.name)
                    with open(mask_path, "wb") as _mf:
                        _mf.write(_mask_up.getbuffer())
            if comfy_tool and not comfy_alive:
                st.caption("⛔ Start the box + open the tunnel to render on ComfyUI "
                           "(Box & Status tab).")
            run = st.form_submit_button(f"Run {name}", use_container_width=True,
                                        disabled=(comfy_tool and not comfy_alive))
        if not run:
            return

        tool_input, errors = ch.split_form_errors(values)
        if mask_path:
            tool_input["mask"] = mask_path
        for _e in errors:
            st.error(_e)
        _missing = ch.missing_required(tool, tool_input)
        if _missing:
            st.error(f"Missing required field(s): {', '.join(_missing)}")
        if errors or _missing:
            return
        # A comfyui:* model chosen inside the form can't disable the submit
        # button pre-emptively — gate it here instead (dead endpoint RAISES).
        if ch.is_comfy_model(str(tool_input.get("model", ""))) and not comfy_alive:
            st.error("That model runs on the ComfyUI box, which is unreachable. "
                     "Start the box + open the tunnel first (Box & Status tab).")
            return

        from studio_tools import execute_tool
        res = None
        if name in ch.SLOW_TOOLS:
            with st.status(f"Running {name}… (may call paid/slow backends)",
                           expanded=True) as _tstat:
                try:
                    res = execute_tool(name, tool_input, project_dir,
                                       progress_cb=lambda m: st.write(m))
                    _tstat.update(label=f"{name} finished", state="complete")
                except Exception as e:
                    _tstat.update(label=f"{name} failed", state="error")
                    st.error(f"{name} error: {e}")
        else:
            try:
                with st.spinner(f"Running {name}…"):
                    res = execute_tool(name, tool_input, project_dir)
            except Exception as e:
                st.error(f"{name} error: {e}")
        if res is not None:
            ch.show_tool_result(res.get("content", ""))
            if res.get("project_dir") and res["project_dir"] != project_dir:
                st.session_state.active_project_dir = res["project_dir"]
                st.info(f"Active project is now: {res['project_dir']}")


def _render_shot_control(project_dir, comfy_alive: bool):
    """Stage-4 bespoke control: producer.render_shot with the registry-driven
    model picker (comfyui:* ids included), gated on ComfyUI reachability."""
    st.markdown("##### 🎥 Render a shot (`render_shot`)")
    if not project_dir or not os.path.exists(os.path.join(project_dir, "project.json")):
        st.info("Select a project with a project.json above to render shots.")
        st.divider()
        return
    try:
        _proj = ps.load_project(project_dir)
    except Exception as e:
        st.warning(f"Could not load the project: {e}")
        st.divider()
        return
    if not _proj or not _proj.get("shots"):
        st.info("This project has no shots yet — set a script first (stage 2).")
        st.divider()
        return

    _scene_opts = sorted(s["scene_number"] for s in _proj["shots"])
    _rc1, _rc2, _rc3 = st.columns([1, 2, 1])
    _scene = _rc1.selectbox("Shot", _scene_opts, key="prod_render_scene")
    # Default the model to the sidebar's global "Active image model": whenever
    # the global choice changes, push it into this widget (pre-instantiation);
    # the user can still override per render (incl. the video engines).
    _shot_opts = ch.render_model_options()
    _g_model = st.session_state.get("active_image_model")
    if _g_model in _shot_opts and st.session_state.get("_shot_model_synced") != _g_model:
        st.session_state["prod_render_model"] = _g_model
        st.session_state["_shot_model_synced"] = _g_model
    _model = _rc2.selectbox(
        "Model", _shot_opts, key="prod_render_model",
        help="Defaults to the sidebar's Active image model. comfyui:<id> = "
             "self-hosted registry models on the EC2 box (from model_registry.json).")
    _blocked = ch.is_comfy_model(_model) and not comfy_alive
    _rc3.markdown("&nbsp;", unsafe_allow_html=True)   # aligns the button row
    _go = _rc3.button("Render", key="prod_render_go", use_container_width=True,
                      disabled=_blocked)
    if _blocked:
        st.caption("⛔ Start the box + open the tunnel to render on ComfyUI "
                   "(Box & Status tab).")
    if _go:
        with st.status(f"Rendering shot {_scene} via {_model}…", expanded=True) as _rs:
            try:
                _tid = render_shot(_proj, project_dir, _scene, model=_model,
                                   progress_cb=lambda m: st.write(m))
                if _tid:
                    _rs.update(label=f"Shot {_scene}: new take {_tid} added", state="complete")
                else:
                    _rs.update(label=f"Shot {_scene}: render produced no take", state="error")
            except Exception as e:
                _rs.update(label="Render failed", state="error")
                st.error(f"Render error: {e}")
        # Preview the newest take (image or video) if one landed.
        try:
            _proj2 = ps.load_project(project_dir)
            _shot = ps.get_shot(_proj2, _scene) if _proj2 else None
            if _shot and _shot.get("takes"):
                _t = _shot["takes"][-1]
                if _t.get("image") and os.path.exists(_t["image"]):
                    st.image(_t["image"], caption=f"{_t['take_id']} · {_t.get('model')}", width=420)
                elif _t.get("video") and os.path.exists(_t["video"]):
                    st.video(_t["video"])
        except Exception:
            pass
    st.divider()


with tab_prod:
    st.header("🎛️ Production — studio tools by stage")
    st.caption(
        "All studio tools, grouped by the pipeline stage where they're used "
        "(Brief → Script → Storyboard → Asset Gen → Edit → Review → Assembly → "
        "Rights/Delivery). They run in-process against the selected project — "
        "the same engine the Ad Studio director drives."
    )

    # --- project picker (ad projects under outputs/ with a project.json) ---
    _tool_projects = ch.list_ad_project_dirs()
    _active = st.session_state.get("active_project_dir")
    _proj_opts = ["(no project)"] + _tool_projects
    if _active and _active not in _proj_opts:
        _proj_opts.insert(1, _active)
    _sel_pdir = st.selectbox(
        "Active project (used by project-scoped tools)", _proj_opts,
        index=_proj_opts.index(_active) if _active in _proj_opts else 0,
        help="Ad projects live under outputs/ (project.json). set_script creates one "
             "if none is active; scaffold_project film trees are driven in Studio Rooms.",
    )
    _tool_pdir = None if _sel_pdir == "(no project)" else _sel_pdir
    if _tool_pdir and _tool_pdir != _active:
        st.session_state.active_project_dir = _tool_pdir

    _comfy_alive = ch.comfy_up()
    if not _comfy_alive:
        st.caption("🔴 ComfyUI unreachable — comfyui renders/edits are disabled. "
                   "Start the box + open the tunnel in the Box & Status tab.")

    try:
        _menu = ch.load_tool_menu()
    except Exception as e:
        _menu = []
        st.error(f"Could not load the studio tool menu: {e}")

    if _menu:
        _groups = ch.group_tools_by_stage(_menu)
        _stage_tabs = st.tabs([g[0] for g in _groups])
        for _gi, ((_glabel, _gtools), _gtab) in enumerate(zip(_groups, _stage_tabs)):
            with _gtab:
                if _glabel.startswith("4"):
                    _render_shot_control(_tool_pdir, _comfy_alive)
                for _tool in _gtools:
                    _render_tool_expander(_tool, f"stage{_gi}", _tool_pdir, _comfy_alive)


# =============================================================================
# 💬 STUDIO CHAT TAB — conversational qwen3 + ComfyUI REPL (in-process engine)
# =============================================================================
_CHAT_HELP = (
    "**Studio Chat commands**\n\n"
    "- plain text — generate an image; if there's a current image, **edit** it "
    "(img2img, qwen3 rewrites the prompt with your change applied)\n"
    "- `:new <text>` — clear the context and generate fresh\n"
    "- `:model <id>` — switch the active image model (e.g. `:model flux2` or "
    "`:model comfyui:zimage`) — also updates the sidebar selector\n"
    "- `:region x1,y1,x2,y2 <change>` — inpaint just that region of the current "
    "image (coords are 0–1 fractions, or pixels)\n"
    "- `:denoise <0-1>` — set edit strength for img2img (default 0.65)\n"
    "- `:seed <n>` — fix the seed (`:seed random` to unfix)\n"
    "- `:help` — this list"
)

_CHAT_DIR = os.path.join("outputs", "_chat")


def _studio_chat_reply(msg: str):
    """Handle one Studio Chat message; return (reply_markdown, image_path|None).

    All engine (`ce.*`) failures are caught and returned as reply text — no
    traceback ever reaches the UI."""
    import time as _time
    ss = st.session_state
    cmd, arg = ch.parse_chat_command(msg)

    # --- setting/utility commands (no render) --------------------------------
    if cmd == "help":
        return _CHAT_HELP, None
    if cmd == "unknown":
        return f"Unrecognized command `{msg.split()[0]}`.\n\n{_CHAT_HELP}", None
    if cmd == "model":
        _full = ch.resolve_model_id(arg)
        if not _full:
            _known = ", ".join(f"`{i}`" for i in ch.comfyui_model_ids()) or "(none)"
            return f"Unknown model `{arg}`. Available: {_known}", None
        # Applied to the sidebar widget pre-instantiation on the next rerun.
        ss["_pending_active_model"] = _full
        return f"Active image model set to `{_full}`.", None
    if cmd == "denoise":
        try:
            _v = float(arg)
            if not 0.0 <= _v <= 1.0:
                raise ValueError
        except ValueError:
            return "Usage: `:denoise <0-1>`, e.g. `:denoise 0.55`", None
        ss["chat_denoise"] = _v
        return f"Edit strength (denoise) set to **{_v}**.", None
    if cmd == "seed":
        if arg.lower() in ("", "random", "rand", "none"):
            ss["chat_seed"] = None
            return "Seed unfixed — each render gets a random seed.", None
        try:
            ss["chat_seed"] = int(arg)
        except ValueError:
            return "Usage: `:seed <integer>` or `:seed random`", None
        return f"Seed fixed at **{ss['chat_seed']}**.", None

    # --- render commands: fresh generate / edit / region inpaint -------------
    region = None
    if cmd == "region":
        _parts = arg.split(None, 1)
        if len(_parts) < 2:
            return "Usage: `:region x1,y1,x2,y2 <change>`", None
        if not ss.get("chat_last_image"):
            return "No current image to inpaint — generate one first.", None
        region, idea = _parts[0], _parts[1]
    elif cmd == "new":
        ss["chat_last_image"] = None
        ss["chat_last_prompt"] = None
        if not arg:
            return "Context cleared — describe the next image.", None
        idea = arg
    else:  # plain text
        idea = arg
        if not idea:
            return _CHAT_HELP, None

    model_spec = ss.get("active_image_model")
    if not model_spec:
        return ("No ComfyUI models available — model_registry.json wasn't "
                "found (see the sidebar)."), None
    try:
        if not ce.is_up():
            return ("ComfyUI is unreachable — start the box + open the tunnel "
                    "(Box & Status tab), then try again."), None
    except Exception as e:
        return f"⚠️ Could not reach ComfyUI: {e}", None

    editing = bool(ss.get("chat_last_image"))
    _err = None
    with st.status(f"Rendering via `{model_spec}`…", expanded=True) as _cstat:
        try:
            os.makedirs(_CHAT_DIR, exist_ok=True)
            hint = ch.prompt_hint(model_spec)
            base = ss.get("chat_last_prompt") if editing else None
            st.write("🧠 qwen3 writing the image prompt… (first call after boot "
                     "can take minutes while the model loads)")
            prompt = ce.gen_prompt(idea, hint, base=base)
            st.write(f"📝 {prompt}")
            kwargs = {"seed": ss.get("chat_seed"), "width": 1024, "height": 1024}
            if editing:
                st.write("⬆️ Uploading the current image for img2img…")
                kwargs["img"] = ce.upload_image(ss["chat_last_image"])
                kwargs["denoise"] = float(ss.get("chat_denoise", 0.65))
                if region:
                    _mask_local = ce.make_region_mask(
                        region, 1024, 1024, save_dir=_CHAT_DIR,
                        name=f"mask_{int(_time.time())}.png")
                    kwargs["mask"] = ce.upload_image(_mask_local)
            graph = ce.build_graph(model_spec, prompt, **kwargs)
            st.write("🎨 ComfyUI rendering…")
            out = ce.submit_and_wait(graph, output_dir=_CHAT_DIR,
                                     output_name=f"chat_{int(_time.time())}.png")
            _cstat.update(label="Render complete", state="complete")
        except Exception as e:
            _err = e
            _cstat.update(label="Render failed", state="error")
    if _err:
        return f"⚠️ Render failed: {_err}", None

    ss["chat_last_image"] = out
    ss["chat_last_prompt"] = prompt
    _mode = ("region inpaint" if region else
             ("edit (img2img)" if editing else "new image"))
    reply = (f"**{_mode}** via `{model_spec}`\n\n"
             f"*qwen prompt:* {prompt}\n\n"
             f"Saved: `{out}` — follow up to edit it, `:region …` to inpaint, "
             f"or `:new …` to start over.")
    return reply, out


with tab_chat:
    st.header("💬 Studio Chat — talk to the render box")
    st.caption(
        "A conversational REPL: qwen3 (on the box) turns your words into an "
        "image prompt, ComfyUI renders it, and follow-up messages edit the "
        "last image. Same loop as the desktop `cli/ilyrium.ps1`, in the "
        "console. Type `:help` for commands."
    )
    if "studio_chat" not in st.session_state:
        st.session_state["studio_chat"] = []
    st.session_state.setdefault("chat_denoise", 0.65)
    st.session_state.setdefault("chat_seed", None)
    st.session_state.setdefault("chat_last_image", None)
    st.session_state.setdefault("chat_last_prompt", None)

    # ce.is_up() never raises (returns False on any failure) — belt & braces.
    try:
        _chat_up = ce.is_up()
    except Exception:
        _chat_up = False

    _cm = st.session_state.get("active_image_model") or "—"
    _csd = st.session_state.get("chat_seed")
    _cli = st.session_state.get("chat_last_image")
    st.caption(
        f"Model `{_cm}` · denoise {st.session_state['chat_denoise']} · "
        f"seed {'random' if _csd is None else _csd} · "
        + (f"editing `{os.path.basename(_cli)}`" if _cli
           else "no current image — next message generates fresh")
    )

    for _ci, _ct in enumerate(st.session_state["studio_chat"]):
        with st.chat_message(_ct["role"]):
            st.markdown(_ct["text"])
            _cimg = _ct.get("image")
            if _cimg and os.path.exists(_cimg):
                st.image(_cimg, width=420)
                try:
                    with open(_cimg, "rb") as _cfh:
                        st.download_button(
                            "⬇️ Download", _cfh.read(),
                            file_name=os.path.basename(_cimg),
                            mime="image/png", key=f"chat_dl_{_ci}")
                except Exception:
                    pass

    if not _chat_up:
        st.caption("⛔ Studio Chat needs the render box. Start the box + open "
                   "the tunnel (Box & Status tab), then 🔄 Refresh status.")
    _chat_msg = st.chat_input(
        "Describe an image… or :help for commands",
        key="studio_chat_input", disabled=not _chat_up)
    if _chat_msg and _chat_msg.strip():
        st.session_state["studio_chat"].append(
            {"role": "user", "text": _chat_msg})
        with st.chat_message("user"):
            st.markdown(_chat_msg)
        _reply, _rimg = _studio_chat_reply(_chat_msg.strip())
        _turn = {"role": "assistant", "text": _reply}
        if _rimg:
            _turn["image"] = _rimg
        st.session_state["studio_chat"].append(_turn)
        st.rerun()


# =============================================================================
# 📦 BOX & STATUS TAB — full box / ComfyUI lifecycle
# =============================================================================
with tab_box:
    st.header("📦 Box & ComfyUI — lifecycle")
    st.caption(
        "The EC2 GPU box (g6.2xlarge, NVIDIA L4) hosts ComfyUI and ollama. "
        "Start it, open the SSH tunnel, render, then Stop to end billing. "
        "The same controls live in the sidebar on every tab."
    )
    _bx1, _bx2 = st.columns(2)
    with _bx1:
        render_box_panel(key="tab")
    with _bx2:
        st.subheader("On-box image models")
        _box_ids = ch.comfyui_model_ids()
        if _box_ids:
            for _mid in _box_ids:
                st.markdown(f"- `{_mid}`")
            st.caption("From model_registry.json (provider == 'comfyui'). Rendered via "
                       "`render_shot(model='comfyui:<id>')`, the stage-4 render control, "
                       "or the stage-5 edit/inpaint tools.")
        else:
            st.caption("model_registry.json unavailable — no comfyui models found.")